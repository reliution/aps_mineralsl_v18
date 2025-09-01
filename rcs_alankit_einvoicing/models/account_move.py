import requests
import json
import base64
import re
import logging
from base64 import b64encode
from collections import defaultdict
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from Crypto.Util.Padding import pad
from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import html_escape, float_is_zero, float_compare
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    irn_no = fields.Char(copy=False, readonly=True)
    invoice_ack_no = fields.Char(copy=False, readonly=True)
    invoice_ack_dt = fields.Char(copy=False, readonly=True)
    einvoice_canceled = fields.Boolean(copy=False, readonly=True)
    einvoice_generated = fields.Boolean(copy=False)
    einvoice_cancel_reason = fields.Char(string="Cancellation Reason",
                                         help="This field display reason of cancellation", copy=False)
    einvoice_cancel_date = fields.Char(string="Cancellation Date",
                                       help="This field display date of cancellation", copy=False)

    signed_qr_code_str = fields.Char(string='QR Code')
    signed_invoice_str = fields.Char(string='Invoice')
    einvoice_log_count = fields.Integer(string="Alankit E-invoice Logs", compute='_get_alankit_einvoice_logs')

    def _get_alankit_einvoice_logs(self):
        """
            @usage: Alankit log Count
        """
        for rec in self:
            log_ids = self.env['common.process.log'].search(
                [('res_id', '=', rec.id), ('res_model', '=', 'account.move'),
                 ('resource_log', '=', 'alankit_e-invoice')])
            rec.einvoice_log_count = len(log_ids)

    # Encryption by the decrypted sek key
    def encrypt_einvoice_data_by_symmetric_key(self, json_data, decrypted_sek):
        """
        Encrypt the JSON payload using the provided decrypted SEK (Symmetric Encryption Key)

        :param json_data: dict
            payload json formatted data
        :param decrypted_sek: decrypted sek key
        :return: encrypted JSON payload data
        :raises Exception:
                If decryption fails, the exception is raised
        """
        sek_b = (decrypted_sek)
        aes_key = AES.new(sek_b, AES.MODE_ECB)
        try:
            # Convert dictionary to JSON string
            json_str = json.dumps(json_data)
            padded_data = pad(json_str.encode(), AES.block_size)
            encrypted_data = aes_key.encrypt(padded_data)
            encrypted_json = b64encode(encrypted_data).decode()
            return encrypted_json
        except Exception as e:
            return "Exception " + str(e)

    # Decrypt sek key
    def decrypt_einvoice_data_by_symmetric_key(self, encrypted_sek, app_key):
        """
        Decrypts the provided encrypted SEK (Symmetric Encryption Key) using the given app key
        :param encrypted_sek: encrypted SEK encoded in base64
        :param app_key: app key used for decryption
        :return:bytes
            decrypted SEK
        :raises Exception:
            If decryption fails, the exception is raised
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


    def static_einvoice_data(self):
        json_data = {
          'Version': '1.1',
          'TranDtls': {
            'TaxSch': 'GST',
            'SupTyp': 'B2B',
            'RegRev': 'N',
            'EcmGstin': None,
            'IgstOnIntra': 'N'
          },
          'DocDtls': {
            'Typ': 'INV',
            'No': 'NV/200/00008',
            'Dt': '26/11/2024'
          },
          'SellerDtls': {
            'Gstin': '07AGAPA5363L002',
            'LglNm': 'IN Company',
            'Addr1': 'Block no. 401',
            'Loc': 'new delhi',
            'Pin': 110002,
            'Stcd': '07',
            'Ph': '918123456789',
            'Em': 'info@company.inexample.com',
            'Addr2': 'Street 2'
          },
          'BuyerDtls': {
            'Gstin': '24AACCT6304M1ZB',
            'LglNm': 'Registered Customer',
            'Addr1': '201, Second Floor, IT Tower 4',
            'Loc': 'Gandhinagar',
            'Pin': 382007,
            'Stcd': '24',
            'Pos': '24',
            'Addr2': 'InfoCity Gate - 1, Infocity'
          },
          'DispDtls': {
            'Nm': 'IN Company',
            'Addr1': 'Block no. 401',
            'Loc': 'new delhi',
            'Pin': 110002,
            'Stcd': '07',
            'Addr2': 'Street 2'
          },
          'ShipDtls': {
            'Gstin': '24AACCT6304M1ZB',
            'LglNm': 'Registered Customer',
            'Addr1': '201, Second Floor, IT Tower 4',
            'Loc': 'Gandhinagar',
            'Pin': 382007,
            'Stcd': '24',
            'Addr2': 'InfoCity Gate - 1, Infocity'
          },
          'ItemList': [
            {
              'SlNo': '1',
              'PrdDesc': '[E-COM12] Conference Chair (Steel)',
              'IsServc': 'N',
              'HsnCd': '94018000',
              'Barcde': None,
              'Qty': 1.0,
              'Unit': 'UNT',
              'UnitPrice': 33.0,
              'TotAmt': 33.0,
              'Discount': 0.0,
              'AssAmt': 33.0,
              'GstRt': 5.0,
              'CgstAmt': 0.0,
              'SgstAmt': 0.0,
              'IgstAmt': 1.65,
              'CesRt': 0.0,
              'CesAmt': 0.0,
              'CesNonAdvlAmt': 0.0,
              'StateCesRt': 0.0,
              'StateCesAmt': 0.0,
              'StateCesNonAdvlAmt': 0.0,
              'OthChrg': 0.0,
              'TotItemVal': 34.65,
              'BchDtls': {
                'Nm': 'No Batch',
                'ExpDt': None,
                'WrDt': None
              },
              'AttribDtls': [
                {
                  'Nm': '[E-COM12] Conference Chair (Steel)',
                  'Val': '33.0'
                }
              ]
            }
          ],
          'ValDtls': {
            'AssVal': 33.0,
            'CgstVal': 0.0,
            'SgstVal': 0.0,
            'IgstVal': 1.65,
            'CesVal': 0.0,
            'StCesVal': 0.0,
            'RndOffAmt': 0.0,
            'TotInvVal': 34.65
          },
          'RefDtls': {
            'DocPerdDtls': {
              'InvStDt': '26/11/2024',
              'InvEndDt': '26/11/2024'
            },
            'PrecDocDtls': [
              {
                'InvNo': 'NV/2024/00004',
                'InvDt': '26/11/2024'
              }
            ]
          },
          'AddlDocDtls': [
            {
              'Url': 'https://einv-apisandbox.nic.in',
              'Docs': 'NV/2024/00004',
              'Info': None
            }
          ]
        }
        return json_data

    # Generate e-invoice bill
    def create_einvoice(self):
        """
        @usage: Generate E-invoice through Alankit API
        """
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
            _logger.info("=============>Generated Einvoice URL %s", encrypted_sek)
            app_key = base64.b64decode(instance.app_key)
            key = self.decrypt_einvoice_data_by_symmetric_key(encrypted_sek, app_key)
            log_name = "%s_Alankit_E-invoice" % (self.name.replace("/", "_"))
            log_obj = self.env['common.process.log'].sudo().create({'name': log_name,
                                                                    'res_model': 'account.move',
                                                                    'res_id': self.id,
                                                                    'resource_log': 'alankit_e-invoice'})
            json_data = self.generate_einvoice_json(log_obj)
            # json_data = self.static_einvoice_data()
            # print(json_data)
            _logger.info("=============>Generated Einvoice json %s", json_data)
            generate_json = self.encrypt_einvoice_data_by_symmetric_key(json_data, key)
            try:
                _logger.info("=============>Generated Einvoice json %s", generate_json)
                url = self.env['alankit.api.configuration'].prepare_einvoice_url(instance.einvoice_url)
                _logger.info("=============>Generated Einvoice URL %s", url)
                headers = {
                    'Content-Type': 'application/json',
                    'Ocp-Apim-Subscription-Key': instance.subscription_key,
                    'gstin': instance.gstin,
                    'AuthToken': instance.einvoice_access_token,
                    'user_name': instance.username
                }
                payload = json.dumps({"Data": generate_json})
                response = requests.request("POST", url, headers=headers, data=payload)
                _logger.info("=============>Response Invoice Content %s", response.content)
                _logger.info("=============>Response invoice Status %s", response.status_code)
                message = ""
                status_code = 200
                if status_code == 200:
                    if response.status_code == 200:
                        json_response = response.json()

                    # static response
                    # json_response = {'Status': 1, 'ErrorDetails': None,
                    #                  'Data': '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',
                    #                  'InfoDtls': [{'InfCd': 'EWBERR', 'Desc': [{'ErrorCode': '4021',
                    #                                                             'ErrorMessage': 'Transporter document date cannot be earlier than the invoice date.'}]}]}
                    # print(json_response)
                    _logger.info("=============>Generated Einvoice Response %s", json_response)
                    if json_response.get("Status") == 1:
                        self.einvoice_generated = True
                        data = json_response.get("Data")
                        data_decrypt = self.decrypt_einvoice_data_by_symmetric_key(data, key)
                        # print(data_decrypt)
                        info = json.loads(data_decrypt.decode())
                        # Update the log object once
                        log_obj.sudo().update({
                            'response': json.dumps(info, indent=2),
                            'message': 'E-invoice Generated!'
                        })
                        _logger.info("Alankit API Response: %s", json.dumps(json_response, indent=4))
                        if isinstance:
                            self.irn_no = info.get('Irn')
                            self.invoice_ack_no = info.get('AckNo')
                            self.invoice_ack_dt = info.get('AckDt')

                        signed_invoice = info.get('SignedInvoice')
                        signed_qrcode = info.get('SignedQRCode')

                        # signed_invoice = 'eyJhbGciOiJSUzI1NiIsImtpZCI6IjE1MTNCODIxRUU0NkM3NDlBNjNCODZFMzE4QkY3MTEwOTkyODdEMUYiLCJ4NXQiOiJGUk80SWU1R3gwbW1PNGJqR0w5eEVKa29mUjgiLCJ0eXAiOiJKV1QifQ.eyJkYXRhIjoie1wiQWNrTm9cIjoxNzI0MTAwMTY2MDY3NDEsXCJBY2tEdFwiOlwiMjAyNC0wNi0wOCAxMDo1Mjo0NlwiLFwiSXJuXCI6XCI5M2Q2NDNlNWQ3ZWZlYmVkZmI1ZGQ1ZmM1ZWNlMmY3YWM5OTRhNjhiOGY1OTdmZjBlM2IyOTZkMzFkMmFjYWQ1XCIsXCJWZXJzaW9uXCI6XCIxLjFcIixcIlRyYW5EdGxzXCI6e1wiVGF4U2NoXCI6XCJHU1RcIixcIlN1cFR5cFwiOlwiQjJCXCIsXCJSZWdSZXZcIjpcIk5cIixcIklnc3RPbkludHJhXCI6XCJOXCJ9LFwiRG9jRHRsc1wiOntcIlR5cFwiOlwiSU5WXCIsXCJOb1wiOlwiSU5WLzIwMjQvMDAwMzhcIixcIkR0XCI6XCIwOC8wNi8yMDI0XCJ9LFwiU2VsbGVyRHRsc1wiOntcIkdzdGluXCI6XCIwN0FHQVBBNTM2M0wwMDJcIixcIkxnbE5tXCI6XCJJTiBDb21wYW55XCIsXCJBZGRyMVwiOlwiQmxvY2sgbm8uIDQwMVwiLFwiQWRkcjJcIjpcIlN0cmVldCAyXCIsXCJMb2NcIjpcIkRlbGhpXCIsXCJQaW5cIjoxMTAwNTUsXCJTdGNkXCI6XCIwN1wiLFwiUGhcIjpcIjkxODEyMzQ1Njc5MFwiLFwiRW1cIjpcImluZm9AY29tcGFueS5pbmV4YW1wbGUuY29tXCJ9LFwiQnV5ZXJEdGxzXCI6e1wiR3N0aW5cIjpcIjI5QVdHUFY3MTA3QjFaMVwiLFwiTGdsTm1cIjpcIkhtZyBSYW1hbnVqXCIsXCJQb3NcIjpcIjI5XCIsXCJBZGRyMVwiOlwiNXRoIGJsb2NrLCBrdXZlbXB1IGxheW91dFwiLFwiQWRkcjJcIjpcImt1dmVtcHUgbGF5b3V0XCIsXCJMb2NcIjpcIkdBTkRISU5BR0FSXCIsXCJQaW5cIjo1NjIxNjAsXCJQaFwiOlwiOTkyMTEyNTEyM1wiLFwiRW1cIjpcImluZm9AeW91cmNvbXBhbnkuY29tXCIsXCJTdGNkXCI6XCIyOVwifSxcIkRpc3BEdGxzXCI6e1wiTm1cIjpcIklOIENvbXBhbnlcIixcIkFkZHIxXCI6XCJCbG9jayBuby4gNDAxXCIsXCJBZGRyMlwiOlwiU3RyZWV0IDJcIixcIkxvY1wiOlwiRGVsaGlcIixcIlBpblwiOjExMDA1NSxcIlN0Y2RcIjpcIjA3XCJ9LFwiU2hpcER0bHNcIjp7XCJHc3RpblwiOlwiMjlBV0dQVjcxMDdCMVoxXCIsXCJMZ2xObVwiOlwiSG1nIFJhbWFudWpcIixcIkFkZHIxXCI6XCI1dGggYmxvY2ssIGt1dmVtcHUgbGF5b3V0XCIsXCJBZGRyMlwiOlwia3V2ZW1wdSBsYXlvdXRcIixcIkxvY1wiOlwiR0FOREhJTkFHQVJcIixcIlBpblwiOjU2MjE2MCxcIlN0Y2RcIjpcIjI5XCJ9LFwiSXRlbUxpc3RcIjpbe1wiSXRlbU5vXCI6MCxcIlNsTm9cIjpcIjFcIixcIklzU2VydmNcIjpcIk5cIixcIlByZERlc2NcIjpcIltFLUNPTTA4XSBTdG9yYWdlIEJveFwiLFwiSHNuQ2RcIjpcIjQ4MTk2MDAwXCIsXCJCYXJjZGVcIjpcIjEyMzQ1MjNcIixcIlF0eVwiOjEuMCxcIlVuaXRcIjpcIlVOVFwiLFwiVW5pdFByaWNlXCI6NTAwLjAsXCJUb3RBbXRcIjo1MDAuMCxcIkRpc2NvdW50XCI6MC4wLFwiQXNzQW10XCI6NTAwLjAsXCJHc3RSdFwiOjE4LjAsXCJJZ3N0QW10XCI6OTAuMCxcIkNnc3RBbXRcIjowLjAsXCJTZ3N0QW10XCI6MC4wLFwiQ2VzUnRcIjowLjAsXCJDZXNBbXRcIjowLjAsXCJDZXNOb25BZHZsQW10XCI6MC4wLFwiU3RhdGVDZXNSdFwiOjAuMCxcIlN0YXRlQ2VzQW10XCI6MC4wLFwiU3RhdGVDZXNOb25BZHZsQW10XCI6MC4wLFwiT3RoQ2hyZ1wiOjAuMCxcIlRvdEl0ZW1WYWxcIjo1OTAuMCxcIk9yZExpbmVSZWZcIjpcIjMyNTZcIixcIk9yZ0NudHJ5XCI6XCJBR1wiLFwiUHJkU2xOb1wiOlwiMTIzNDVcIixcIkJjaER0bHNcIjp7XCJObVwiOlwiMTIzNDU2XCIsXCJFeHBEdFwiOlwiMDEvMDgvMjAyNFwiLFwiV3JEdFwiOlwiMDEvMDkvMjAyNFwifSxcIkF0dHJpYkR0bHNcIjpbe1wiTm1cIjpcIltFLUNPTTA4XSBTdG9yYWdlIEJveFwiLFwiVmFsXCI6XCIxMDAwMFwifV19XSxcIlZhbER0bHNcIjp7XCJBc3NWYWxcIjo1MDAuMCxcIkNnc3RWYWxcIjowLjAsXCJTZ3N0VmFsXCI6MC4wLFwiSWdzdFZhbFwiOjkwLjAsXCJDZXNWYWxcIjowLjAsXCJTdENlc1ZhbFwiOjAuMCxcIkRpc2NvdW50XCI6MCxcIk90aENocmdcIjowLFwiUm5kT2ZmQW10XCI6MC4wLFwiVG90SW52VmFsXCI6NTkwLjAsXCJUb3RJbnZWYWxGY1wiOjB9LFwiUGF5RHRsc1wiOntcIk5tXCI6XCJTQklcIixcIkFjY0RldFwiOlwiNTY5NzM4OTcxMzIxMFwiLFwiTW9kZVwiOlwiQ2FzaFwiLFwiRmluSW5zQnJcIjpcIlNCSU4xMTAwMFwiLFwiUGF5VGVybVwiOlwiMTAwXCIsXCJQYXlJbnN0clwiOlwiR2lmdFwiLFwiQ3JUcm5cIjpcInRlc3RcIixcIkRpckRyXCI6XCJ0ZXN0XCIsXCJDckRheVwiOjEwMCxcIlBhaWRBbXRcIjo1OTAuMCxcIlBheW10RHVlXCI6MC4wfSxcIlJlZkR0bHNcIjp7XCJEb2NQZXJkRHRsc1wiOntcIkludlN0RHRcIjpcIjA4LzA2LzIwMjRcIixcIkludkVuZER0XCI6XCIwOC8wNi8yMDI0XCJ9LFwiUHJlY0RvY0R0bHNcIjpbe1wiSW52Tm9cIjpcIklOVi8yMDI0LzAwMDM4XCIsXCJJbnZEdFwiOlwiMDgvMDYvMjAyNFwifV0sXCJDb250ckR0bHNcIjpbe1wiUmVjQWR2UmVmclwiOlwiRG9jLzAwM1wiLFwiUmVjQWR2RHRcIjpcIjAxLzA4LzIwMjBcIixcIlRlbmRSZWZyXCI6XCJBYmMwMDFcIixcIkNvbnRyUmVmclwiOlwiQ28xMjNcIixcIkV4dFJlZnJcIjpcIllvNDU2XCIsXCJQcm9qUmVmclwiOlwiRG9jLTQ1NlwiLFwiUE9SZWZyXCI6XCJEb2MtNzg5XCIsXCJQT1JlZkR0XCI6XCIwMS8wOC8yMDIwXCJ9XX0sXCJBZGRsRG9jRHRsc1wiOlt7XCJVcmxcIjpcImh0dHBzOi8vZWludi1hcGlzYW5kYm94Lm5pYy5pblwiLFwiRG9jc1wiOlwiVGVzdCBEb2NcIixcIkluZm9cIjpcIkRvY3VtZW50IFRlc3RcIn1dLFwiRXhwRHRsc1wiOntcIlNoaXBCTm9cIjpcIkEtMjQ4XCIsXCJTaGlwQkR0XCI6XCIxMi8wNi8yMDI0XCIsXCJQb3J0XCI6XCJJTkFCRzFcIixcIlJlZkNsbVwiOlwiTlwiLFwiRm9yQ3VyXCI6XCJJTlJcIixcIkNudENvZGVcIjpcIjI5XCJ9LFwiRXdiRHRsc1wiOntcIlRyYW5zSWRcIjpcIjEyQVdHUFY3MTA3QjFaMVwiLFwiVHJhbnNOYW1lXCI6XCJBenVyZSBJbnRlcmlvclwiLFwiVHJhbnNNb2RlXCI6XCIxXCIsXCJEaXN0YW5jZVwiOjIxMzAsXCJUcmFuc0RvY05vXCI6XCJUUkFOLzIwMjQvMDAwMzdcIixcIlRyYW5zRG9jRHRcIjpcIjA2LzA2LzIwMjRcIixcIlZlaE5vXCI6XCJHSjAzSFIwMDE0XCIsXCJWZWhUeXBlXCI6XCJSXCJ9fSIsImlzcyI6Ik5JQyBTYW5kYm94In0.Y_iifHSEwt11p1-ydGMouLuR3OxjDr5BOAhG3YShHv0lliw7KY_d5epjES-PTJWSjuzX1dM1W-MbfFOHvJZ4kZNBH_u9tuRR_J_l9zoSRCiTGTxQBa3dyXCfJ2_2c6QvpaAgZPZtwrEBKMUgL_2djJeIYtcCCjSprw6a4-Nri6gSIzaorp9utdN_g5jN4dGQOk_4M1E0MkHQZazKeHyFXMWojFKaauaHamr77a7zsq59e3vrgBh7YIrdtAMUoYavUq0hJSTD09XRY1stjOu9yOd5TFys2XpywzBCWRVaWQuGIwFO_evi7cANsc9hbgEgCXep5v6Xuy4-OFu3ynfywg'
                        # signed_qrcode = 'eyJhbGciOiJSUzI1NiIsImtpZCI6IjE1MTNCODIxRUU0NkM3NDlBNjNCODZFMzE4QkY3MTEwOTkyODdEMUYiLCJ4NXQiOiJGUk80SWU1R3gwbW1PNGJqR0w5eEVKa29mUjgiLCJ0eXAiOiJKV1QifQ.eyJkYXRhIjoie1wiU2VsbGVyR3N0aW5cIjpcIjA3QUdBUEE1MzYzTDAwMlwiLFwiQnV5ZXJHc3RpblwiOlwiMjlBV0dQVjcxMDdCMVoxXCIsXCJEb2NOb1wiOlwiSU5WLzIwMjQvMDAwMzhcIixcIkRvY1R5cFwiOlwiSU5WXCIsXCJEb2NEdFwiOlwiMDgvMDYvMjAyNFwiLFwiVG90SW52VmFsXCI6NTkwLjAsXCJJdGVtQ250XCI6MSxcIk1haW5Ic25Db2RlXCI6XCI0ODE5NjAwMFwiLFwiSXJuXCI6XCI5M2Q2NDNlNWQ3ZWZlYmVkZmI1ZGQ1ZmM1ZWNlMmY3YWM5OTRhNjhiOGY1OTdmZjBlM2IyOTZkMzFkMmFjYWQ1XCIsXCJJcm5EdFwiOlwiMjAyNC0wNi0wOCAxMDo1Mjo0NlwifSIsImlzcyI6Ik5JQyBTYW5kYm94In0.HJdGpI0ULs9Pc5Pc4mz5S68i97WiXanP9-FUO6p7AMkTd5e6V8rX0Gm_l0l58Z9TolauOJhDHMMhaYmp3UFK1oSmLaYPRjM-2VTo5-XGOuhMuO5nLdZs_gathMcL2lqPPl2blerTn4gyUkF4FrE9yaJGIl6aRzIKkimqB8XGChwPNea_-PQGSIGaosKBNfieJ35bgFlIXRWePRjX4U7Lg3-e5jXrVWlfIITODnjNiyx8nkASWyUOKgZYaLZeUrtuQqBvuUdMxJKaSwHcg6scoJoF4m4c7v43yfRUpm5XqoSNxSXD5DdOzhdENPD2O8ejgfVXOptr5EMoyEZ7wGdQiw'
                        self.signed_invoice_str = signed_invoice
                        self.signed_qr_code_str = signed_qrcode

                        info_dtls = json_response.get("InfoDtls", [])

                        if info_dtls:
                            for i, error in enumerate(info_dtls):
                                desc_list = error.get('Desc', [])
                                for desc in desc_list:
                                    error_message = desc.get('ErrorMessage', 'No error message provided')
                                    log_obj.line_ids.create({
                                        'process_log_id': log_obj.id,
                                        'name': "Error",
                                        'res_model': 'account.move',
                                        'res_id': self.id,
                                        'resource_log': 'alankit_e-invoice',
                                        'response': json.dumps(json_response, indent=2),
                                        'message': error_message,
                                        'state': "error"
                                    })
                        # pdf = self.env.ref('rcs_alankit_einvoicing.action_report_einvoice')._render_qweb_pdf()
                        pdf = self.env['ir.actions.report']._render_qweb_pdf('rcs_alankit_einvoicing.action_report_einvoice',
                                                                             res_ids=self.ids)
                        b64_pdf = base64.b64encode(pdf[0])
                        # save pdf as attachment
                        attachment_pdf = self.env['ir.attachment'].create({
                            'name': log_name,
                            'type': 'binary',
                            'datas': b64_pdf,
                            'store_fname': log_name,
                            'res_model': self._name,
                            'res_id': self.id,
                            'mimetype': 'application/pdf'
                        })
                        return attachment_pdf


                    else:
                        self.einvoice_generated = False

                        # Extract ErrorDetails
                        error_details = json_response.get('ErrorDetails', [])

                        log_obj.sudo().update({
                            'response': json.dumps(json_response, indent=2),
                            'message': 'Failed to Generate E-invoice!'
                        })
                        if error_details:
                            # Create log lines for each error
                            for i, error in enumerate(error_details):
                                log_obj.line_ids.create({
                                    'process_log_id': log_obj.id,
                                    'name': "Error",
                                    'res_model': 'account.move',
                                    'res_id': self.id,
                                    'resource_log': 'alankit_e-invoice',
                                    'response': json.dumps(error_details,
                                                           indent=2),
                                    'message': f"{error['ErrorMessage']}",
                                    'state': "error"
                                })

                        info_dtls = json_response.get("InfoDtls", [])
                        if info_dtls:
                            for i, error in enumerate(info_dtls):
                                desc_list = error.get('Desc', {})
                                if isinstance(desc_list, dict):
                                    self.irn_no = desc_list.get('Irn', '')
                                    self.invoice_ack_no = desc_list.get('AckNo', '')
                                    self.invoice_ack_dt = desc_list.get('AckDt', '')
                                    self.einvoice_generated = True
                                    log_obj.line_ids.create({
                                        'process_log_id': log_obj.id,
                                        'name': "Error",
                                        'res_model': 'account.move',
                                        'res_id': self.id,
                                        'resource_log': 'alankit_e-invoice',
                                        'response': json.dumps(info_dtls,
                                                               indent=2),
                                        'message': f"E-invoice is already generated for this document.",
                                        'state': "error"
                                    })
                                else:
                                    self.irn_no = ''
                                    self.invoice_ack_no = ''
                                    self.invoice_ack_dt = ''

            except Exception as error:
                raise UserError(_(f"Failed! Exception: {error}"))

    def prepare_einvoice_report_data(self):
        # Signed Invoice details
        header_b64, payload_b64, signature_b64 = self.signed_invoice_str.split('.')
        signed_invoice_header_json = base64.urlsafe_b64decode(header_b64 + '==').decode('utf-8')
        signed_invoice_payload_json = base64.urlsafe_b64decode(payload_b64 + '==').decode('utf-8')
        json_string = signed_invoice_payload_json
        data = json.loads(json_string)
        inner_invoice_data = json.loads(data['data'])
        report_data = inner_invoice_data
        return report_data

    def einvoice_qr_data(self):
        """
        @usage : Generates and returns a formatted string containing e-way bill data for QR code generation.
        :param: None
        :return: str
        """
        # signed QR code details
        header_b64, payload_b64, signature_b64 = self.signed_qr_code_str.split('.')
        signed_qr_header_json = base64.urlsafe_b64decode(header_b64 + '==').decode('utf-8')
        signed_qr_payload_json = base64.urlsafe_b64decode(payload_b64 + '==').decode('utf-8')
        json_string = signed_qr_payload_json
        data = json.loads(json_string)
        inner_qr_data = json.loads(data['data'])
        einvoice_qr_data = f"{inner_qr_data}"
        return einvoice_qr_data

    def generate_einvoice_json(self, log_obj):
        invoice = self
        tax_details = self._l10n_in_prepare_edi_tax_details(invoice)
        tax_details_by_code = self._get_l10n_in_tax_details_by_line_code(tax_details.get("tax_details", {}))
        seller_details = self.prepare_seller_details(invoice, log_obj)
        is_overseas = invoice.l10n_in_gst_treatment == "overseas"
        transportation_details = self.prepare_trans_details(log_obj)
        document_details = self.prepare_document_details(invoice)
        buyer_details = self.prepare_buyer_details(invoice, log_obj, pos_state_id=invoice.l10n_in_state_id, is_overseas=is_overseas)
        dispatch_details = self.prepare_dispatch_details(invoice, log_obj)
        ship_details = self.prepare_ship_details(invoice, log_obj, is_overseas=is_overseas)
        vals_details = self.prepare_vals_details(invoice, log_obj)
        reference_details = self.prepare_reference_details(invoice, log_obj)
        lines = invoice.invoice_line_ids.filtered(lambda line: line.display_type not in ('line_note', 'line_section', 'rounding'))
        global_discount_line = lines.filtered(self._l10n_in_is_global_discount)
        lines -= global_discount_line
        # invoice_line_tax_details = tax_details.get("invoice_line_tax_details")
        invoice_line_tax_details = tax_details.get("tax_details_per_record")
        json_payload = {
            "Version": "1.1",
            "TranDtls": transportation_details,
            "DocDtls": document_details,
            "SellerDtls": seller_details,
            "BuyerDtls": buyer_details,
            "DispDtls": dispatch_details,
            "ShipDtls": ship_details,
            "ItemList": [
                self._get_l10n_in_edi_line_details(index, line, invoice_line_tax_details.get(line, {}), log_obj)
                for index, line in enumerate(lines, start=1)
            ],
            "ValDtls": vals_details,
            "RefDtls": reference_details,
            "AddlDocDtls": [
                {
                    "Url": "https://einv-apisandbox.nic.in",
                    "Docs": invoice.name,
                    "Info": invoice.ref or None
                }
            ],
        }

        if is_overseas:
            json_payload.update({
                "ExpDtls": {
                    "RefClm": tax_details_by_code.get("igst") and "Y" or "N",
                    "ForCur": invoice.currency_id.name,
                    "CntCode": invoice.partner_id.country_id.code or "",
                }
            })
            if invoice.l10n_in_shipping_bill_number:
                json_payload["ExpDtls"].update({
                    "ShipBNo": invoice.l10n_in_shipping_bill_number,
                })
            if invoice.l10n_in_shipping_bill_date:
                json_payload["ExpDtls"].update({
                    "ShipBDt": invoice.l10n_in_shipping_bill_date.strftime("%d/%m/%Y"),
                })
            if invoice.l10n_in_shipping_port_code_id:
                json_payload["ExpDtls"].update({
                    "Port": invoice.l10n_in_shipping_port_code_id.code
                })

            _logger.info("=============>Einvoice json payload %s", json_payload)
        return self._l10n_in_edi_generate_invoice_json_managing_negative_lines(invoice, json_payload)

    def _l10n_in_is_global_discount(self, line):
        return not line.tax_ids and line.price_subtotal < 0 or False
    def _l10n_in_edi_generate_invoice_json_managing_negative_lines(self, invoice, json_payload):
        """Set negative lines against positive lines as discount with same HSN code and tax rate

            With negative lines

            product name | hsn code | unit price | qty | discount | total
            =============================================================
            product A    | 123456   | 1000       | 1   | 100      |  900
            product B    | 123456   | 1500       | 2   | 0        | 3000
            Discount     | 123456   | -300       | 1   | 0        | -300

            Converted to without negative lines

            product name | hsn code | unit price | qty | discount | total
            =============================================================
            product A    | 123456   | 1000       | 1   | 100      |  900
            product B    | 123456   | 1500       | 2   | 300      | 2700

            totally discounted lines are kept as 0, though
        """
        def discount_group_key(line_vals):
            return "%s-%s"%(line_vals['HsnCd'], line_vals['GstRt'])

        def put_discount_on(discount_line_vals, other_line_vals):
            discount = discount_line_vals['AssAmt'] * -1
            discount_to_allow = other_line_vals['AssAmt']
            if float_compare(discount_to_allow, discount, precision_rounding=invoice.currency_id.rounding) < 0:
                # Update discount line, needed when discount is more then max line, in short remaining_discount is not zero
                discount_line_vals.update({
                    'AssAmt': self._l10n_in_round_value(discount_line_vals['AssAmt'] + other_line_vals['AssAmt']),
                    'IgstAmt': self._l10n_in_round_value(discount_line_vals['IgstAmt'] + other_line_vals['IgstAmt']),
                    'CgstAmt': self._l10n_in_round_value(discount_line_vals['CgstAmt'] + other_line_vals['CgstAmt']),
                    'SgstAmt': self._l10n_in_round_value(discount_line_vals['SgstAmt'] + other_line_vals['SgstAmt']),
                    'CesAmt': self._l10n_in_round_value(discount_line_vals['CesAmt'] + other_line_vals['CesAmt']),
                    'CesNonAdvlAmt': self._l10n_in_round_value(discount_line_vals['CesNonAdvlAmt'] + other_line_vals['CesNonAdvlAmt']),
                    'StateCesAmt': self._l10n_in_round_value(discount_line_vals['StateCesAmt'] + other_line_vals['StateCesAmt']),
                    'StateCesNonAdvlAmt': self._l10n_in_round_value(discount_line_vals['StateCesNonAdvlAmt'] + other_line_vals['StateCesNonAdvlAmt']),
                    'OthChrg': self._l10n_in_round_value(discount_line_vals['OthChrg'] + other_line_vals['OthChrg']),
                    'TotItemVal': self._l10n_in_round_value(discount_line_vals['TotItemVal'] + other_line_vals['TotItemVal']),
                })
                other_line_vals.update({
                    'Discount': self._l10n_in_round_value(other_line_vals['Discount'] + discount_to_allow),
                    'AssAmt': 0.00,
                    'IgstAmt': 0.00,
                    'CgstAmt': 0.00,
                    'SgstAmt': 0.00,
                    'CesAmt': 0.00,
                    'CesNonAdvlAmt': 0.00,
                    'StateCesAmt': 0.00,
                    'StateCesNonAdvlAmt': 0.00,
                    'OthChrg': 0.00,
                    'TotItemVal': 0.00,
                })
                return False
            other_line_vals.update({
                'Discount': self._l10n_in_round_value(other_line_vals['Discount'] + discount),
                'AssAmt': self._l10n_in_round_value(other_line_vals['AssAmt'] + discount_line_vals['AssAmt']),
                'IgstAmt': self._l10n_in_round_value(other_line_vals['IgstAmt'] + discount_line_vals['IgstAmt']),
                'CgstAmt': self._l10n_in_round_value(other_line_vals['CgstAmt'] + discount_line_vals['CgstAmt']),
                'SgstAmt': self._l10n_in_round_value(other_line_vals['SgstAmt'] + discount_line_vals['SgstAmt']),
                'CesAmt': self._l10n_in_round_value(other_line_vals['CesAmt'] + discount_line_vals['CesAmt']),
                'CesNonAdvlAmt': self._l10n_in_round_value(other_line_vals['CesNonAdvlAmt'] + discount_line_vals['CesNonAdvlAmt']),
                'StateCesAmt': self._l10n_in_round_value(other_line_vals['StateCesAmt'] + discount_line_vals['StateCesAmt']),
                'StateCesNonAdvlAmt': self._l10n_in_round_value(other_line_vals['StateCesNonAdvlAmt'] + discount_line_vals['StateCesNonAdvlAmt']),
                'OthChrg': self._l10n_in_round_value(other_line_vals['OthChrg'] + discount_line_vals['OthChrg']),
                'TotItemVal': self._l10n_in_round_value(other_line_vals['TotItemVal'] + discount_line_vals['TotItemVal']),
            })
            return True

        discount_lines = []
        for discount_line in json_payload['ItemList'].copy():  # to be sure to not skip in the loop:
            if discount_line['AssAmt'] < 0:
                discount_lines.append(discount_line)
                json_payload['ItemList'].remove(discount_line)
        if not discount_lines:
            return json_payload

        lines_grouped_and_sorted = defaultdict(list)
        for line in sorted(json_payload['ItemList'], key=lambda i: i['AssAmt'], reverse=True):
            lines_grouped_and_sorted[discount_group_key(line)].append(line)

        for discount_line in discount_lines:
            apply_discount_on_lines = lines_grouped_and_sorted.get(discount_group_key(discount_line), [])
            for apply_discount_on in apply_discount_on_lines:
                if put_discount_on(discount_line, apply_discount_on):
                    break
        return json_payload

    # Transaction Details"required": ["TaxSch","SupTyp"]
    def prepare_trans_details(self, log):
        tax_details = self._l10n_in_prepare_edi_tax_details(self)
        tax_details_by_code = self._get_l10n_in_tax_details_by_line_code(tax_details.get("tax_details", {}))
        is_intra_state = self.l10n_in_state_id == self.company_id.state_id

        transdtls = {
            "TaxSch": "GST",
            "SupTyp": self._l10n_in_get_supply_type(self, tax_details_by_code),
            "RegRev": tax_details_by_code.get("is_reverse_charge") and "Y" or "N",
            "EcmGstin": None,
            "IgstOnIntra": is_intra_state and tax_details_by_code.get("Igst") and "Y" or "N",
        }

        required_fields = ["TaxSch", "SupTyp"]
        missing_fields = [field for field in required_fields if not transdtls.get(field)]

        if missing_fields:
            log_message = f"Missing required fields: {', '.join(missing_fields)}"
            log.line_ids.create({
                'process_log_id': log.id,
                'name': 'Transaction',
                'res_model': 'account.move',
                'res_id': self.id,
                'resource_log': 'alankit_e-invoice',
                'message': log_message,
                'state': "error"
            })

        return transdtls if transdtls.get('SupTyp') else None

    # Document Details"required": ["Typ","No","Dt"]
    def prepare_document_details(self, move):
        date = move.date.strftime('%d/%m/%Y')

        doc_name = move.name.removeprefix('BILL/').removeprefix('RBILL/') if len(move.name) > 16 else move.name

        doc_dtls = {
            "Typ": (move.move_type == "out_refund" and "CRN") or (move.debit_origin_id and "DBN") or "INV",
            "No": doc_name,
            "Dt": date
        }
        return doc_dtls

    def _l10n_in_edi_extract_digits(self, string):
        if not string:
            return string
        matches = re.findall(r"\d+", string)
        result = "".join(matches)
        return result

    # Seller Details "required":["Gstin","LglNm","Addr1","Loc","Pin","Stcd"]
    def prepare_seller_details(self, move, log, is_overseas=False):
        company_partner = move.company_id.partner_id
        pin_code = self._l10n_in_edi_extract_digits(company_partner.zip)

        seller_details = {
            "Gstin": company_partner.vat or 'URP',
            "LglNm": company_partner.commercial_partner_id.name,
            "Addr1": company_partner.street or "",
            "Loc": company_partner.city or "",
            "Pin": pin_code and int(pin_code) or "",
            "Stcd": company_partner.state_id.l10n_in_tin or "",
        }
        if company_partner.phone:
            seller_details.update({"Ph": self._l10n_in_edi_extract_digits(company_partner.phone)})
        if company_partner.email:
            seller_details.update({"Em": company_partner.email})
        if company_partner.street2:
            seller_details.update({"Addr2": company_partner.street2})

        # For no country I would suppose it is India, so not sure this is super right
        if is_overseas and (not company_partner.country_id or company_partner.country_id.code != 'IN'):
            seller_details.update({
                "Gstin": "URP",
                "Pin": 999999,
                "Stcd": "96",
            })

        required_fields = ["Gstin", "LglNm", "Addr1", "Loc", "Pin", "Stcd"]
        missing_fields = [field for field in required_fields if not seller_details.get(field)]

        if missing_fields:
            log_message = f"Missing required fields: {', '.join(missing_fields)}"
            log.line_ids.create({
                'process_log_id': log.id,
                'name': 'Seller',
                'res_model': 'account.move',
                'res_id': move.id,
                'resource_log': 'alankit_e-invoice',
                'message': log_message,
                'state': "error"
            })

        return seller_details

    # Buyer Details "required":["Gstin","LglNm","Pos","Addr1","Loc","Stcd"]
    def prepare_buyer_details(self, move, log, pos_state_id=False, is_overseas=False):
        buyer = move.partner_id
        pin_code = self._l10n_in_edi_extract_digits(buyer.zip)
        buyer_details = {
            "Gstin": buyer.vat or 'URP',
            "LglNm": buyer.commercial_partner_id.name,
            "Addr1": buyer.street,
            "Loc": buyer.city,
            "Pin": pin_code and int(pin_code) or "",
            "Stcd": buyer.state_id.l10n_in_tin or "",
            "Pos": buyer.state_id.l10n_in_tin or "",
        }
        if buyer.phone:
            buyer_details.update({"Ph": self._l10n_in_edi_extract_digits(buyer.phone)})
        if buyer.email:
            buyer_details.update({"Em": buyer.email})
        if buyer.street2:
            buyer_details.update({"Addr2": buyer.street2})
        if pos_state_id:
            buyer_details.update({"Pos": pos_state_id.l10n_in_tin or ""})
        # For no country I would suppose it is India, so not sure this is super right
        if is_overseas and (not buyer.country_id or buyer.country_id.code != 'IN'):
            buyer_details.update({
                "Gstin": "URP",
                "Pin": 999999,
                "Stcd": "96",
                "Pos": "96",
            })

        required_fields = ["Gstin", "LglNm", "Pos", "Addr1", "Loc", "Pin", "Stcd"]
        missing_fields = [field for field in required_fields if not buyer_details.get(field)]

        if missing_fields:
            log_message = f"Missing required fields: {', '.join(missing_fields)}"
            log.line_ids.create({
                'process_log_id': log.id,
                'name': 'Buyer',
                'res_model': 'account.move',
                'res_id': move.id,
                'resource_log': 'alankit_e-invoice',
                'message': log_message,
                'state': "error"
            })

        return buyer_details

    # Dispatch Details "required":["Nm","Addr1","Loc","Pin","Stcd"]
    def prepare_dispatch_details(self, move, log):
        company = move.company_id.partner_id
        pin_code = self._l10n_in_edi_extract_digits(company.zip)
        dispatch_details = {
            "Nm": company.name or company.commercial_partner_id.name,
            "Addr1": company.street,
            "Loc": company.city,
            "Pin": pin_code and int(pin_code) or "",
            "Stcd": company.state_id.l10n_in_tin or "",
        }
        if company.street2:
            dispatch_details.update({"Addr2": company.street2})

        required_fields = ["Nm", "Addr1", "Loc", "Pin", "Stcd"]
        missing_fields = [field for field in required_fields if not dispatch_details.get(field)]

        if missing_fields:
            log_message = f"Missing required fields: {', '.join(missing_fields)}"
            log.line_ids.create({
                'process_log_id': log.id,
                'name': 'Dispatch',
                'res_model': 'account.move',
                'res_id': move.id,
                'resource_log': 'alankit_e-invoice',
                'message': log_message,
                'state': "error"
            })

        return dispatch_details

    # Ship Details "required":["LglNm","Addr1","Loc","Pin","Stcd"]
    def prepare_ship_details(self, move, log, is_overseas=False):
        ship_partner = move.partner_id
        pin_code = self._l10n_in_edi_extract_digits(ship_partner.zip)
        if self.partner_shipping_id:
            state_code = self.partner_shipping_id.state_id.l10n_in_tin
        else:
            state_code = ship_partner.state_id.l10n_in_tin

        if self.partner_shipping_id:
            shipping_partner = self.partner_shipping_id
            ship_details = {
                "LglNm": shipping_partner.name or ship_partner.name,
                "Addr1": shipping_partner.street,
                "Loc": shipping_partner.city,
                "Pin": self._l10n_in_edi_extract_digits(shipping_partner.zip),
                "Stcd": state_code
            }
            if ship_partner.street2:
                ship_details.update({"Addr2": shipping_partner.street2})
        else:
            ship_details = {
                "LglNm": ship_partner.name,
                "Addr1": ship_partner.street,
                "Loc": ship_partner.city,
                "Pin": pin_code,
                "Stcd": state_code
            }
            if ship_partner.street2:
                ship_details.update({"Addr2": ship_partner.street2})
        # For no country I would suppose it is India, so not sure this is super right
        if is_overseas and (not ship_partner.country_id or ship_partner.country_id.code != 'IN'):
            ship_details.update({
                "Gstin": "URP",
                "Pin": 999999,
                "Stcd": "96",
                "Pos": "96",
            })

        required_fields = ["LglNm", "Addr1", "Loc", "Pin", "Stcd"]
        missing_fields = [field for field in required_fields if not ship_details.get(field)]

        if missing_fields:
            log_message = f"Missing required fields: {', '.join(missing_fields)}"
            log.line_ids.create({
                'process_log_id': log.id,
                'name': 'Ship',
                'res_model': 'account.move',
                'res_id': move.id,
                'resource_log': 'alankit_e-invoice',
                'message': log_message,
                'state': "error"
            })

        return ship_details

    # invoice Details "required":["SlNo","IsServc","HsnCd","UnitPrice","TotAmt","AssAmt","GstRt","TotItemVal"]
    def _get_l10n_in_edi_line_details(self, index, line, line_tax_details, log):
        """
        Create the dictionary with line details
        return {
            account.move.line('1'): {....},
            account.move.line('2'): {....},
            ....
        }
        """
        sign = line.move_id.is_inbound() and -1 or 1
        tax_details_by_code = self._get_l10n_in_tax_details_by_line_code(line_tax_details.get("tax_details", {}))
        quantity = line.quantity
        full_discount_or_zero_quantity = line.discount == 100.00 or float_is_zero(quantity, 3)
        if full_discount_or_zero_quantity:
            unit_price_in_inr = line.currency_id._convert(
                line.price_unit,
                line.company_currency_id,
                line.company_id,
                line.date or fields.Date.context_today(self)
            )
        else:
            unit_price_in_inr = ((sign * line.balance) / (1 - (line.discount / 100))) / quantity

        if unit_price_in_inr < 0 and quantity < 0:
            # If unit price and quantity both is negative then
            # We set unit price and quantity as positive because
            # government does not accept negative in qty or unit price
            unit_price_in_inr = unit_price_in_inr * -1
            quantity = quantity * -1

        # Fetch the batch/lot associated with this invoice line
        batch_lot = self.env['stock.lot'].search([
            ('product_id', '=', line.product_id.id),
            ('quant_ids.location_id.usage', '=', 'internal')  # Ensure the product is in stock (if needed)
        ], limit=1)
        PrdDesc = line.product_id.display_name or line.name
        invoice_details = {
            "SlNo": str(index),
            "PrdDesc": PrdDesc.replace("\n", ""),
            "IsServc": line.product_id.type == "service" and "Y" or "N",
            "HsnCd": self._l10n_in_edi_extract_digits(line.l10n_in_hsn_code),
            "Barcde": self._l10n_in_edi_extract_digits(line.product_id.barcode) or None,
            "Qty": self._l10n_in_round_value(quantity or 0.0, 3),
            "Unit": line.product_uom_id.l10n_in_code and line.product_uom_id.l10n_in_code.split("-")[0] or "OTH",
            # Unit price in company currency and tax excluded so its different then price_unit
            "UnitPrice": self._l10n_in_round_value(unit_price_in_inr, 3),
            # total amount is before discount
            "TotAmt": self._l10n_in_round_value(unit_price_in_inr * quantity),
            "Discount": self._l10n_in_round_value((unit_price_in_inr * quantity) * (line.discount / 100)),
            "AssAmt": self._l10n_in_round_value((sign * line.balance)),
            "GstRt": self._l10n_in_round_value(tax_details_by_code.get("igst_rate", 0.00) or (
                tax_details_by_code.get("cgst_rate", 0.00) + tax_details_by_code.get("sgst_rate", 0.00)), 3),
            "IgstAmt": self._l10n_in_round_value(tax_details_by_code.get("igst_amount", 0.00)),
            "CgstAmt": self._l10n_in_round_value(tax_details_by_code.get("cgst_amount", 0.00)),
            "SgstAmt": self._l10n_in_round_value(tax_details_by_code.get("sgst_amount", 0.00)),
            "CesRt": self._l10n_in_round_value(tax_details_by_code.get("cess_rate", 0.00), 3),
            "CesAmt": self._l10n_in_round_value(tax_details_by_code.get("cess_amount", 0.00)),
            "CesNonAdvlAmt": self._l10n_in_round_value(
                tax_details_by_code.get("cess_non_advol_amount", 0.00)),
            "StateCesRt": self._l10n_in_round_value(tax_details_by_code.get("state_cess_rate_amount", 0.00), 3),
            "StateCesAmt": self._l10n_in_round_value(tax_details_by_code.get("state_cess_amount", 0.00)),
            "StateCesNonAdvlAmt": self._l10n_in_round_value(
                tax_details_by_code.get("state_cess_non_advol_amount", 0.00)),
            "OthChrg": self._l10n_in_round_value(tax_details_by_code.get("other_amount", 0.00)),
            "TotItemVal": self._l10n_in_round_value(((sign * line.balance) + line_tax_details.get("tax_amount", 0.00))),
            "BchDtls": {
                # "required":["Nm"]
                "Nm": batch_lot.name if batch_lot else "No Batch",  # Batch Number
                "ExpDt": batch_lot.expiration_date.strftime('%d/%m/%Y') if batch_lot and hasattr(batch_lot,
                                                                                                 'expiration_date') and batch_lot.expiration_date else None,
                # Expiry Date
                "WrDt": batch_lot.create_date.strftime('%d/%m/%Y') if batch_lot else None  # Manufacturing Date
            },
            "AttribDtls": [
                {
                    "Nm": line.name,
                    "Val": str(line.price_unit)
                }
            ]
        }
        required_fields = ["SlNo", "PrdDesc", "IsServc", "HsnCd", "Qty", "Unit", "UnitPrice", "AssAmt", "GstRt"]
        # Check if the field is None (assuming 0.0 is a valid value)
        missing_fields = [field for field in required_fields if invoice_details.get(field) is None]

        if missing_fields:
            log_message = f"Missing required fields: {', '.join(missing_fields)}"
            log.line_ids.create({
                'process_log_id': log.id,
                'name': 'Invoice Line',
                'res_model': 'account.move.line',
                'res_id': line.id,
                'resource_log': 'alankit_e-invoice',
                'message': log_message,
                'state': "error"
            })

        return invoice_details

    # prepare value details "required":["AssVal","TotInvVal"]
    def prepare_vals_details(self, move, log):
        tax_details = self._l10n_in_prepare_edi_tax_details(self)
        tax_details_by_code = self._get_l10n_in_tax_details_by_line_code(tax_details.get("tax_details", {}))
        sign = self.is_inbound() and -1 or 1
        lines = move.invoice_line_ids.filtered(
            lambda line: line.display_type not in ('line_note', 'line_section', 'rounding'))
        global_discount_line = lines.filtered(self._l10n_in_is_global_discount)
        lines -= global_discount_line
        rounding_amount = sum(line.balance for line in move.line_ids if line.display_type == 'rounding') * sign
        global_discount_amount = sum(line.balance for line in global_discount_line) * sign * -1

        vals = {
            "AssVal": self._l10n_in_round_value(tax_details.get("base_amount") + global_discount_amount),
            "CgstVal": self._l10n_in_round_value(tax_details_by_code.get("cgst_amount", 0.00)),
            "SgstVal": self._l10n_in_round_value(tax_details_by_code.get("sgst_amount", 0.00)),
            "IgstVal": self._l10n_in_round_value(tax_details_by_code.get("igst_amount", 0.00)),
            "CesVal": self._l10n_in_round_value((
                tax_details_by_code.get("cess_amount", 0.00)
                + tax_details_by_code.get("cess_non_advol_amount", 0.00)),
            ),
            "StCesVal": self._l10n_in_round_value((
                tax_details_by_code.get("state_cess_amount", 0.00)
                + tax_details_by_code.get("state_cess_non_advol_amount", 0.00)),
            ),
            "Discount": self._l10n_in_round_value(global_discount_amount),
            "RndOffAmt": self._l10n_in_round_value(
                rounding_amount),
            "TotInvVal": self._l10n_in_round_value(
                (tax_details.get("base_amount") + tax_details.get("tax_amount") + rounding_amount)),
            }

        if move.company_currency_id != move.currency_id:
            vals.update({
                "TotInvValFc": self._l10n_in_round_value(
                    (tax_details.get("base_amount_currency") + tax_details.get("tax_amount_currency")) * sign)
            })

        required_fields = ["AssVal", "TotInvVal"]
        missing_fields = [field for field in required_fields if not vals.get(field)]

        if missing_fields:
            log_message = f"Missing required fields: {', '.join(missing_fields)}"
            log.line_ids.create({
                'process_log_id': log.id,
                'name': 'Values',
                'res_model': 'account.move',
                'res_id': self.id,
                'resource_log': 'alankit_e-invoice',
                'message': log_message,
                'state': "error"
            })

        return vals

    # prepare_eway_details "required": ["Distance"]
    def prepare_eway_details(self, move, log):
        date_t = move.transportation_doc_date.strftime('%d/%m/%Y')
        eway_details = {
            "TransId": move.transportation_gstin,
            "TransName": move.transporter_id.name,
            "Distance": move.transportation_distance,
            "TransDocNo": move.transportation_doc_name,
            "TransDocDt": date_t,
            "VehNo": move.vehicle_no,
            "VehType": move.vehicle_type,
            "TransMode": move.transporter_in_mode
        }

        required_fields = ["Distance"]
        missing_fields = []
        for field in required_fields:
            if field not in eway_details or not eway_details[field]:
                missing_fields.append(field)

        if missing_fields:
            log_message = f"Missing required fields: {', '.join(missing_fields)}"
            log.line_ids.create({
                'process_log_id': log.id,
                'name': 'E-Way Bill',
                'res_model': 'account.move',
                'res_id': self.id,
                'resource_log': 'alankit_e-invoice',
                'message': log_message,
                'state': "error"
            })

        return eway_details

    # prepare invoice details "required":[" InvStDt "," InvEndDt "]
    def prepare_reference_details(self, invoice, log):
        start_date = invoice.create_date.strftime('%d/%m/%Y')
        accounting_date = invoice.invoice_date_due.strftime('%d/%m/%Y')
        invoice_date = self.invoice_date.strftime('%d/%m/%Y')
        reference_data = {
            "DocPerdDtls": {
                "InvStDt": start_date,
                "InvEndDt": accounting_date
            },
            "PrecDocDtls": [
                {
                    "InvNo": invoice.name.removeprefix('BILL/').removeprefix('RBILL/') if len(
                        invoice.name) > 16 else invoice.name,
                    "InvDt": invoice_date
                }
            ],
        }

        required_fields = ["DocPerdDtls"]
        missing_fields = []
        for field in required_fields:
            if field not in reference_data or not reference_data[field]:
                missing_fields.append(field)

        if missing_fields:
            log_message = f"Missing required fields: {', '.join(missing_fields)}"
            log.line_ids.create({
                'process_log_id': log.id,
                'name': 'Reference',
                'res_model': 'account.move',
                'res_id': self.id,
                'resource_log': 'alankit_e-invoice',
                'message': log_message,
                'state': "error"
            })

        return reference_data

    @api.model
    def _l10n_in_prepare_edi_tax_details(self, move, in_foreign=False, filter_invl_to_apply=None):
        def l10n_in_grouping_key_generator(base_line, tax_data):
            invl = base_line['record']
            tax = tax_data['tax']
            tags = tax.invoice_repartition_line_ids.tag_ids
            line_code = "other"
            if not invl.currency_id.is_zero(tax_data['tax_amount_currency']):
                if any(tag in tags for tag in self.env.ref("l10n_in.tax_tag_cess")):
                    if tax.amount_type != "percent":
                        line_code = "cess_non_advol"
                    else:
                        line_code = "cess"
                elif any(tag in tags for tag in self.env.ref("l10n_in.tax_tag_state_cess")):
                    if tax.amount_type != "percent":
                        line_code = "state_cess_non_advol"
                    else:
                        line_code = "state_cess"
                else:
                    for gst in ["cgst", "sgst", "igst"]:
                        if any(tag in tags for tag in self.env.ref("l10n_in.tax_tag_%s" % (gst))):
                            line_code = gst
                        # need to separate rc tax value so it's not pass to other values
                        if any(tag in tags for tag in self.env.ref("l10n_in.tax_tag_%s_rc" % (gst))):
                            line_code = gst + '_rc'
            return {
                "tax": tax,
                "base_product_id": invl.product_id,
                "tax_product_id": invl.product_id,
                "base_product_uom_id": invl.product_uom_id,
                "tax_product_uom_id": invl.product_uom_id,
                "line_code": line_code,
            }

        def l10n_in_filter_to_apply(base_line, tax_values):
            if base_line['record'].display_type == 'rounding':
                return False
            return True

        return move._prepare_edi_tax_details(
            filter_to_apply=l10n_in_filter_to_apply,
            grouping_key_generator=l10n_in_grouping_key_generator,
            filter_invl_to_apply=filter_invl_to_apply,
        )

    def _prepare_edi_tax_details(self, filter_to_apply=None, filter_invl_to_apply=None, grouping_key_generator=None):
        ''' Compute amounts related to taxes for the current invoice. '''
        return self._prepare_invoice_aggregated_taxes(
            filter_invl_to_apply=filter_invl_to_apply,
            filter_tax_values_to_apply=filter_to_apply,
            grouping_key_generator=grouping_key_generator,
        )

    def _get_l10n_in_tax_details_by_line_code(self, tax_details):
        l10n_in_tax_details = {}
        for tax_detail in tax_details.values():
            if tax_detail["tax"].l10n_in_reverse_charge:
                l10n_in_tax_details.setdefault("is_reverse_charge", True)
            l10n_in_tax_details.setdefault("%s_rate" % (tax_detail["line_code"]), tax_detail["tax"].amount)
            l10n_in_tax_details.setdefault("%s_amount" % (tax_detail["line_code"]), 0.00)
            l10n_in_tax_details.setdefault("%s_amount_currency" % (tax_detail["line_code"]), 0.00)
            l10n_in_tax_details["%s_amount" % (tax_detail["line_code"])] += tax_detail["tax_amount"]
            l10n_in_tax_details["%s_amount_currency" % (tax_detail["line_code"])] += tax_detail["tax_amount_currency"]
        return l10n_in_tax_details

    def _l10n_in_get_supply_type(self, move, tax_details_by_code):
        supply_type = "B2B"
        if move.l10n_in_gst_treatment in ("overseas", "special_economic_zone") and tax_details_by_code.get(
                "igst_amount"):
            supply_type = move.l10n_in_gst_treatment == "overseas" and "EXPWP" or "SEZWP"
        elif move.l10n_in_gst_treatment in ("overseas", "special_economic_zone"):
            supply_type = move.l10n_in_gst_treatment == "overseas" and "EXPWOP" or "SEZWOP"
        elif move.l10n_in_gst_treatment == "deemed_export":
            supply_type = "DEXP"
        return supply_type

    @api.model
    def _l10n_in_round_value(self, amount, precision_digits=2):
        """
            This method is call for rounding.
            If anything is wrong with rounding then we quick fix in method
        """
        value = round(amount, precision_digits)
        # avoid -0.0
        return value if value else 0.0

    def _l10n_in_edi_extract_digits(self, string):
        if not string:
            return string
        matches = re.findall(r"\d+", string)
        result = "".join(matches)
        return result

    def cancel_einvoice(self):
        ctx = dict(self.env.context)
        ctx['invoice_cancel'] = True
        ctx['einvoice_active_id'] = self.id
        return {
            'name': 'Add Reason',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'alankit.einvoice.cancel',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': ctx,
        }

    def open_alankit_einvoice_logs(self):
        log_ids = self.env['common.process.log'].search([('res_id', '=', self.id), ('res_model', '=', 'account.move'),
                                                         ('resource_log', '=', 'alankit_e-invoice')])
        if log_ids:
            view_form_id = self.env.ref('rcs_process_logs.common_process_log_form').id
            view_tree_id = self.env.ref('rcs_process_logs.common_process_log_tree').id
            action = {
                'type': 'ir.actions.act_window',
                'domain': [('id', 'in', log_ids.ids)],
                'view_mode': 'list,form',
                'name': _('Common Logs'),
                'res_model': 'common.process.log',
            }
            if len(log_ids.ids) == 1:
                action.update({'views': [(view_form_id, 'form')], 'res_id': log_ids.id})
            else:
                action['views'] = [(view_tree_id, 'list'), (view_form_id, 'form')]
            return action
