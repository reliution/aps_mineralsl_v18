# -*- coding: utf-8 -*-
""" Create/Manage the Logs for process """
import logging
from odoo import models, api, fields, _

_LOGGER = logging.getLogger(">>> Common Process Logs <<<")

OPERATION_TYPE = [('import', 'Import'),
                  ('export', 'Export'), ]


class CommonProcessLogs(models.Model):
    """
        Create/Manage the Logs for process
    """
    _name = "common.process.log"
    _description = "Common Process Logs"
    _order = 'id desc'

    name = fields.Char(string='Name', required=True, copy=False, readonly=True, index=True,
                       default=lambda self: _('New'))
    line_ids = fields.One2many(comodel_name='common.process.log.lines', inverse_name='process_log_id',
                               string='Log Lines')
    message = fields.Text(string="Message")
    res_model = fields.Char('Resource Model', readonly=True,
                            help="The database object this attachment will be attached to.")
    res_field = fields.Char('Resource Field', readonly=True)
    res_id = fields.Many2oneReference('Resource ID', model_field='res_model',
                                      readonly=True, help="The record id this is attached to.")
    resource_log = fields.Char('Resource Log', readonly=True, help="Represent the Source of the Log.")
    company_id = fields.Many2one('res.company', string='Company', change_default=True,
                                 default=lambda self: self.env.company)
    response = fields.Text(string="API Response", copy=False)


    def prepare_common_process_log_values(self, operation_type='import', message="", **kwargs):
        """
            Create/Manage the Logs for process
        """
        values = {
            'operation_type': operation_type,
            'name': self.env['ir.sequence'].sudo().next_by_code('common.process.log') or _('New'),
            'message': message
        }
        model_fields = self._fields
        for field_name in kwargs:
            if hasattr(self, field_name):
                if model_fields[field_name].type == 'many2one' and kwargs.get(field_name):
                    values.update({field_name: kwargs[field_name].id})
                else:
                    values.update({field_name: kwargs.get(field_name, False) or False})
        _LOGGER.info(f"Common Process Log Values: [{values}]")
        return values

    @api.model
    def _get_log_count(self, res_id, res_model, company_id, resource_log):
        """
        Calculate the count of related logs for a given record and return it.

        :param res_id: ID of the record for which logs need to be counted.
        :param res_model: Model name of the related resource (e.g., 'product.template').
        :param company_id: ID of the company to filter logs (optional).
        :return: Integer representing the count of logs.
        """
        log_ids = self.env['common.process.log'].search([
            ('res_id', '=', res_id),
            ('res_model', '=', res_model),
            ('company_id', '=', company_id),
            ('resource_log', '=', resource_log),
        ])
        return log_ids

    def _open_logs_action(self, log_ids):
        """
        Generate an action to open logs based on the provided log IDs and resource model.

        :param log_ids: Record IDs of logs to be opened.
        :return: Action dictionary to open logs.
        """
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
        return False
