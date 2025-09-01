# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class StockMove(models.Model):
    _inherit = 'stock.move'

    sub_total = fields.Float(string="Total", compute='_compute_total')
    product_price = fields.Float(string="Unit Price")
    total = fields.Float(string="Sub Total")

    @api.onchange('product_id', 'picking_type_id')
    def _onchange_product_id(self):
        super(StockMove, self)._onchange_product_id()
        if self.product_id:
            self.product_price = self.product_id.standard_price

    def _compute_total(self):
        for rec in self:
            rec.sub_total = 0.0
            if rec.product_id:
                rec.sub_total = rec.product_id.standard_price * rec.product_uom_qty
