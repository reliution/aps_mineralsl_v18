# -*- coding: utf-8 -*-
import base64
import requests
import logging
import json
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from Crypto.Util.Padding import pad
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)


class AddQuotationEinvoiceCancel(models.TransientModel):
    _name = "alankit.einvoice.cancel"
    _description = "Add Cancel E-invoice Reason"

    einvoice_cancel_reasons = fields.Selection(
        [('1', 'Duplicate'), ('2', 'Data Entry mistake')], required=True)
    einvoice_cancel_remarks = fields.Char(string="Cancellation Remarks", required=True)

    # Encryption by the decrypted sek key
    def encrypt_einvoice_cancel_data_by_symmetric_key(self, json_data, decrypted_sek):
        """
        Encrypts JSON data using the provided SEK key via AES encryption.

        :param json_data: The JSON data to be encrypted.
        :param decrypted_sek: The decrypted SEK key for encryption.
        :return: The encrypted JSON data.
        """
        sek_b = (decrypted_sek)
        aes_key = AES.new(sek_b, AES.MODE_ECB)
        try:
            # Convert dictionary to JSON string
            json_str = json.dumps(json_data)
            padded_data = pad(json_str.encode(), AES.block_size)
            encrypted_data = aes_key.encrypt(padded_data)
            encrypted_json = base64.b64encode(encrypted_data).decode()
            return encrypted_json
        except Exception as e:
            return "Exception " + str(e)

    # Decrypt sek key
    def decrypt_einvoice_cancel_data_by_symmetric_key(self, encrypted_sek, app_key):
        """
        Decrypts the encrypted SEK key using the provided app key via AES decryption.

        :param encrypted_sek: The encrypted SEK key to be decrypted.
        :param app_key: The application key for decryption.
        :return: The decrypted SEK key.
        """
        try:
            data_to_decrypt = base64.b64decode(encrypted_sek)
            key_bytes = app_key
            tdes = AES.new(key_bytes, AES.MODE_ECB)
            decrypted_data = tdes.decrypt(data_to_decrypt)
            decrypted_data = unpad(decrypted_data, AES.block_size)
            return decrypted_data
        except Exception as ex:
            raise ex

    def static_cancel_response(self):
        canceled_data = {
            "Irn": "a5c12dca80e743321740b001fd70953e8738d109865d28ba4013750f2046f229",
            "CancelDate": "2019-12-05 14:26:00"
        }
        return canceled_data

    def cancel_einvoice(self):
        """
        Cancels the E-way bill for the active invoice.
        This method validates the time constraint for cancellation (within 24 hours),
        generates the cancellation payload, and sends the request to the API.

        :return: Notification or log details based on the outcome.
        """
        active_model_id = self.env.context.get('active_id')
        einvoice_active_id = self.env.context.get('einvoice_active_id')
        instance = self.env['alankit.api.configuration'].get_instance()
        headers = {
            'Ocp-Apim-Subscription-Key': instance.subscription_key,
            'gstin': instance.gstin,
            'AuthToken': instance.einvoice_access_token,
            'user_name': instance.username
        }
        if self.env.context.get('active_model') == 'account.move':
            invoice = self.env['account.move'].search([('id', '=', active_model_id)])
        else:
            invoice = self.env['account.move'].search([('id', '=', einvoice_active_id)])

            # Calculate time difference to check if within 24 hours
            if invoice.invoice_ack_dt:
                current_date = fields.Datetime.now() + timedelta(hours=5, minutes=30)
                einvoice_date_str = invoice.invoice_ack_dt
                # Adjust the format string to match '2024-09-23 18:23:44'
                einvoice_date = datetime.strptime(einvoice_date_str, '%Y-%m-%d %H:%M:%S')
                time_difference = current_date - einvoice_date
                if time_difference > timedelta(hours=24):
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'title': 'Error',
                            'message': 'E-invoice cannot be cancelled as it is older than 24 hours.',
                            'type': 'danger',
                            'sticky': False,
                            'next': {
                                'type': 'ir.actions.act_window_close',
                            }
                        }
                    }

        try:
            instance = self.env['alankit.api.configuration'].get_instance()

            if instance.state != 'verify' or instance.einvoice_auth != True:
                raise ValidationError(_('Please Create/Verify or Authenticate first Your E-invoice Instance!'))
            else:
                current_datetime = fields.Datetime.now() + timedelta(hours=5, minutes=30)
                einvoice_expire_time_str = instance.einvoice_expire_time
                # Convert expiration time string to datetime object
                einvoice_date = datetime.strptime(einvoice_expire_time_str, '%Y-%m-%d %H:%M:%S')
                # Check if expire time is less than or not matching current time
                if einvoice_date <= current_datetime:
                    instance.einvoice_authentication()

            encrypted_sek = instance.einvoice_Sek_key
            app_key = base64.b64decode(instance.app_key)
            key = self.decrypt_einvoice_cancel_data_by_symmetric_key(encrypted_sek, app_key)
            cancel_json = self.generate_einvoice_cancel_json(invoice, self.einvoice_cancel_remarks,
                                                             self.einvoice_cancel_reasons)
            generate_json = self.encrypt_einvoice_cancel_data_by_symmetric_key(cancel_json, key)
            cancel_invoice_url = instance.prepare_einvoice_cancel_url()
            payload = json.dumps({"Data": generate_json})
            response = requests.request("POST", cancel_invoice_url, headers=headers, data=payload)
            _logger.info("=============>Response E-invoice Cancel Content %s", response.content)
            _logger.info("=============>Response E-invoice Cancel %s", response.status_code)
            if response.status_code == 200:
                json_response = response.json()
                _logger.info("=============>Response E-invoice Cancel %s", json_response)
                if json_response.get("Status") == 1:
                    invoice.einvoice_canceled = True
                    invoice.einvoice_generated = False
                    cancel_reason_label = dict(
                        self.fields_get(allfields=['einvoice_cancel_reasons'])['einvoice_cancel_reasons'][
                            'selection']).get(self.einvoice_cancel_reasons)
                    invoice.write({'einvoice_cancel_reason': cancel_reason_label})
                    log_name = "%s_Alankit_Cancel_E-invoice" % (invoice.name.replace("/", "_"))
                    invoice.env['common.process.log'].sudo().create({'name': log_name,
                                                                     'res_model': 'account.move',
                                                                     'res_id': invoice.id,
                                                                     'resource_log': 'alankit_e-invoice',
                                                                     'response': json.dumps(json_response,
                                                                                            indent=2),
                                                                     'message': "E-invoice Canceled!"})
                    data = json_response.get("Data")
                    data_decrypt = self.decrypt_einvoice_cancel_data_by_symmetric_key(data, key)
                    print(data_decrypt)
                    info = json.loads(data_decrypt.decode())
                    # info = self.static_cancel_response()
                    _logger.info("=============>Response E-invoice Cancel %s", info)
                    invoice.write({'einvoice_cancel_date': info.get('CancelDate')})
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'type': 'info',
                            'sticky': False,
                            'message': "E-invoice cancelled successfully !!!",
                            'next': {
                                'type': 'ir.actions.act_window_close',
                            }
                        }
                    }
                else:
                    invoice.einvoice_canceled = False
                    error_details = json_response.get('ErrorDetails', [])
                    _logger.info("=============>Response Alankit Cancel Einvoice %s", error_details)

                    log_name = "%s_Alankit_Cancel_Einvoice" % (invoice.name.replace("/", "_"))
                    # Extract ErrorDetails
                    log = invoice.env['common.process.log'].sudo().create({
                        'name': log_name,
                        'res_model': 'account.move',
                        'res_id': invoice.id,
                        'resource_log': 'alankit_e-invoice',
                        'response': json.dumps(json_response, indent=2),
                        'message': "E-invoice not Canceled!"
                    })
                    # Create log lines for each error
                    for i, error in enumerate(error_details):
                        log.line_ids.create({
                            'process_log_id': log.id,
                            'name': f"ErrorCode_{error['ErrorCode']}",
                            'res_model': 'account.move',
                            'res_id': invoice.id,
                            'resource_log': 'alankit_e-invoice',
                            'message': f"{error['ErrorMessage']}",
                            'state': "error"
                        })

            else:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Error',
                        'message': response.reason,
                        'type': 'danger',
                        'sticky': False,
                        'next': {
                            'type': 'ir.actions.act_window_close',
                        }
                    }
                }

        except Exception as error:
            raise UserError(_(f"Exception: {error}"))

        return {'type': 'ir.actions.act_window_close'}

    def generate_einvoice_cancel_json(self, invoice, cancel_remarks, reason):
        """
        Generates the JSON payload required to cancel the E-way bill.

        :param invoice: The invoice record related to the E-way bill.
        :param cancel_remarks: The reason for cancellation.
        :param reason: The selected cancellation reason code.
        :return: A dictionary containing the E-way bill cancellation payload.
        """
        return {
            "Irn": invoice.irn_no,
            "CnlRsn": reason,
            "CnlRem": cancel_remarks
        }
