# -*- coding: utf-8 -*
import secrets
import requests
import logging
from odoo import models, fields, api,_
from odoo.exceptions import UserError
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5 as Cipher_PKCS1_v1_5
from base64 import b64encode
import json, base64
from .globals import *

_logger = logging.getLogger(">>> Alankit <<<")


class AlankitAPIConfiguratin(models.AbstractModel):
    _inherit = "alankit.api.configuration"

    einvoice_url = fields.Char(default='https://www.alankitgst.com', string="E-invoice URL")  # for testing https://developers.eraahi.com
    einvoice_public_key = fields.Binary(string="E-invoice Public Key", attachment=True, required=True,
                               help="Public key for authentication with Alankit E-invoice API")
    einvoice_access_token = fields.Char(string="Access Token", copy=False, )
    einvoice_expire_time = fields.Char(string="Expire Time")
    einvoice_Sek_key = fields.Char(string="Session Encryption Key")
    einvoice_auth = fields.Boolean(string="E-invoice Authentication")

    def einvoice_authentication(self):
        """
        @usage : this method is used for authentication
        :return:
        """
        headers = {
            'Content-Type': 'application/json',
            'Ocp-Apim-Subscription-Key': self.subscription_key,
            'gstin': self.gstin
        }
        base64_encoded_data = self.env["alankit.api.configuration"].base64_encode(self.prepare_einvoice_payload_values())
        public_key_pem = base64.b64decode(self.einvoice_public_key)
        keyPub = RSA.importKey(public_key_pem)
        cipher = Cipher_PKCS1_v1_5.new(keyPub)
        cipher_text = cipher.encrypt(base64_encoded_data.encode())
        emsg = b64encode(cipher_text).decode()

        payload = json.dumps({"Data": emsg})
        # payload = emsg
        url = self.prepare_einvoice_authentication_url()
        log_name = "%s_Alankit Einvoice Instance Authentication" % (self.name.replace("/", "_"))
        log_obj = self.env['common.process.log'].sudo().create({'name': log_name,
                                                                'res_model': 'alankit.api.configuration',
                                                                'res_id': self.id,
                                                                'resource_log': 'alankit_instance'})
        try:
            response = requests.request("POST", url, headers=headers, data=payload)
            _logger.info("=============>URL Response %s", response)
            if response.status_code == 200:
                json_response = response.json()
                if json_response.get("Status") == 1:
                    _logger.info("=============> E-invoice Authentication successful!!")
                    data = json_response.get('Data', {})
                    auth_token = data.get('AuthToken')
                    token_expiry_str = data.get('TokenExpiry')
                    einvoice_Sek_key = data.get('Sek')
                    log_obj.sudo().update({
                        'response': json.dumps(json_response, indent=2),
                        'message': 'E-invoice Authentication successful!'
                    })
                    if auth_token and token_expiry_str and einvoice_Sek_key:
                        # token_expiry = datetime.strptime(token_expiry_str, '%Y-%m-%d %H:%M:%S')
                        self.write({
                            'einvoice_access_token': auth_token,
                            'einvoice_Sek_key': einvoice_Sek_key,
                            'einvoice_expire_time': token_expiry_str,
                            'einvoice_auth': True,
                            'state': 'verify'
                        })
                        return {
                            'type': 'ir.actions.client',
                            'tag': 'display_notification',
                            'params': {
                                'title': 'Success',
                                'message': 'E-invoice Authentication successful!',
                                'type': 'success',
                                'next': {'type': 'ir.actions.client', 'tag': 'reload'}
                            },
                        }
                else:
                    log_obj.sudo().update({
                        'response': json.dumps(json_response, indent=2),
                        'message': 'Alankit Einvoice Authentication failed!!!',
                    })
                    # Extract ErrorDetails
                    error_details = json_response.get('ErrorDetails', [])
                    if error_details:
                        # Create log lines for each error
                        for i, error in enumerate(error_details):
                            log_obj.line_ids.create({
                                'process_log_id': log_obj.id,
                                'name': "Error",
                                'res_model': 'alankit.api.configuration',
                                'res_id': self.id,
                                'resource_log': 'alankit_instance',
                                'response': json.dumps(error_details,indent=2),
                                'message': f"{error['ErrorMessage']}",
                                'state': "error"
                            })
                    _logger.error("Authentication Failed!")
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'title': 'Error',
                            'message': 'Alankit Einvoice Authentication failed!!!',
                            'type': 'danger',
                        }
                    }
        except requests.exceptions.RequestException:
            raise UserError(_("Authentication Failed!"))

    def prepare_einvoice_authentication_url(self):
        """
        @Usage: This method prepares the Authentication URL
        :return: Authentication URL -> String
        """
        return AUTHENTICATION_ENDPOINT_INVOICE.format(auth_url=self.einvoice_url)

    def prepare_einvoice_payload_values(self):
        payload = {
            'UserName': self.username,
            'Password': self.password,
            'AppKey': self.app_key,
            'ForceRefreshAccessToken': True
        }

        json_str = json.dumps(payload)
        return json_str

    def prepare_einvoice_url(self, einv_url):
        """
        @Usage: This method prepares the E-way Bill URL
        :return: E-invoice URL -> String
        """
        return GENERATE_INVOICE.format(auth_url=einv_url)

    def prepare_einvoice_cancel_url(self):
        """
        @Usage: This method prepared the  Cancel URL by Environment wise
        :return: E Invoice URL -> String
        """
        return CANCEL_EINVOICE.format(auth_url=self.einvoice_url)
