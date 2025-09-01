# -*- coding: utf-8 -*-
""" Create/Manage the Log Lines for process """

import logging
from odoo import fields, models

_LOGGER = logging.getLogger(">>> Common Process Logs <<<")


class CommonProcessLogLines(models.Model):
    """
        Create/Manage the Log Lines for process
    """
    _name = "common.process.log.lines"
    _description = "Common Process Log Lines"

    name = fields.Char(string="Name")
    process_log_id = fields.Many2one(comodel_name='common.process.log', string='Process Log', ondelete='cascade',
                                     readonly=True)
    res_model = fields.Char('Resource Model', readonly=True,
                            help="The database object this attachment will be attached to.")
    res_field = fields.Char('Resource Field', readonly=True)
    res_id = fields.Many2oneReference('Resource ID', model_field='res_model',
                                      readonly=True, help="The record id this is attached to.")
    resource_log = fields.Char('Resource Log', readonly=True, help="Represent the Source of the Log.")
    company_id = fields.Many2one('res.company', string='Company', change_default=True,
                                 default=lambda self: self.env.company)
    message = fields.Text(string="Message")
    response = fields.Text(string="API Response", copy=False)

    state = fields.Selection(
        [('success', 'Success'),('error', 'Error')],
        string='Status',
        default='success')

    def prepare_common_process_log_line_values(self, process_log_book, **kwargs):
        """
            Create/Manage the Log Lines for process
        """
        values = {
            'process_log_id': process_log_book.id,
            'default_code': kwargs.get('default_code') if kwargs.get('default_code') else '',
        }
        model_fields = self._fields
        for field_name in kwargs:
            if hasattr(self, field_name):
                if model_fields[field_name].type == 'many2one' and kwargs.get(field_name):
                    values.update({field_name: kwargs[field_name].id})
                else:
                    values.update({field_name: kwargs.get(field_name, False)})
        _LOGGER.info(f"Common Process Log Lines Values: [{values}]")
        return values
