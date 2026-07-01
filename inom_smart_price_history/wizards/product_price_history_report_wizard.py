# -*- coding: utf-8 -*-
import base64
import io

from dateutil.relativedelta import relativedelta

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ProductPriceHistoryReportWizard(models.TransientModel):
    _name = "product.price.history.report.wizard"
    _description = "Product Price History Report Wizard"

    supplier_id = fields.Many2one(
        comodel_name="res.partner",
        string="Supplier",
        domain="[('supplier_rank', '>', 0)]",
        help="Optional. Leave empty to include all suppliers.",
    )
    product_id = fields.Many2one(
        comodel_name="product.product",
        string="Product",
        help="Optional. Leave empty to include all products.",
    )
    date_from = fields.Date(string="Start Date")
    date_to = fields.Date(string="End Date")

    def _check_dates(self):
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise UserError(_("Start Date cannot be after End Date."))

    def _get_history_lines(self):
        """F-13/F-14: List the confirmed Purchase Order lines for the selected
        product/supplier within the order-date range, with their pricing
        (Qty, Unit Price, Subtotal, Tax, Total), sorted by order date.
        """
        self.ensure_one()
        self._check_dates()

        domain = [
            ("order_id.state", "in", ("purchase", "done")),
            ("product_id", "!=", False),
        ]
        if self.supplier_id:
            domain.append(
                ("order_id.partner_id.commercial_partner_id", "=",
                 self.supplier_id.commercial_partner_id.id)
            )
        if self.product_id:
            domain.append(("product_id", "=", self.product_id.id))
        if self.date_from:
            domain.append(("order_id.date_order", ">=", self.date_from))
        if self.date_to:
            domain.append(
                ("order_id.date_order", "<",
                 self.date_to + relativedelta(days=1))
            )

        po_lines = self.env["purchase.order.line"].search(domain)
        po_lines = po_lines.sorted(
            key=lambda l: l.order_id.date_order or fields.Datetime.now()
        )

        lines = []
        for line in po_lines:
            order = line.order_id
            lines.append({
                "document": order.name,
                "date": order.date_order,
                "vendor": order.partner_id.display_name,
                "qty": line.product_qty,
                "price_unit": line.price_unit,
                "price_subtotal": line.price_subtotal,
                "price_tax": line.price_tax,
                "price_total": line.price_total,
                "currency": order.currency_id or self.env.company.currency_id,
            })
        return lines

    def action_print_pdf(self):
        """F-14: Generate the PDF report for the selected filters."""
        self.ensure_one()
        self._check_dates()
        return self.env.ref(
            "inom_smart_price_history.price_history_report"
        ).report_action(self, data={"wizard_id": self.id})

    def action_download_xls(self):
        """F-15: Generate an Excel (.xlsx) file with the same columns as the
        PDF report and return it as an immediate download.
        """
        self.ensure_one()
        try:
            import xlsxwriter
        except ImportError:
            raise UserError(_(
                "The 'xlsxwriter' Python library is required to export "
                "Excel reports. Please install it on the server "
                "(pip install xlsxwriter)."
            ))

        lines = self._get_history_lines()

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})
        sheet = workbook.add_worksheet("Price History")

        header_format = workbook.add_format({
            "bold": True,
            "bg_color": "#D9D9D9",
            "border": 1,
        })
        cell_format = workbook.add_format({"border": 1})
        date_format = workbook.add_format({"border": 1, "num_format": "yyyy-mm-dd hh:mm:ss"})
        money_format = workbook.add_format({"border": 1, "num_format": "0.00"})

        headers = ["Purchase Order", "Order Date", "Vendor Name", "Qty",
                   "Unit Price", "Subtotal", "Tax", "Total"]
        for col, header in enumerate(headers):
            sheet.write(0, col, header, header_format)
            sheet.set_column(col, col, 20)

        for row, line in enumerate(lines, start=1):
            sheet.write(row, 0, line["document"] or "", cell_format)
            if line["date"]:
                sheet.write_datetime(row, 1, line["date"], date_format)
            else:
                sheet.write(row, 1, "", cell_format)
            sheet.write(row, 2, line["vendor"], cell_format)
            sheet.write(row, 3, line["qty"], cell_format)
            sheet.write(row, 4, line["price_unit"], money_format)
            sheet.write(row, 5, line["price_subtotal"], money_format)
            sheet.write(row, 6, line["price_tax"], money_format)
            sheet.write(row, 7, line["price_total"], money_format)

        workbook.close()
        output.seek(0)
        file_data = base64.b64encode(output.read())
        output.close()

        attachment = self.env["ir.attachment"].create({
            "name": "Product_Price_History.xlsx",
            "type": "binary",
            "datas": file_data,
            "res_model": self._name,
            "res_id": self.id,
            "mimetype": "application/vnd.openxmlformats-officedocument"
                        ".spreadsheetml.sheet",
        })

        return {
            "type": "ir.actions.act_url",
            "url": "/web/content/%s?download=true" % attachment.id,
            "target": "self",
        }