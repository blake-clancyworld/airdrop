{
    'name': 'Clancy3 AirDrop by Clancyworld',
    'version': '15.0.1.0.4',
    'category': 'Sales',
    'summary': 'Module for airdropping NFTs to selected users in the Odoo system',
    'description': 'This module allows users to create AirDrop campaigns in the Odoo system, selecting users based on certain criteria and assigning them a specific NFT product for purchase. The AirDrop module then generates sales orders and invoices for the selected users, with publishing dates in the future.',
    'depends': ['base', 'sale', 'product', 'contacts'],
    'data': [
        'views/airdrop_contact_views.xml',
        'views/airdrop_list_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',

}
