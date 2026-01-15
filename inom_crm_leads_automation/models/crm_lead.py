from odoo import models, api

class CrmLead(models.Model):
    _inherit = "crm.lead"

    @api.model
    def create(self, vals):
        record = super().create(vals)
        template = self.env.ref('inom_crm_leads_automation.email_template_thank_you')
        if template:
            template.with_user(self.env.user).send_mail(record.id, force_send=True)
        return record
