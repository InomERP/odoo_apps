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

    @api.model
    def _create_sample_employee_table(self):
        """Create and seed the `employee` table used by the example queries,
        so they work in any order. Safe to run on every install/upgrade."""
        self.env.cr.execute("""
            CREATE TABLE IF NOT EXISTS employee (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100),
                department VARCHAR(50),
                salary INTEGER
            )
        """)
        self.env.cr.execute("SELECT 1 FROM employee LIMIT 1")
        if not self.env.cr.fetchone():
            self.env.cr.execute("""
                INSERT INTO employee (name, department, salary)
                VALUES ('Amit', 'IT', 50000), ('Rahul', 'HR', 40000), ('Sneha', 'IT', 60000)
            """)
        # the example record is noupdate, so fix databases installed before this change
        sample = self.env.ref('inom_pg_query_toolkit.create_employee_table', raise_if_not_found=False)
        if sample and sample.name and 'IF NOT EXISTS' not in sample.name:
            sample.name = sample.name.replace('CREATE TABLE employee', 'CREATE TABLE IF NOT EXISTS employee')

    def action_print_pdf(self):
         if self:
             self = self.sudo()
             first = self[0]
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

                if rowcount < 0:  # DDL statements (CREATE, ALTER, ...) have no row count
                    vals["rowcount"] = _("Query executed successfully")
                else:
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

                        row_color = "#f9aafb" if i % 2 == 0 else "#ffffff"

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
