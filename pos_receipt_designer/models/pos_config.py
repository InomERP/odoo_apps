from odoo import models, fields


class PosConfig(models.Model):
    _inherit = "pos.config"

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
        default="classic",
        required=True,
    )

    def _load_pos_data(self, data):
        """Ensure receipt_design is loaded in POS config"""
        result = super()._load_pos_data(data)

        for config in result.get("pos.config", []):
            config["receipt_design"] = config.get("receipt_design", "classic")

        return result