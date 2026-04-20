from odoo import models, fields, _ ,api
from odoo.exceptions import UserError

class OrientationPdfWizard(models.TransientModel):
    _name = 'orientationpdf'

    @api.model
    def orientation_choices(self):
        return [('landscape', _('Landscape')), ('portrait', _('Portrait'))]

    orientation = fields.Selection(
        selection=orientation_choices,
        string="PDF orientation",
        default='landscape'
    )

    def get_default_caution_html(self):
        return _("""
        <div>
            <span style='color: red'>Be careful</span>, it will execute the query <span style='color: red; text-decoration: underline'>one more time</span> on your database in order to get-back the datas used to print the result.
            <br/>
            For example, query with <span style='color: orange'>CREATE</span> or <span style='color: orange'>UPDATE</span> statement without any 'RETURNING' statement will not necessary print a table unlike <span style='color: blue'>SELECT</span> statement,
            <br/>
            <span style='text-decoration: underline'>but it will still be executed one time in the background during the attempt of printing process</span>.
            <br/>
            So when you want to print the result, use preferably 'SELECT' statement to be sure to not execute an unwanted query twice.
        </div>
        """)

    name = fields.Text(string="Query")
    query_id = fields.Many2one('query.tool', string="Query origin")
    caution_html = fields.Html(string="CAUTION", default=get_default_caution_html)
    understand = fields.Boolean(string="I understand")

    def pdf_print(self):
        if self:
            self = self.sudo()
            first = self[0]
            action_print_pdf = self.env.ref('inom_pg_query_toolkit.action_print_pdf')
            if first.orientation == 'landscape':
                action_print_pdf.paperformat_id.orientation = "Landscape"
            elif first.orientation == 'portrait':
                action_print_pdf.paperformat_id.orientation = "Portrait"
            return action_print_pdf.with_context(report_orientation=first.orientation).report_action(first.query_id)

