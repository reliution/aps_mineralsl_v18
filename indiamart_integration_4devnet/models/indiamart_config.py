from odoo import models, fields,api,_
from datetime import datetime ,timedelta
from odoo.exceptions import ValidationError

class IndiamartConfigSettings(models.Model):
    _name = 'indiamart.config.settings'
    _description = 'Indiamart Configuration'
    _rec_name = 'display_name'

    name = fields.Char(string="Configuration Name", required=True)
    glusr_crm_key = fields.Char(string='Glusr Crm Key')
    start_time = fields.Datetime(string='Start Date', default=lambda self: datetime.now() - timedelta(days=1))
    end_time = fields.Datetime(string='End Date')
    last_sync_time = fields.Datetime(string='Last Sync Time', readonly=True , store=True)
    last_api_hit_time = fields.Datetime(string="Last API Hit Time", readonly=True)
    hit_count = fields.Integer(string="API Hit Count", default=0)
    block_until = fields.Datetime(string="Block Until", readonly=True)
    hit_time = fields.Datetime(string="API Hit Time", default=fields.Datetime.now)
    api_key_generated_time = fields.Datetime(string="API Key Generated Time" ,store=True)
    company_id = fields.Many2one('res.company', string="Company")
    create_customer = fields.Boolean(string="Create Customer",default=False)

    environment = fields.Selection([
        ('test', 'Testing'),
        ('production', 'Production')
    ], string="Environment", default="test", required=True)
    display_name = fields.Char(compute="_compute_display_name", store=False)  # Computed field for name

    def action_run_scheduler(self):
        """Manually trigger Indiamart lead retrieval."""
        self.env["indiamart.log"]._cron_retrieve_indiamart_leads()

    @api.depends('name')
    def _compute_display_name(self):
        """Compute custom display name based on the 'name' field."""
        for record in self:
            record.display_name = record.name or "Indiamart Configuration"

    @api.constrains('start_time', 'end_time')
    def validate_start_end_time(self):
        for record in self:
            if record.start_time and record.end_time:
                time_difference = record.end_time - record.start_time
                if time_difference > timedelta(days=7):
                    raise ValidationError(_("The maximum allowed difference between Start Time and End Time is 7 days."))

            if record.start_time:
                if record.start_time < (fields.Datetime.now() - timedelta(days=365)):
                    raise ValidationError(_("Data can only be retrieved for the last 365 days."))

    def toggle_environment(self):
        """Toggle between Testing and Production"""
        for record in self:
            record.environment = 'production' if record.environment == 'test' else 'test'

    @api.model
    def create(self, vals):
        if 'glusr_crm_key' in vals:
            existing_key = self.search([('glusr_crm_key', '=', vals['glusr_crm_key'])])
            if existing_key:
                raise ValidationError(f"CRM Key '{vals['glusr_crm_key']}' already exists! Please use a different key.")
        res =super().create(vals)
        retrieve_cron_obj = self.env.ref('indiamart_integration_4devnet.ir_cron_indiamart_leads')
        if retrieve_cron_obj:
        	retrieve_cron_obj.active =True
        return res




class CRMLead(models.Model):
    _inherit = "crm.lead"

    is_indiamart_lead = fields.Boolean(string="Is IndiaMart Lead", default=False)
