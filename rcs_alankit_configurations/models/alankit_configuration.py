# -*- coding: utf-8 -*
import secrets
import logging
import base64
from odoo import fields, api, models, _


_logger = logging.getLogger(">>> Alankit <<<")


class AlankitAPIConfiguration(models.Model):
    _name = "alankit.api.configuration"
    _description = "Alankit API Configuration"

    name = fields.Char(string="Name")
    gstin = fields.Char(string="GST IN", required=True)
    subscription_key = fields.Char(string="Subscription Key", required=True)
    username = fields.Char(string="Username", required=True)
    password = fields.Char(string="Password", required=True)
    app_key = fields.Char(string="APP Key", readonly=True, copy=False)
    state = fields.Selection([('draft', 'Draft'), ('verify', 'Verified')], default="draft")

    @staticmethod
    def generate_uuid():
        """
        @Usage:Generate a UUID (base64 encoded) for app_key field.
       :return: str - Base64 encoded UUID string.
        """
        app_key = secrets.token_bytes(32)
        base64_key = base64.b64encode(app_key).decode('utf-8')
        return base64_key

    @api.model
    def create(self, values):
        """
        @Usage:Override create method to generate app_key on creation.
        :param values: dict - Dictionary of field values for the new record.
        :return: record - Created record with the generated app_key.
        """
        values['app_key'] = self.generate_uuid()
        return super(AlankitAPIConfiguration, self).create(values)

    def get_instance(self, domain=None, order='id desc', limit=1):
        """
        @Usage:Retrieve E-invoice instance based on domain and ordering.
        :param domain: list - List of domain conditions (default: empty list).
        :param order: str - Sorting order of results (default: 'id desc').
        :param limit: int - Maximum number of records to retrieve (default: 1).
        :return: recordset - Recordset of E-invoice instances.

        """
        domain = [] if domain is None else domain
        return self.search(domain, order=order, limit=limit)

    @staticmethod
    def base64_encode(data: str) -> str:
        """
        @Usage: Encode data to base64.
        :param data: str - String data to be encoded.
        :return: str - Base64 encoded string.
        """
        encoded_bytes = base64.b64encode(data.encode('utf-8'))
        encoded_str = encoded_bytes.decode('utf-8')
        return encoded_str
