from odoo import api, models


class CrmLead(models.Model):
    _inherit = "crm.lead"

    @api.model
    def create(self, vals):
        record = super().create(vals)
        template = self.env.ref(
            "inom_crm_leads_automation.email_template_thank_you",
            raise_if_not_found=False,
        )
        if template and record.email_from:
            template.with_user(self.env.user).send_mail(
                record.id,
                force_send=True,
            )
        return record
