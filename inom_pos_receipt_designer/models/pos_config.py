from odoo import fields, models


class PosConfig(models.Model):
    _inherit = "pos.config"

    # pos.config loads all of its fields in the POS frontend in Odoo 20
    # (_load_pos_data_fields returns []), and the full record is passed as
    # `config` to the receipt templates, so no loader override is needed.
    receipt_design = fields.Selection(
        [
            ("classic", "Classic"),
            ("modern", "Modern"),
            ("compact", "Compact"),
            ("detailed", "Detailed"),
            ("minimal", "Minimal"),
            ("dark", "Dark"),
            ("card", "Card"),
            ("bold", "Bold"),
            ("elegant", "Elegant"),
            ("gradient", "Gradient"),
        ],
        string="Receipt Design",
        default="classic",
        required=True,
    )
