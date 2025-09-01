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
from odoo.addons.rcs_alankit_eway_bill.models.error_codes import ERROR_CODES

_logger = logging.getLogger(__name__)


class AddQuotationEwayCancel(models.TransientModel):
    _name = "alankit.ewaybill.cancel"
    _description = "Add Cancel Ewaybill Reason"

    eway_bill_cancel_reasons = fields.Selection(
        [('1', 'Duplicate'), ('2', 'Order Cancelled'), ('3', 'Data Entry mistake'), ('4', 'Others')], required=True)
    eway_bill_cancel_remarks = fields.Char(string="Cancellation Remarks")

    # Encryption by the decrypted sek key
    def encrypt_ewaybill_cancel_data_by_symmetric_key(self, json_data, decrypted_sek):
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
    def decrypt_ewaybill_cancel_data_by_symmetric_key(self, encrypted_sek, app_key):
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

    def cancel_eway_bill(self):
        """
        Cancels the E-way bill for the active invoice.
        This method validates the time constraint for cancellation (within 24 hours),
        generates the cancellation payload, and sends the request to the API.

        :return: Notification or log details based on the outcome.
        """
        active_model_id = self.env.context.get('active_id')
        active_model = self.env.context.get('active_model')
        ewaybill_active_id = self.env.context.get('ewaybill_active_id')
        stock_ewaybill_active_id = self.env.context.get('stock_ewaybill_active_id')
        instance = self.env['alankit.api.configuration'].get_instance()
        headers = {
            'Content-Type': 'application/json',
            'Ocp-Apim-Subscription-Key': instance.subscription_key,
            'gstin': instance.gstin,
            'AuthToken': instance.ewaybill_access_token
        }
        if self.env.context.get('active_model') == 'account.move':
            invoice = self.env['account.move'].search([('id', '=', active_model_id)])
        elif self.env.context.get('active_model') == 'stock.picking':
            invoice = self.env['stock.picking'].sudo().search([('id', '=', stock_ewaybill_active_id)])
        else:
            invoice = self.env['account.move'].search([('id', '=', ewaybill_active_id)])

            # Calculate time difference to check if within 24 hours
            if invoice.eway_bill_date:
                current_date = fields.Datetime.now() + timedelta(hours=5, minutes=30)
                eway_bill_date_str = invoice.eway_bill_date
                eway_bill_date = datetime.strptime(eway_bill_date_str, '%d/%m/%Y %I:%M:%S %p')
                time_difference = current_date - eway_bill_date
                if time_difference > timedelta(hours=24):
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'title': 'Error',
                            'message': 'E-way Bill cannot be cancelled as it is older than 24 hours.',
                            'type': 'danger',
                            'sticky': False,
                            'next': {'type': 'ir.actions.act_window_close'},
                        }
                    }

        try:
            instance = self.env['alankit.api.configuration'].get_instance()

            if instance.state != 'verify' or instance.ewaybill_auth != True:
                raise ValidationError(_('Please Create/Verify or Authenticate first Your E-way Bill Instance!'))
            else:
                current_datetime = fields.Datetime.now() + timedelta(hours=5, minutes=30)
                if hasattr(instance, 'einvoice_expire_time'):
                    einvoice_expire_time_str = instance.einvoice_expire_time
                    # Convert expiration time string to datetime object
                    einvoice_date = datetime.strptime(einvoice_expire_time_str, '%Y-%m-%d %H:%M:%S')
                    # Check if expire time is less than or not matching current time
                    if einvoice_date <= current_datetime:
                        instance.ewaybill_authentication()

            encrypted_sek = instance.ewaybill_Sek_key
            app_key = base64.b64decode(instance.app_key)
            key = self.decrypt_ewaybill_cancel_data_by_symmetric_key(encrypted_sek, app_key)
            cancel_json = self.generate_ewaybill_cancel_json(invoice, self.eway_bill_cancel_remarks,
                                                                      self.eway_bill_cancel_reasons)
            generate_json = self.encrypt_ewaybill_cancel_data_by_symmetric_key(cancel_json, key)
            cancel_invoice_url = instance.prepare_eway_bill_url()
            payload = json.dumps({"action": "CANEWB", "data": generate_json})
            response = requests.request("POST", cancel_invoice_url, headers=headers, data=payload)
            _logger.info("=============>Response Eway Bill Cancel Content %s", response.content)
            _logger.info("=============>Response Eway Bill Cancel %s", response.status_code)
            if response.status_code == 200:
                _logger.info("=============>Response Eway Bill Cancel %s", response.status_code)
                json_response = response.json()
                if json_response.get("status") == '1':
                    invoice.eway_bill_canceled = True
                    invoice.eway_bill_generated = False
                    cancel_reason_label = dict(
                        self.fields_get(allfields=['eway_bill_cancel_reasons'])['eway_bill_cancel_reasons'][
                            'selection']).get(self.eway_bill_cancel_reasons)
                    invoice.write({'eway_bill_cancel_reason': cancel_reason_label})
                    log_name = "%s_Alankit_Cancel_E-way_Bill" % (invoice.name.replace("/", "_"))
                    invoice.env['common.process.log'].sudo().create({'name': log_name,
                                                                     'res_model': active_model,
                                                                     'res_id': invoice.id,
                                                                     'resource_log': 'alankit_eway_bill',
                                                                     'response': json.dumps(json_response,
                                                                                            indent=2),
                                                                     'message': "Eway Bill Canceled!"})
                    data = json_response.get("data")
                    data_decrypt = self.decrypt_ewaybill_cancel_data_by_symmetric_key(data, key)
                    print(data_decrypt)
                    info = json.loads(data_decrypt.decode())
                    _logger.info(f"Alankit api Response : {json.dumps(json_response, indent=4)}")
                    invoice.write({'eway_bill_cancel_date': info.get('cancelDate')})
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'type': 'info',
                            'sticky': False,
                            'message': f"E-way bill cancelled successfully !!!",
                            'next': {'type': 'ir.actions.act_window_close'},
                        }
                    }
                else:
                    invoice.eway_bill_canceled = False
                    errors = base64.b64decode(json_response.get('error', [])).decode()
                    response_errors_str = json.loads(errors)['errorCodes']
                    response_errors = [code for code in response_errors_str.split(',') if code]

                    log_name = "%s_Alankit_Cancel_Eway_Bill" % (invoice.name.replace("/", "_"))
                    # Extract ErrorDetails
                    log = invoice.env['common.process.log'].sudo().create({
                        'name': log_name,
                        'res_model': active_model,
                        'res_id': invoice.id,
                        'resource_log': 'alankit_eway_bill',
                        'response': json.dumps(json_response, indent=2),
                        'message': "Eway Bill not Canceled!"
                    })

                    # Fetch the error list from the function
                    # Create log lines for each found error
                    if errors:
                        for i, error_code in enumerate(response_errors):
                            error_desc = ERROR_CODES.get(error_code)
                            log.line_ids.create({
                                'process_log_id': log.id,
                                'name': f"Error {error_code}",
                                'res_model': active_model,
                                'res_id': invoice.id,
                                'resource_log': 'alankit_eway_bill',
                                'message': error_desc,
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
                        'next': {'type': 'ir.actions.act_window_close'},
                    }
                }

        except Exception as error:
            raise UserError(_(f"Exception: {error}"))

        return {'type': 'ir.actions.act_window_close'}

    def generate_ewaybill_cancel_json(self, invoice, cancel_remarks, reason):
        """
        Generates the JSON payload required to cancel the E-way bill.

        :param invoice: The invoice record related to the E-way bill.
        :param cancel_remarks: The reason for cancellation.
        :param reason: The selected cancellation reason code.
        :return: A dictionary containing the E-way bill cancellation payload.
        """
        return {
            "ewbNo": int(invoice.eway_bill_no),
            "cancelRsnCode": int(reason),
            **({"cancelRmrk": cancel_remarks} if cancel_remarks else {})
        }
