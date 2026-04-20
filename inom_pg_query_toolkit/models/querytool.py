from odoo import api, fields, models,_
from odoo import exceptions

class Querytool(models.Model):
    _name = 'query.tool'
    _description = 'Query tool'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'
    active = fields.Boolean(default=True)
    rowcount = fields.Text(string='Rowcount')
    html = fields.Html(string='HTML')
    name = fields.Text(string="Write a quary")
    note = fields.Char(string="note")

    def action_print_pdf(self):
         if self:
             self = self.sudo()
             first = self[0]
             print(first)
             return {
                'name': _("Select orientation of the PDF's result"),
                'view_mode': 'form',
                'res_model': 'orientationpdf',
                'type': 'ir.actions.act_window',
                'target': 'new',
                'context': {
                    'default_name': first.name,
                    'default_query_id': first.id,

                },
            }

    def get_result_query(self, query):
        self = self.sudo()
        headers = []
        datas = []

        if query:
            try:
                self.env.cr.execute(query)
            except Exception as e:
                raise exceptions.UserError(e)

            try:
                if self.env.cr.description:
                    headers = [d[0] for d in self.env.cr.description]
                    datas = self.env.cr.fetchall()
            except Exception as e:
                raise exceptions.UserError(e)

        return headers, datas

    def execute(self):
        for record in self.sudo():
            vals = {"rowcount": False, "html": False}

            if record.name:
                record.message_post(body=str(record.name))
                headers, datas = self.get_result_query(record.name)

                rowcount = record.env.cr.rowcount

                vals["rowcount"] = _("{0} row{1} processed").format(
                    rowcount, 's' if rowcount != 1 else ''
                )

                if headers and datas:

                    # ===== HEADER STYLE =====
                    header_html = "<tr style='background-color:#1f6737; color:black;'>"
                    header_html += "<th style='padding:8px; border:1px solid #374151;'>#</th>"

                    header_html += "".join([
                        "<th style='padding:8px; border:1px solid #374151;'>{}</th>".format(h)
                        for h in headers
                    ])
                    header_html += "</tr>"

                    # ===== BODY STYLE =====
                    body_html = ""
                    i = 0

                    for data in datas:
                        i += 1

                        row_color = "#f9aafb" if i % 2 == 0 else "#ffvfff"

                        body_line = f"""
                            <tr style="background-color:{row_color};">
                                <td style="
                                    border:10px solid #d1d9db;
                                    padding:6px;
                                    font-weight:bold;
                                    color:#1e3a8a;
                                    background-color:#dbeafe;
                                ">
                                    {i}
                                </td>
                        """

                        for value in data:
                            display_value = ''
                            if value is not None:
                                display_value = str(value).replace("&", "&amp;") \
                                    .replace("<", "&lt;") \
                                    .replace(">", "&gt;")

                            body_line += f"""
                                <td style="border:1px solid #e5e7eb; padding:6px; color:#374151;">
                                    {display_value}
                                </td>
                            """

                        body_line += "</tr>"
                        body_html += body_line

                    # ===== FINAL TABLE =====
                    vals["html"] = f"""
                    <table style="
                        width:100%;
                        border-collapse:collapse;
                        font-family:Arial;
                        font-size:13px;
                        border:10px solid #111927;
                    ">
                        <thead>
                            {header_html}
                        </thead>
                        <tbody>
                            {body_html}
                        </tbody>
                    </table>
                    """

            record.update(vals)
