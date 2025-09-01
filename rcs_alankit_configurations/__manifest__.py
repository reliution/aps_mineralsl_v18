# -*- coding: utf-8 -*

{
    'name': 'Common Configuration of Alankit',
    'summary': 'Alankit common configuration',
    'description': """""",
    'author': 'Reliution',
    'website': 'https://www.reliution.com/',
    'license': 'AGPL-3',
    'category': 'Tools',
    'version': '1.0',
    'sequence': 0,
    'currency': 'USD',
    'price': '0',
    'depends': ['base_setup','account'],
    'data': [
        'security/ir.model.access.csv',
        'views/alankit_configuration_views.xml',
        'views/account_move.xml'
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
    "images": [],
}
