# -*- coding: utf-8 -*

{
    'name': 'RCS Alankit E-invoicing',
    'summary': 'RCS Alankit E-invoicing',
    'description': """""",
    'author': 'Reliution',
    'website': 'https://www.reliution.com/',
    'license': 'AGPL-3',
    'category': 'Accounting',
    'version': '1.0',
    'sequence': 0,
    'currency': 'USD',
    'price': '0',
    'depends': ['rcs_alankit_configurations','rcs_process_logs', 'account', 'sale', 'stock'],
    'data': [
        'security/ir.model.access.csv',
        'views/alankit_einvoice_instance.xml',
        'views/account_move.xml',
        'wizard/add_einvoice_cancel_reason.xml',
        'report/report_alankit_einvoice.xml'
    ],
     'external_dependencies': {'python': ['pycryptodome']},
    'installable': True,
    'auto_install': False,
    'application': True,
    "images": [],
}
