# -*- coding: utf-8 -*

{
    'name': 'RCS Alankit E-waybill',
    'summary': 'RCS Alankit E-waybill',
    'description': """""",
    'author': 'Reliution',
    'website': 'https://www.reliution.com/',
    'license': 'AGPL-3',
    'category': 'Accounting',
    'version': '1.0',
    'sequence': 0,
    'currency': 'USD',
    'price': '0',
    'depends': ['rcs_alankit_configurations', 'rcs_process_logs', 'account', 'stock'],
    'data': [
        # 'data/ir_cron.xml',
        'security/ir.model.access.csv',
        'views/alankit_ewaybill_instance.xml',
        'views/account_move.xml',
        'views/stock_picking.xml',
        'wizard/add_ewaybill_cancel_reason.xml',
        'report/report_alankit_ewaybill.xml'
    ],
     'external_dependencies': {'python': ['pycryptodome']},
    'installable': True,
    'auto_install': False,
    'application': True,
    "images": [],
}
