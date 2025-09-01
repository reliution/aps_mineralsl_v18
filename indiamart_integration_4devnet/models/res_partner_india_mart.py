from odoo import models, fields

class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_indiamart_customer = fields.Boolean(string="IndiaMart Customer")
    is_indiamart_lead = fields.Boolean(string="Indiamart Lead", default=False)
