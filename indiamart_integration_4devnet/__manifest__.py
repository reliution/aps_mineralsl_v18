{
    'name': "Indiamart Integration 4devnet",
    'version': '18.0.1.0',
    'category': 'Sales/CRM',
    'summary': "Indiamart Integration 4devnet",
    'description': """
This module fetches the leads from indiamart and creates the lead in odoo.
""",
    'depends': ['base_setup', 'crm'],

    # Views
    'data': [
        'security/ir.model.access.csv',
        'views/log_views.xml',
        'views/indiamart_config_view.xml',
        'views/indiamart_menus.xml',
        'data/sales_team_data.xml',
        'data/cron.xml',
    ],
    #Other Information
    'price':0.00,
    'currency': 'INR',
    'author': '4devnet',
    'maintainer': '4devnet.',
    'license': "AGPL-3",
    'images': ['static/description/banner.jpg'],
    'installable': True,
    'auto_install': False,
    'application': True,
}
