from odoo import models, fields, api, _

class ClancyAirdropWizard(models.TransientModel):
    _name = 'clancy.airdrop.wizard'
    _description = 'Clancy AirDrop Wizard by Clancyworld'

    name = fields.Char(string='Name', required=True)
    selection_criteria = fields.Char(string='Selection Criteria', required=True)
    assigned_product_id = fields.Many2one('product.product', string='Assigned Product', required=True)
    publishing_date = fields.Date(string='Publishing Date', required=True)

    def action_create_airdrop(self):
        airdrop_data = {
            'name': self.name,
            'selection_criteria': self.selection_criteria,
            'assigned_product_id': self.assigned_product_id.id,
            'publishing_date': self.publishing_date,
            'state': 'draft',
        }
        self.env['clancy.airdrop'].create(airdrop_data)
