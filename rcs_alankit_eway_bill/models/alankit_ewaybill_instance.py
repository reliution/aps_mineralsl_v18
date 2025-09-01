# -*- coding: utf-8 -*
import secrets
import requests
import logging
from odoo import fields, models, api, _
from .globals import *
from odoo.exceptions import UserError
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5 as Cipher_PKCS1_v1_5
from base64 import b64encode
import json, base64

_logger = logging.getLogger(">>> Alankit <<<")


class AlankitAPIConfiguratin(models.AbstractModel):
    _inherit = "alankit.api.configuration"

    ewaybill_url = fields.Char(string="E-way Bill URL")
    ewaybill_public_key = fields.Binary(string="E-way Bill Public Key", attachment=True, required=True,
                               help="Public key for authentication with Alankit E-way bill API")
    ewaybill_access_token = fields.Char(string="Access Token", copy=False)
    ewaybill_Sek_key = fields.Char(string="Session Encryption Key", copy=False)
    ewaybill_auth = fields.Boolean(string="E-way Bill Authentication")

    def ewaybill_authentication(self):
        """
        Perform authentication with Alankit E-way bill API.
        :return: dict - Dictionary containing action parameters for notification display.
        """
        headers = {
            'Content-Type': 'application/json',
            'Ocp-Apim-Subscription-Key': self.subscription_key,
            'Gstin': self.gstin
        }
        base64_encoded_data = self.env["alankit.api.configuration"].base64_encode(self.prepare_payload_values())
        public_key_pem = base64.b64decode(self.ewaybill_public_key)
        keyPub = RSA.importKey(public_key_pem)
        cipher = Cipher_PKCS1_v1_5.new(keyPub)
        cipher_text = cipher.encrypt(base64_encoded_data.encode())
        emsg = b64encode(cipher_text).decode()
        print(f"{emsg}")
        payload = json.dumps({"Data": emsg})
        url = self.prepare_authentication_url()
        log_name = "%s_Alankit Eway Bill Instance Authentication" % (self.name.replace("/", "_"))
        log_obj = self.env['common.process.log'].sudo().create({'name': log_name,
                                                                'res_model': 'alankit.api.configuration',
                                                                'res_id': self.id,
                                                                'resource_log': 'alankit_instance'})
        try:
            response = requests.request("POST", url, headers=headers, data=payload)
            if response.status_code == 200:
                json_response = response.json()
                if json_response.get('status') == '1':
                    _logger.info("=============> E-way Bill Authentication successful!!")
                    auth_token = json_response.get('authtoken')
                    ewaybill_Sek_key = json_response.get('sek')
                    log_obj.sudo().update({
                        'response': json.dumps(json_response, indent=2),
                        'message': 'E-way Bill Authentication successful!'
                    })
                    if auth_token and ewaybill_Sek_key:
                        self.update({
                            'ewaybill_access_token': auth_token,
                            'ewaybill_Sek_key': ewaybill_Sek_key,
                            'ewaybill_auth': True,
                            'state': 'verify'
                        })
                        return {
                            'type': 'ir.actions.client',
                            'tag': 'display_notification',
                            'params': {
                                'title': 'Success',
                                'message': 'E-way Bill Authentication successful!',
                                'type': 'success',
                                'next': {'type': 'ir.actions.client', 'tag': 'reload'}
                            },
                        }
                else:
                    log_obj.sudo().update({
                        'response': json.dumps(json_response, indent=2),
                        'message': 'Alankit Eway Bill Authentication failed!!!',
                    })
                    error = json_response.get('error')
                    msg = base64.b64decode(error).decode()
                    if error:
                        log_obj.line_ids.create({
                            'process_log_id': log_obj.id,
                            'name': "Error",
                            'res_model': 'alankit.api.configuration',
                            'res_id': self.id,
                            'resource_log': 'alankit_instance',
                            'response': json.dumps(msg, indent=2),
                            'message': msg,
                            'state': "error"
                        })
                    _logger.error("Authentication Failed!")
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'title': 'Error',
                            'message': 'Alankit Eway Bill Authentication failed!!!',
                            'type': 'danger',
                        }
                    }
        except requests.exceptions.RequestException as error:
            raise UserError(_("Authentication Failed!!!"))

    def prepare_authentication_url(self):
        """
        @Usage: This method prepares the Authentication URL for Alankit
        :return: str - Authentication URL
        """
        return AUTHENTICATION_ENDPOINT.format(auth_url=self.ewaybill_url)

    def prepare_payload_values(self):
        """
        @Usage: This method prepares the E-way Bill Payload values for Alankit
        :return: payload json string
        """
        payload = {
            'action': 'ACCESSTOKEN',
            'username': self.username,
            'password': self.password,
            'app_key': self.app_key,
        }
        json_string = json.dumps(payload)

        return json_string

    def prepare_eway_bill_url(self):
        """
        @Usage: This method prepares the E-way Bill URL for Alankit
        :return: Eway Bill URL -> String
        """
        return EWAY_BILL.format(auth_url=self.ewaybill_url)

    def prepare_generate_ewaybill_errorlist(self):
        """
        @Usage: This method prepares the E-way Bill ErrorList URL for Alankit
        :return: Eway Bill ErrorList URL -> String
        """
        return GENERATE_EWAY_BILL_ERRORLIST.format(auth_url=self.ewaybill_url)
