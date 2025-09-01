import requests
import json
import pytz
import base64
import re
import logging
from base64 import b64encode
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from Crypto.Util.Padding import pad
from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
from .error_codes import ERROR_CODES

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    transporter_in_mode = fields.Selection([
        ("1", "By Road"),
        ("2", "Rail"),
        ("3", "Air"),
        ("4", "Ship")],
        string="Transportation Mode", tracking=True)
    transportation_distance = fields.Integer(
        string='Distance (Km) ',
        help="Distance of transportation [Distance between source and destination PIN codes]"
    )
    transportation_doc_name = fields.Char(string="TransDocNo", copy=False)
    transportation_doc_date = fields.Date(string="TransDocDt", default=fields.Date.today)
    vehicle_no = fields.Char(string='Vehicle Number')
    vehicle_type = fields.Selection([
        ("R", "Regular"),
        ("O", "ODC")],
        string="Vehicle Type", tracking=True)
    sub_supply_type = fields.Selection(
        [
            ('1', 'Supply'),
            ('2', 'Import'),
            ('3', 'Export'),
            ('4', 'Job Work'),
            ('5', 'For Own Use'),
            ('6', 'Job work Returns'),
            ('7', 'Sales Return'),
            ('8', 'Others'),
            ('9', 'SKD/CKD'),
            ('10', 'Line Sales'),
            ('11', 'Recipient Not Known'),
            ('12', 'Exhibition or Fairs'),
        ],
        string='Sub Supply Type', default="1",
        help="Sub types of Supply like supply, export, Job Work etc."
    )
    sub_supply_desc = fields.Char(string="Sub Supply Description")
    transporter_id = fields.Many2one('res.partner', string='Transport')
    transportation_gstin = fields.Char(related='transporter_id.vat', string='Transin/GSTIN', tracking=True,
                                     readonly=False)
    transporter_contact_no = fields.Char(string='Contact No', tracking=True, readonly=False)

    eway_bill_generated = fields.Boolean(copy=False)
    eway_bill_canceled = fields.Boolean(copy=False, readonly=True)
    eway_bill_no = fields.Char(string='E-way Bill No', readonly=True, copy=False)
    eway_bill_date = fields.Char(string='E-way Bill Date', readonly=True, copy=False)
    eway_bill_valid_till = fields.Char(string='E-way Bill Valid Till', readonly=True, copy=False)
    eway_bill_cancel_reason = fields.Char('Eway bill cancel reason', copy=False)
    eway_bill_cancel_date = fields.Char(string='E-way Bill Cancel Date', readonly=True, copy=False)
    ewaybill_log_count = fields.Integer(string="Alankit E-way Bill Logs", compute='_get_alankit_ewaybill_logs')

    def _get_alankit_ewaybill_logs(self):
        """
            @usage: Alankit log Count
        """
        for rec in self:
            log_ids = self.env['common.process.log'].search(
                [('res_id', '=', rec.id), ('res_model', '=', 'account.move'),
                 ('resource_log', '=', 'alankit_eway_bill')])
            rec.ewaybill_log_count = len(log_ids)

    @api.model
    def create(self, values):
        """
        :param values: Transportation document name
        :return: Created transportation_doc_name
        """
        if 'transportation_doc_name' not in values or not values['transportation_doc_name']:
            sequence = self.env['ir.sequence'].next_by_code('account.move.transportation_doc') or 'TRAN/00001'
            values['transportation_doc_name'] = sequence
        return super(AccountMove, self).create(values)

    # Encryption by the decrypted sek key
    def encrypt_ewaybill_data_by_symmetric_key(self, json_data, decrypted_sek):
        """
        Encrypt the JSON payload using the provided decrypted SEK (Symmetric Encryption Key)

        :param json_data: dict
            payload json formatted data
        :param decrypted_sek: decrypted sek key
        :return: encrypted JSON payload data
        :raises Exception:
                If decryption fails, the exception is raised
        """
        sek_b = decrypted_sek
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

    def decrypt_ewaybill_data_by_symmetric_key(self, encrypted_sek, app_key):
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

    def static_ewaybill_response(self):
        ewaybill_data = {
            "supplyType": "O",
            "subSupplyType": "1",
            "subSupplyDesc": "TESTING",
            "docType": "INV",
            "docNo": "INV/2024/00006",
            "docDate": "11/09/2024",
            "fromGstin": "07AGAPA5363L002",
            "fromTrdName": "YourCompany",
            "fromAddr1": "250 Executive Park Blvd, Suite 3400",
            "fromPlace": "Daryaganj",
            "fromPincode": 110002,
            "actFromStateCode": 7,
            "fromStateCode": 7,
            "toGstin": "29AWGPV7107B1Z1",
            "toTrdName": "Gemini Furniture",
            "toAddr1": "123, MG Road",
            "toPlace": "Bengaluru",
            "toPincode": 560001,
            "actToStateCode": 29,
            "toStateCode": 29,
            "transactionType": "1",
            "dispatchFromTradeName": "Kishor Kumari",
            "shipToTradeName": "Jeya Rosini",
            "otherValue": 0.0,
            "totalValue": 0.0,
            "cgstValue": 0.0,
            "sgstValue": 0.0,
            "igstValue": 2.84,
            "cessValue": 0.0,
            "cessNonAdvolValue": 0.0,
            "totInvValue": 15.8,
            "transporterId": "12AWGPV7107B1Z1",
            "transporterName": "Azure Interior",
            "transDocNo": False,
            "transMode": "1",
            "transDistance": 2010,
            "transDocDate": "11/09/2024",
            "vehicleNo": "DL03HR2004",
            "vehicleType": "R",
            "itemList": [
                {
                    "product_name": "Storage Box",
                    "product_description": "[E-COM08] Storage Box",
                    "quantity": 1.0,
                    "unit_of_product": "UNT",
                    "taxable_amount": 15.8,
                    "igstRate": 18.0,
                }
            ],
        }
        return ewaybill_data

    @api.onchange('transporter_id')
    def onchange_transporter_details(self):
        if self.transporter_id:
            self.transportation_gstin = self.transporter_id.vat
            self.transporter_contact_no = self.transporter_id.phone

    # Generate e-way bill
    def create_eway_bill(self):
        """
        @usage: Generate EwayBill through Alankit API
        """
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
            _logger.info("=============>Generated Eway bill SEk key %s", encrypted_sek)
            app_key = base64.b64decode(instance.app_key)
            key = self.decrypt_ewaybill_data_by_symmetric_key(encrypted_sek, app_key)
            log_name = "%s_Alankit_E-way_Bill" % (self.name.replace("/", "_"))
            log_obj = self.env['common.process.log'].sudo().create({'name': log_name,
                                                                    'res_model': 'account.move',
                                                                    'res_id': self.id,
                                                                    'resource_log': 'alankit_eway_bill'})
            json_data = self.generate_ewaybill_json(log_obj)
            # json_data = self.static_ewaybill_response()
            print(json_data)
            _logger.info("=============>Generated Eway bill json %s", json_data)
            generate_json = self.encrypt_ewaybill_data_by_symmetric_key(json_data, key)
            try:
                _logger.info("=============>Generated Eway bill json %s", generate_json)
                url = instance.prepare_eway_bill_url()
                _logger.info("=============>Generated Eway bill URL %s", url)
                headers = {
                    'Content-Type': 'application/json',
                    'Ocp-Apim-Subscription-Key': instance.subscription_key,
                    'gstin': instance.gstin,
                    'authtoken': instance.ewaybill_access_token
                }
                payload = json.dumps({"action": "GENEWAYBILL", "data": generate_json})
                response = requests.request("POST", url, headers=headers, data=payload)
                if response.status_code == 200:
                    json_response = response.json()
                    _logger.info("=============>Response Eway bill %s", json_response)
                    if json_response.get('status') == '1':
                        self.eway_bill_generated = True
                        data = json_response.get("data")
                        data_decrypt = self.decrypt_ewaybill_data_by_symmetric_key(data, key)
                        print(data_decrypt)
                        info = json.loads(data_decrypt.decode())
                        # Update the log object once
                        log_obj.sudo().update({
                            'response': json.dumps(info, indent=2),
                            'message': 'Eway Bill Generated!'
                        })
                        _logger.info(f"Alankit api Response : {json.dumps(json_response, indent=4)}")

                        if isinstance(info, dict):
                            self.eway_bill_no = info.get('ewayBillNo')
                            self.eway_bill_date = info.get('ewayBillDate')
                            self.eway_bill_valid_till = info.get('validUpto')

                        if info.get("alert"):
                            alert = info.get("alert")
                            # Use the existing log object to create a line
                            log_obj.line_ids.create({
                                'process_log_id': log_obj.id,
                                'name': "Error",
                                'res_model': 'account.move',
                                'res_id': self.id,
                                'resource_log': 'alankit_eway_bill',
                                'message': f"{alert}",
                                'state': "error"
                            })
                        # pdf = self.env.ref('rcs_alankit_eway_bill.action_invoice_report_ewaybill')._render_qweb_pdf(self.ids)
                        pdf = self.env['ir.actions.report']._render_qweb_pdf('rcs_alankit_eway_bill.action_invoice_report_ewaybill', res_ids=self.ids)
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
                        self.eway_bill_generated = False
                        errors = base64.b64decode(json_response.get('error', [])).decode()
                        response_errors_str = json.loads(errors)['errorCodes']
                        _logger.info("=============>Response Eway bill Error List %s", response_errors_str)
                        response_errors = [code.strip() for code in response_errors_str.split(',') if code.strip()]

                        log_obj.sudo().update({
                            'response': json.dumps(json_response, indent=2),
                            'message': 'Failed to Generate Eway Bill!'
                        })

                        # Fetch the error list from the function
                        # Create log lines for each found error
                        if errors:
                            for i, error_code in enumerate(response_errors):
                                error_desc = ERROR_CODES.get(error_code)
                                log_obj.line_ids.create({
                                    'process_log_id': log_obj.id,
                                    'name': f"Error {error_code}",
                                    'res_model': 'account.move',
                                    'res_id': self.id,
                                    'resource_log': 'alankit_eway_bill',
                                    'message': f"{error_desc}",
                                    'state': "error"
                                })

            except Exception as error:
                raise UserError(_(f"Failed! Exception: {error}"))

    # Generate E-way Bill Json
    # "required": ["supplyType", "subSupplyType", "docType", "docNo", "docDate", "fromGstin", "fromPincode",
    #              "fromStateCode", "toGstin", "toPincode", "toStateCode", "transDistance", "itemList", "actToStateCode",
    #              "actFromStateCode", "totInvValue", "transactionType"]
    def generate_ewaybill_json(self, log):
        """
        :param log: Log object associated with the current transaction or process
        :return: Payload JSON formatted data for e-way bill generation
        """

        def get_transaction_type(seller_details, dispatch_details, buyer_details, ship_to_details):
            """
                1 - Regular
                2 - Bill To - Ship To
                3 - Bill From - Dispatch From
                4 - Combination of 2 and 3
            """
            if seller_details != dispatch_details and buyer_details != ship_to_details:
                return 4
            elif seller_details != dispatch_details:
                return 3
            elif buyer_details != ship_to_details:
                return 2
            else:
                return 1

        tax_details = self._l10n_in_prepare_edi_tax_details(self)
        tax_details_by_code = self._get_l10n_in_tax_details_by_line_code(tax_details.get("tax_details", {}))
        sign = self.is_inbound() and -1 or 1
        extract_digits = self._l10n_in_edi_extract_digits
        invoice_line_tax_details = tax_details.get("tax_details_per_record")
        supply_type = self.determine_inward_outward()
        invoice_date = self.invoice_date.strftime('%d/%m/%Y')
        # If supplyType is outward ('O'), consignor is the company and consignee is the partner
        # If supplyType is inward ('I'), consignor is the partner and consignee is the company
        if supply_type == 'I':
            consignor = self.partner_id
            consignee = self.company_id.partner_id
        else:
            consignor = self.company_id.partner_id
            consignee = self.partner_id
        document_name = ''
        if len(self.name) > 16:
            document_name = self.name.replace('/', '')
            if len(document_name) > 16:
                document_name = self.document_name.lstrip('BILL/').lstrip('RBILL/')
        else:
            document_name = self.name

        json_payload = {
            # "supplyType": self.is_purchase_document(include_receipts=True) and "I" or "O",
            "supplyType": supply_type,
            "subSupplyType": self.sub_supply_type,
            "subSupplyDesc": self.sub_supply_desc,
            "docType": self.move_type == "out_refund" and "CRN" or "INV",
            "docNo": document_name,
            "docDate": invoice_date,
            "fromGstin": consignor.vat or 'URP',
            # "fromGstin": "07AGAPA5363L002",
            "fromTrdName": consignor.name,
            "fromAddr1": consignor.street,
            "fromPlace": consignor.city,
            "fromPincode": consignor.country_id.code == "IN" and int(extract_digits(consignor.zip)) or "",
            "actFromStateCode": int(consignor.state_id.l10n_in_tin) if consignor.state_id.l10n_in_tin else 97,
            "fromStateCode": int(consignor.state_id.l10n_in_tin) if consignor.state_id.l10n_in_tin else 99,
            "toGstin": consignee.vat or 'URP',
            # "toGstin": '07AGAPA5363L002',
            "toTrdName": consignee.name,
            "toAddr1": consignee.street,
            "toPlace": consignee.city,
            "toPincode": int(consignee.zip),
            "actToStateCode": int(consignee.state_id.l10n_in_tin) if consignee.state_id.l10n_in_tin else 97,
            "toStateCode": int(consignee.state_id.l10n_in_tin) if consignee.state_id.l10n_in_tin else 99,
            "transDistance": self.transportation_distance,
            "transactionType": get_transaction_type(self.partner_id, self.partner_shipping_id,
                                                    self.company_id.partner_id, self.company_id.partner_id),
            "dispatchFromTradeName": consignor.commercial_partner_id.name,
            "shipToTradeName": consignee.commercial_partner_id.name,
            "otherValue": self._l10n_in_round_value(tax_details_by_code.get("other_amount", 0.00)),
            "totalValue": self._l10n_in_round_value(
                (tax_details.get("base_amount", 0.00))),
            "cgstValue": self._l10n_in_round_value(tax_details_by_code.get("cgst_amount", 0.00)),
            "sgstValue": self._l10n_in_round_value(tax_details_by_code.get("sgst_amount", 0.00)),
            "igstValue": self._l10n_in_round_value(tax_details_by_code.get("igst_amount", 0.00)),
            "cessValue": self._l10n_in_round_value(tax_details_by_code.get("cess_amount", 0.00)),
            "cessNonAdvolValue": self._l10n_in_round_value(
                tax_details_by_code.get("cess_non_advol_amount", 0.00)),
            "totInvValue": self._l10n_in_round_value(
                (tax_details.get("base_amount", 0.00) + tax_details.get("tax_amount", 0.00))),

            "itemList": [
                self._get_l10n_in_rcs_ewaybill_line_details(line, line_tax_details, sign)
                for line, line_tax_details in invoice_line_tax_details.items()
            ], }

        is_overseas = self.l10n_in_gst_treatment in ("overseas", "special_economic_zone")
        if self.is_purchase_document(include_receipts=True):
            if is_overseas:
                json_payload.update({"fromStateCode": 99})
            if is_overseas and self.partner_shipping_id.state_id.country_id.code != "IN":
                json_payload.update({
                    "actFromStateCode": 97,
                    "fromPincode": 999999,
                })
            else:
                json_payload.update({
                    "actFromStateCode": self.partner_shipping_id.state_id.l10n_in_tin and int(
                        self.partner_shipping_id.state_id.l10n_in_tin) or "",
                    "fromPincode": int(extract_digits(self.partner_shipping_id.zip)),
                })
        else:
            if is_overseas:
                json_payload.update({"toStateCode": 99})
            if is_overseas and consignee.state_id.country_id.code != "IN":
                json_payload.update({
                    "actToStateCode": 97,
                    "toPincode": 999999,
                })
            else:
                json_payload.update({
                    "actToStateCode": int(consignee.state_id.l10n_in_tin),
                    "toPincode": int(extract_digits(consignee.zip)),
                })

        if self.transporter_in_mode == "5":
            json_payload.update({
                "transporterId": self.transportation_gstin or "",
                "transporterName": self.transporter_id.name or "",
            })
        if self.transporter_in_mode in ("2", "3", "4"):
            json_payload.update({
                "transMode": self.transporter_in_mode,
                "transDocNo": self.transportation_doc_name or "",
                "transDocDate": self.transportation_doc_date and
                                self.transportation_doc_date.strftime("%d/%m/%Y") or "",
            })
        if self.transporter_in_mode == "1":
            json_payload.update({
                "transMode": self.transporter_in_mode,
                "vehicleNo": self.vehicle_no or "",
                "vehicleType": self.vehicle_type or "",
            })

        if self.sub_supply_type:
            is_outward = "I" if self.is_purchase_document(include_receipts=True) else "O"
            json_payload.update({
                "docType": (
                    # Outward Transactions
                    "INV" if is_outward == "O" and self.sub_supply_type in ["1", "3", "9"] else
                    "CHL" if is_outward == "O" and self.sub_supply_type in ["4", "5", "7", "10", "11", "12"] else
                    # Inward Transactions
                    "INV" if is_outward == "I" and self.sub_supply_type in ["1", "9"] else
                    "BOE" if is_outward == "I" and self.sub_supply_type in ["2"] else
                    "CHL" if is_outward == "I" and self.sub_supply_type in ["6", "7", "12", "5"] else
                    # Default fallback
                    "OTH"
                )
            })

        required_fields = ["supplyType", "subSupplyType", "docType", "docNo", "docDate", "fromGstin", "fromPincode",
                           "fromStateCode", "toGstin", "toPincode", "toStateCode", "transDistance", "actToStateCode",
                           "actFromStateCode", "totInvValue", "transactionType"]
        missing_fields = [field for field in required_fields if not json_payload.get(field)]
        if missing_fields and log:
            log_message = f"Missing required fields: {', '.join(missing_fields)}"
            log.line_ids.create({
                'process_log_id': log.id,
                'name': 'Values',
                'res_model': 'account.move',
                'res_id': self.id,
                'resource_log': 'alankit_eway_bill',
                'message': log_message,
                'state': "error"
            })
        return json_payload

    def prepare_ewaybill_report_data(self):
        """
        @usage : Prepares and returns the e-way bill report data dictionary by collecting and formatting relevant details.
        :param: None
        :return: dict
        """
        supply_type = self.determine_inward_outward()
        if supply_type == 'I':
            consignor = self.partner_id
            consignee = self.company_id.partner_id
        else:
            consignor = self.company_id.partner_id
            consignee = self.partner_id
        sign = self.is_inbound() and -1 or 1
        tax_details = self._l10n_in_prepare_edi_tax_details(self)
        report_data = self.generate_ewaybill_json(log=None)
        report_data.update({
            "Type": "Inward" if supply_type == 'I' else 'Outward',
            "subSupplyType": dict(self._fields['sub_supply_type'].selection).get(self.sub_supply_type),
            "transMode": dict(self._fields['transporter_in_mode'].selection).get(self.transporter_in_mode),
            "fromStateCode": consignor.state_id.name if consignor.state_id.l10n_in_tin else 'Other Country',
            "toStateCode": consignee.state_id.name if consignee.state_id.l10n_in_tin else 'Other Country',
            "transporterId": self.transportation_gstin,
            "transporterName": self.transporter_id.name,
            "transDocNo": self.transportation_doc_name,
            "transDocDate": self.transportation_doc_date.strftime('%d/%m/%Y'),
            "vehicleNo": self.vehicle_no,
            "vehicleType": self.vehicle_type,
            "total_tax_amt": self._l10n_in_round_value(tax_details.get("base_amount", 0.00)),
            "ewayBillNo": self.eway_bill_no,
            "ewayBillDate": self.eway_bill_date,
            "validUpto": self.eway_bill_valid_till,
        })

        return report_data

    def ewaybill_qr_data(self):
        """
        @usage : Generates and returns a formatted string containing e-way bill data for QR code generation.
        :param: None
        :return: str
        """
        ewaybill_qr_data = f"{self.eway_bill_no}/{self.company_id.vat}/{self.eway_bill_date}"
        return ewaybill_qr_data

    def determine_inward_outward(self):
        """
        Determines whether the transaction is Inward or Outward based on document type.
        :return: supply type
        """
        supply_type = self.is_purchase_document(include_receipts=True) and "I" or "O"
        return supply_type

    def _get_l10n_in_rcs_ewaybill_line_details(self, line, line_tax_details, sign):
        """
        @usage : Retrieves the e-way bill line details including product details and applicable taxes for each line.
        :param line: account.move.line object representing an invoice line
        :param line_tax_details: dict representing tax details for the line
        :param sign: int representing whether the invoice is inbound or outbound (positive or negative sign)
        :return: dict
        """
        extract_digits = self._l10n_in_edi_extract_digits
        tax_details_by_code = self._get_l10n_in_tax_details_by_line_code(line_tax_details.get("tax_details", {}))
        line_details = {
            "productName": line.product_id.name,
            "hsnCode": int(line.product_id.l10n_in_hsn_code),
            "productDesc": line.name,
            "quantity": line.quantity,
            "qtyUnit": line.product_id.uom_id.l10n_in_code and line.product_id.uom_id.l10n_in_code.split("-")[
                0] or "OTH",
            "taxableAmount": self._l10n_in_round_value(line.balance * sign),
        }
        if tax_details_by_code.get("igst_rate") or (
                line.move_id.l10n_in_state_id.l10n_in_tin != line.company_id.state_id.l10n_in_tin):
            line_details.update({"igstRate": self._l10n_in_round_value(tax_details_by_code.get("igst_rate", 0.00))})
        else:
            line_details.update({
                "cgstRate": self._l10n_in_round_value(tax_details_by_code.get("cgst_rate", 0.00)),
                "sgstRate": self._l10n_in_round_value(tax_details_by_code.get("sgst_rate", 0.00)),
            })
        if tax_details_by_code.get("cess_rate"):
            line_details.update({"cessRate": self._l10n_in_round_value(tax_details_by_code.get("cess_rate"))})
        return line_details

    def _l10n_in_edi_extract_digits(self, string):
        """
        @usage : Extracts and returns only the numeric digits from a given string.
        :param string: str containing characters to be extracted
        :return: str containing only digits
        """
        if not string:
            return string
        matches = re.findall(r"\d+", string)
        result = "".join(matches)
        return result

    @api.model
    def _get_l10n_in_tax_details_by_line_code(self, tax_details):
        """
        @usage : Maps tax details by line code and returns the tax details including rates and amounts.
        :param tax_details: dict representing tax details for the entire invoice
        :return: dict containing tax details organized by line code
        """
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

    @api.model
    def _l10n_in_round_value(self, amount, precision_digits=2):
        """
        @usage: Rounds the given amount to the specified number of decimal places.
                If rounding results in -0.0, it returns 0.0.
        :param amount: float - The amount to be rounded.
        :param precision_digits: int - Number of decimal places to round to (default is 2).
        :return: float - The rounded amount.
        """
        value = round(amount, precision_digits)
        # avoid -0.0
        return value if value else 0.0

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

    def cancel_ewaybill(self):
        """
        @usage: Generated Ewaybill Cancellation Form
        :return: Cancel EwayBill Form view
        """
        ctx = dict(self.env.context)
        ctx['ewaybill_active_id'] = self.id
        return {
            'name': 'Add Reason',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'alankit.ewaybill.cancel',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': ctx,
        }

    def open_alankit_invoice_ewaybill_logs(self):
        """
        @usage: Opens the Alankit eWay Bill logs for the current record and company.
        @return: Action to open the logs in the UI.
        """
        log_ids = self.env['common.process.log'].search([('res_id', '=', self.id), ('res_model', '=', 'account.move'),
                                                         ('resource_log', '=', 'alankit_eway_bill')])
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
