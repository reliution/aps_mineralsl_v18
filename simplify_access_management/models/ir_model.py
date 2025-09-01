# -*- coding: utf-8 -*-

from odoo import api, fields, models, tools, _


class ir_model(models.Model):
    _inherit = "ir.model"

    abstract = fields.Boolean("Abstract", readonly=True)

    # def name_get(self):
    #     res = super().name_get()
    #     if self._context.get('is_access_rights'):
    #         res = []
    #         for model in self:
    #             res.append((model.id, "{} ({})".format(model.name, model.model)))
    #     return res
    @api.depends("name")
    @api.depends_context("is_access_rights")
    def _compute_display_name(self):
        if not self.env.context.get("is_access_rights"):
            return super()._compute_display_name()
        for model in self:
            new_name = "{} ({})".format(model.name, model.model)
            model.display_name = new_name


class IrModelField(models.Model):
    _inherit = "ir.model.fields"

    @api.depends("model_id")
    @api.depends_context("is_access_rights")
    def _compute_display_name(self):
        if not self.env.context.get("is_access_rights"):
            return super()._compute_display_name()
        for field in self:
            new_name = "{} => {} ({})".format(
                field.field_description, field.name, field.model_id.model
            )
            field.display_name = new_name


class ir_ui_view(models.Model):
    _inherit = "ir.ui.view"

    @api.depends("model_id")
    @api.depends_context("is_access_rights")
    def _compute_display_name(self):
        if not self.env.context.get("is_access_rights"):
            return super()._compute_display_name()
        for view in self:
            new_name = "{} ({})".format(view.name, view.model)
            view.display_name = new_name

    # def name_get(self):
    #     res = super().name_get()
    #     if self._context.get('is_access_rights'):
    #         res = []
    #         for view in self:
    #             res.append((view.id, "{} ({})".format(view.name, view.model)))
    #     return res


class ir_module_module(models.Model):
    _inherit = "ir.module.module"

    def _button_immediate_function(self, function):
        res = super(ir_module_module, self)._button_immediate_function(function)
        if function.__name__ in ["button_install", "button_upgrade"]:
            for record in self.env["ir.model"].search([]):
                try:
                    record.abstract = self.env[record.model]._abstract
                except:
                    return res
        return res
