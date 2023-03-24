{
    'name': 'Clancy AirDrop by Clancyworld',
    'version': '15.0.1.0.4',
    'category': 'Sales',
    'summary': 'Module for airdropping NFTs to selected users in the Odoo system',
    'description': 'This module allows users to create AirDrop campaigns in the Odoo system, selecting users based on certain criteria and assigning them a specific NFT product for purchase. The AirDrop module then generates sales orders and invoices for the selected users, with publishing dates in the future.',
    'depends': ['base', 'sale', 'product'],
    'data': [
        'views/clancy_airdrop_form.xml',
        'views/clancy_airdrop_kanban.xml',
        'views/clancy_airdrop_search.xml',
        'views/clancy_airdrop_tree.xml',
        'views/clancy_airdrop_wizard.xml',
        'views/clancy_airdrop_actions.xml',
        'views/clancy_airdrop_menu.xml',
        'security/ir.model.access.csv'
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'images': ['static/description/clancy_logo.png'],
}