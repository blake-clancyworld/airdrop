from odoo import models, fields, api, _

import logging
_logger = logging.getLogger(__name__)
_logger.setLevel(logging.DEBUG)

class ClancyAirdrop(models.Model):
    _name = 'clancy.airdrop'
    _description = 'Clancy AirDrop by Clancyworld'

    name = fields.Char(string='Name', required=True)
    query = fields.Selection(
        [
            ('all', 'All Partners'),
            ('inactive', 'Inactive Partners'),
            ('active', 'Active Partners'),
            ('customers', 'Customers'),
            ('vendors', 'Vendors')
        ],
        string='Predefined Query',
        required=True,
        default='all'
    )
    custom_query = fields.Char(string='Custom Query')
    assigned_product_id = fields.Many2one('product.product', string='Assigned Product', required=True)
    publishing_date = fields.Date(string='Publishing Date', required=True)
    state = fields.Selection(
        [('draft', 'Draft'), ('validated', 'Validated'), ('canceled', 'Canceled')],
        string='Status', readonly=True, default='draft', required=True
    )

    @api.constrains('publishing_date')
    def _check_publishing_date(self):
        today = fields.Date.today()
        for record in self:
            if record.publishing_date < today:
                raise ValidationError(_("Publishing date must be in the future."))

    def retrieve_users(self):
        if self.query == 'all':
            users = self.env['res.partner'].search([])
        elif self.query == 'inactive':
            users = self.env['res.partner'].search([('active', '=', False)])
        elif self.query == 'active':
            users = self.env['res.partner'].search([('active', '=', True)])
        elif self.query == 'customers':
            users = self.env['res.partner'].search([('customer', '=', True)])
        elif self.query == 'vendors':
            users = self.env['res.partner'].search([('supplier', '=', True)])
        else:
            selection_criteria = self.custom_query
            domain = []
            for criterion in selection_criteria.split(';'):
                if criterion.strip() != '':
                    field, operator, value = criterion.split(',')
                    domain.append((field.strip(), operator.strip(), value.strip()))
            users = self.env['res.partner'].search(domain)
        return users

    def generate_sales_orders(self):
        users = self.retrieve_users()
        product = self.assigned_product_id
        publishing_date = self.publishing_date
        orders = []
        for user in users:
            order = self.env['sale.order'].create({
                'partner_id': user.id,
                'order_line': [(0, 0, {
                    'product_id': product.id,
                    'product_uom_qty': 1,
                    'price_unit': product.list_price,
                    'name': product.name,
                })],
                'validity_date': publishing_date,
            })
            orders.append(order)
        return orders

    def generate_invoices(self):
        orders = self.generate_sales_orders()
        invoices = []
        for order in orders:
            invoice = order._create_invoices()
            invoices.append(invoice)
        return invoices

    def action_validate(self):
        self.write({'state': 'validated'})

    def action_cancel(self):
        self.write({'state': 'canceled'})