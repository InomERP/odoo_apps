# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class UnivAuditMixin(models.AbstractModel):
    """Mixin that records create/write/unlink operations on configured fields
    into the immutable ``univ.audit.log`` model.

    A model using this mixin should declare the fields it wants tracked in the
    ``_audit_log_fields`` class attribute. If left empty, nothing is logged on
    write (create and unlink are still logged as a single summary line).
    """

    _name = "univ.audit.mixin"
    _description = "University Audit Mixin"

    # Override in concrete models with the list of field names to audit.
    _audit_log_fields = []

    def _audit_format_value(self, field_name, value):
        """Return a human-readable representation for a stored value."""
        if value is False or value is None:
            return ""
        field = self._fields.get(field_name)
        if field and field.type in ("many2one",):
            # ``value`` here is the recordset already resolved by the caller.
            return value.display_name if value else ""
        if field and field.type == "selection":
            selection = dict(field._description_selection(self.env))
            return selection.get(value, value)
        return str(value)

    def _audit_create_logs(self, line_vals_list):
        if line_vals_list:
            self.env["univ.audit.log"].sudo().create(line_vals_list)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        line_vals_list = []
        for record in records:
            line_vals_list.append(
                {
                    "res_model": record._name,
                    "res_id": record.id,
                    "res_name": record.display_name,
                    "operation": "create",
                    "field_name": False,
                    "field_label": False,
                    "old_value": "",
                    "new_value": _("Record created"),
                }
            )
        records._audit_create_logs(line_vals_list)
        return records

    def write(self, vals):
        tracked = [f for f in self._audit_log_fields if f in vals]
        old_data = {}
        if tracked:
            for record in self:
                old_data[record.id] = {f: record[f] for f in tracked}
        result = super().write(vals)
        if tracked:
            line_vals_list = []
            for record in self:
                for field_name in tracked:
                    old_value = old_data.get(record.id, {}).get(field_name)
                    new_value = record[field_name]
                    if old_value == new_value:
                        continue
                    field = record._fields[field_name]
                    line_vals_list.append(
                        {
                            "res_model": record._name,
                            "res_id": record.id,
                            "res_name": record.display_name,
                            "operation": "write",
                            "field_name": field_name,
                            "field_label": field.get_description(self.env).get(
                                "string", field_name
                            ),
                            "old_value": record._audit_format_value(
                                field_name, old_value
                            ),
                            "new_value": record._audit_format_value(
                                field_name, new_value
                            ),
                        }
                    )
            self._audit_create_logs(line_vals_list)
        return result

    def unlink(self):
        line_vals_list = []
        for record in self:
            line_vals_list.append(
                {
                    "res_model": record._name,
                    "res_id": record.id,
                    "res_name": record.display_name,
                    "operation": "unlink",
                    "field_name": False,
                    "field_label": False,
                    "old_value": record.display_name,
                    "new_value": "",
                }
            )
        # Create logs before the records disappear.
        self._audit_create_logs(line_vals_list)
        return super().unlink()
