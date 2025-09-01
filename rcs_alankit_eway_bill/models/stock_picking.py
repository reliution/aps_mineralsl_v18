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


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    rcs_total = fields.Monetary(string="Sub Total", tracking=True, compute='_compute_amount')
    currency_id = fields.Many2one('res.currency', string="Currency",
                                  related='company_id.currency_id',
                                  default=lambda
                                      self: self.env.user.company_id.currency_id.id)
    warehouse_id = fields.Many2one('stock.warehouse', related='picking_type_id.warehouse_id')
    document_type = fields.Selection(
        [('INV', 'Tax Invoice'), ('BIL', 'Bill of Supply'), ('CHL', 'Delivery Challan'), ('BOE', 'Bill of Entry'),
         ('CNT', 'Credit Note'), ('OTH', 'Others')], default='CHL', tracking=True)
    supply_type = fields.Selection(
        [
            ('I', 'Inward'),
            ('O', 'outward')
        ],
        string='Supply Type',
        default='O',
        help="Supply whether it is outward/inward.", tracking=True)
    transaction_type = fields.Selection(
        [('1', 'Regular'), ('2', 'Bill To-Ship To'), ('3', 'Bill From-Dispatch From'), ('4', 'Combination of 2 and 3')],
        default="1", string='Transaction Type', tracking=True)
    
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
    transportation_doc_name = fields.Char(string="TransDocNo", help="""Transport document number. If it is more than 15 chars, last 15 chars may be entered""", tracking=True, copy=False)
    transportation_doc_date = fields.Date(string="TransDocDt", default=fields.Date.today, tracking=True)
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
        string='Sub Supply Type', default="1", tracking=True,
        help="Sub types of Supply like supply, export, Job Work etc."
    )
    sub_supply_desc = fields.Char(string="Sub Supply Description")
    transporter_id = fields.Many2one('res.partner', string='Transport', tracking=True)
    transportation_gstin = fields.Char(related='transporter_id.vat', string='Transin/GSTIN', tracking=True,
                                     readonly=False)
    transporter_contact_no = fields.Char(string='Contact No', tracking=True, readonly=False)
    eway_bill_generated = fields.Boolean(copy=False, tracking=True)
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
                [('res_id', '=', rec.id), ('res_model', '=', 'stock.picking'),
                 ('resource_log', '=', 'alankit_eway_bill')])
            rec.ewaybill_log_count = len(log_ids)

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

    def static_ewaybill_json_data(self):
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

    @api.onchange('supply_type')
    def _onchange_supply_type(self):
        for order in self:
            if order.supply_type == 'I':
                order.sub_supply_type = '6'
            elif order.supply_type == 'O':
                order.sub_supply_type = '4'

    @api.depends('move_ids_without_package','move_ids_without_package.sub_total')
    def _compute_amount(self):
        for order in self:
            comm_total = 0.0
            for line in order.move_ids_without_package:
                    comm_total += line.sub_total
            order.update({'rcs_total': comm_total})

    @api.onchange('transporter_id')
    def onchange_transporter_details(self):
        if self.transporter_id:
            self.transportation_gstin = self.transporter_id.vat
            self.transporter_contact_no = self.transporter_id.mobile

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
            _logger.info("=============>Generated Eway bill URL %s", encrypted_sek)
            app_key = base64.b64decode(instance.app_key)
            key = self.decrypt_ewaybill_data_by_symmetric_key(encrypted_sek, app_key)
            log_name = "%s_Alankit_E-way_Bill" % (self.name.replace("/", "_"))
            log_obj = self.env['common.process.log'].sudo().create({'name': log_name,
                                                                    'res_model': 'stock.picking',
                                                                    'res_id': self.id,
                                                                    'resource_log': 'alankit_eway_bill'})
            json_data = self.generate_ewaybill_json(log_obj)
            # json_data = self.static_ewaybill_json_data()
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
                                'res_model': 'stock.picking',
                                'res_id': self.id,
                                'resource_log': 'alankit_eway_bill',
                                'message': f"{alert}",
                                'state': "error"
                            })
                        # pdf = self.env.ref('rcs_alankit_eway_bill.action_stock_report_ewaybill')._render_qweb_pdf(
                        #     self.ids)
                        pdf = self.env['ir.actions.report']._render_qweb_pdf('rcs_alankit_eway_bill.action_stock_report_ewaybill', res_ids=self.ids)
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
                        response_errors = [code for code in response_errors_str.split(',') if code]

                        log_obj.sudo().update({
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
                                    'res_model': 'stock.picking',
                                    'res_id': self.id,
                                    'resource_log': 'alankit_eway_bill',
                                    'message': f"{error_desc}",
                                    'state': "error"
                                })
            except Exception as error:
                raise UserError(_(f"Failed! Exception: {error}"))

    def ewaybill_errorlist(self, log_obj):
        """
        @usage: GET Alankit Ewaybill ErrorList
        :return:str
            Decrypted error list from Alankit Ewaybill service
        """
        instance = self.env['alankit.api.configuration'].get_instance()
        encrypted_sek = instance.ewaybill_Sek_key
        app_key = base64.b64decode(instance.app_key)
        key = self.decrypt_ewaybill_data_by_symmetric_key(encrypted_sek, app_key)
        url = instance.prepare_generate_ewaybill_errorlist()
        headers = {
            'Content-Type': 'application/json',
            'Ocp-Apim-Subscription-Key': instance.subscription_key,
            'gstin': instance.gstin,
            'authToken': instance.ewaybill_access_token
        }
        response = requests.request("GET", url, headers=headers, data={})
        json_response = response.json()
        if response.status_code == 200:
            if json_response.get('status') == '1':
                encrypted_data = json_response.get("data")
                encrypted_rek = json_response.get("rek")
                # decrypt data
                rek_key = self.decrypt_ewaybill_data_by_symmetric_key(encrypted_rek, key)
                data = self.decrypt_ewaybill_data_by_symmetric_key(encrypted_data, rek_key)
                decrypt_data = data.decode()
                _logger.info("=============>Eway bill Errorlist %s", decrypt_data)
                return decrypt_data
            else:
                _logger.info("=============>Failed to fetch Eway bill Errorlist %s")
                error = json_response.get('error')
                msg = base64.b64decode(error).decode()
                if error:
                    log_obj.line_ids.create({
                        'process_log_id': log_obj.id,
                        'name': "Error",
                        'res_model': 'stock.picking',
                        'res_id': self.id,
                        'resource_log': 'alankit_eway_bill',
                        'response': json.dumps(msg, indent=2),
                        'message': msg,
                        'state': "error"
                    })
                return False

    # Generate E-way Bill Json
    # "required": ["supplyType", "subSupplyType", "docType", "docNo", "docDate", "fromGstin", "fromPincode",
    #              "fromStateCode", "toGstin", "toPincode", "toStateCode", "transDistance", "itemList", "actToStateCode",
    #              "actFromStateCode", "totInvValue", "transactionType"]
    def generate_ewaybill_json(self, log):
        """
        :param log: Log object associated with the current transaction or process
        :return: Payload JSON formatted data for e-way bill generation
        """

        transporterObj = self.transporter_id
        line_data = self.generate_internal_transfer_line()
        itemdata = line_data[0]
        orderJsonDate = self.scheduled_date.strftime('%d/%m/%Y')
        # consignor = self.company_id.partner_id
        # consignee = self.partner_id
        if self.supply_type == 'O':
            consignor = self.warehouse_id.partner_id
            consignee = self.partner_id
        else:
            consignor = self.partner_id
            consignee = self.location_dest_id.warehouse_id.partner_id
        extract_digits = self._l10n_in_edi_extract_digits
        # consignor = self.warehouse_id.store_id  # storeObj
        # consignee = self.location_dest_id.warehouse_id.store_id  # destStoreObj
        # document_type = 'CHL'  # Delivery challan
        if len(self.name) > 16:
            document_name = self.name.replace('/', '').replace(' ', '')
            if len(document_name) > 16:
                document_name = self.document_name.lstrip('BILL/').lstrip('RBILL/').replace(' ', '')
        else:
            document_name = self.name.replace(' ', '')
        json_payload = {
            # "supplyType": self.is_purchase_document(include_receipts=True) and "I" or "O",
            "supplyType": self.supply_type,
            "subSupplyType": self.sub_supply_type,
            "subSupplyDesc": self.sub_supply_desc,
            "docType": self.document_type,
            "docNo": document_name,
            "docDate": orderJsonDate,
            "fromGstin": consignor.vat or "URP",
            # "fromGstin": "07AGAPA5363L002",
            "fromTrdName": consignor.name,
            "fromAddr1": consignor.street,
            "fromAddr2": consignor.street2 or "",
            "fromPlace": consignor.city,
            "fromPincode": consignor.country_id.code == "IN" and int(extract_digits(consignor.zip)) or "",
            "actFromStateCode": int(consignor.state_id.l10n_in_tin) if consignor.state_id.l10n_in_tin else 99,
            "fromStateCode": int(consignor.state_id.l10n_in_tin) if consignor.state_id.l10n_in_tin else 99,
            "toGstin": consignee.vat or "URP",
            # "toGstin": '07AGAPA5363L002',
            "toTrdName": consignee.name,
            "toAddr1": consignee.street,
            "toAddr2": consignee.street2 or "",
            "toPlace": consignee.city,
            "toPincode": int(consignee.zip),
            "actToStateCode": int(consignee.state_id.l10n_in_tin) if consignee.state_id.l10n_in_tin else 99,
            "toStateCode": int(consignee.state_id.l10n_in_tin) if consignee.state_id.l10n_in_tin else 99,
            "transDistance": self.transportation_distance,
            "transactionType": self.transaction_type,
            "dispatchFromTradeName": consignor.commercial_partner_id.name,
            "shipToTradeName": consignee.commercial_partner_id.name,
            "totalValue": round(self.rcs_total, 2),
            "cgstValue": 0.00,
            "sgstValue": 0.00,
            "igstValue": 0.00,
            "cessValue": 0.00,
            "cessNonAdvolValue": 0,
            "totInvValue": round(self.rcs_total, 2),
            "otherValue": 0.00,
            "itemList": itemdata,
        }
        if self.transporter_in_mode == "0":
            json_payload.update({
                "transporterId": transporterObj.vat or "",
                "transporterName": transporterObj.name or "",
            })
        if self.transporter_in_mode in ("2", "3", "4"):
            json_payload.update({
                "transMode": self.transporter_in_mode,
                "transDocNo": self.transportation_doc_name or "",
                "transDocDate": self.transportation_doc_date and self.transportation_doc_date.strftime(
                    "%d/%m/%Y") or "",
            })
        if self.transporter_in_mode == "1":
            json_payload.update({
                "transMode": self.transporter_in_mode,
                "vehicleNo": self.vehicle_no or "",
                "vehicleType": self.vehicle_type or "",
            })

        # for the test purpose
        if self.supply_type == 'I':
            json_payload.update({'toGstin': '07AGAPA5363L002'})
        else:
            json_payload.update({'fromGstin': '07AGAPA5363L002'})

        required_fields = ["supplyType", "subSupplyType", "docType", "docNo", "docDate", "fromGstin", "fromPincode",
                           "fromStateCode", "toGstin", "toPincode", "toStateCode", "transDistance", "actToStateCode",
                           "actFromStateCode", "totInvValue", "transactionType"]
        missing_fields = [field for field in required_fields if not json_payload.get(field)]
        if missing_fields and log:
            log_message = f"Missing required fields: {', '.join(missing_fields)}"
            log.line_ids.create({
                'process_log_id': log.id,
                'name': 'Values',
                'res_model': 'stock.picking',
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
        supply_type = self.supply_type
        if self.supply_type == 'O':
            consignor = self.warehouse_id.partner_id
            consignee = self.partner_id
        else:
            consignor = self.partner_id
            consignee = self.location_dest_id.warehouse_id.partner_id
        report_data = self.generate_ewaybill_json(log=None)
        report_data.update({
            "Type": "Inward" if supply_type == 'I' else 'Outward',
            "subSupplyType": dict(self._fields['sub_supply_type'].selection).get(self.sub_supply_type),
            "fromStateCode": consignor.state_id.name if consignor.state_id.name else 'Other Country',
            "toStateCode": consignee.state_id.name if consignee.state_id.name else 'Other Country',
            "transMode": dict(self._fields['transporter_in_mode'].selection).get(self.transporter_in_mode),
            'transactionType':dict(self._fields['transaction_type'].selection).get(self.transaction_type),
            "transporterId": self.transportation_gstin,
            "transporterName": self.transporter_id.name,
            "transDocNo": self.transportation_doc_name,
            "transDocDate": self.transportation_doc_date.strftime('%d/%m/%Y'),
            "vehicleNo": self.vehicle_no,
            "vehicleType": self.vehicle_type,
            "total_tax_amt": round(self.rcs_total, 2),
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

    def _l10n_in_edi_extract_digits(self, string):
        if not string:
            return string
        matches = re.findall(r"\d+", string)
        result = "".join(matches)
        return result

    def generate_internal_transfer_line(self):
        itemList = []
        itemNo = 1
        for line in self.move_ids_without_package:
            product_obj = line.product_id
            product_name = product_obj.name
            uqc = line.product_id.uom_id.l10n_in_code and line.product_id.uom_id.l10n_in_code.split("-")[0] or 'OTH'
            hsnCode = product_obj.l10n_in_hsn_code or 0
            hsnCode = int(hsnCode)
            itemDict = {
                'productName': product_name,
                'productDesc': product_name,
                'hsnCode': hsnCode,
                'quantity': line.product_uom_qty,
                'qtyUnit': uqc,
                'taxable_amount': round(line.product_id.standard_price, 2),
                'sgstRate': 0.0,
                'cgstRate': 0.0,
                'igstRate': 0.0,
                'cessRate': 0.0
            }
            itemList.append(itemDict)
            itemNo = itemNo + 1
        return [itemList]

    def cancel_ewaybill(self):
        """
        @usage: Generated Ewaybill Cancellation Form
        :return: Cancel EwayBill Form view
        """
        ctx = dict(self.env.context)
        ctx['stock_ewaybill_active_id'] = self.id
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

    def open_alankit_ewaybill_logs(self):
        """
        @usage: Opens the Alankit eWay Bill logs for the current record and company.
        @return: Action to open the logs in the UI.
        """
        log_ids = self.env['common.process.log'].search([('res_id', '=', self.id), ('res_model', '=', 'stock.picking'),
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
