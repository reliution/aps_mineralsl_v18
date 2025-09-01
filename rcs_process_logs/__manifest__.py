# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Common Process Logs',
    'summary': """Common Process Logs""",
    'description': """
        The Common Process Log module is a versatile tool designed to handle log management for applications. 
        Its primary features and functionalities include

        - Log Collection
        - Log Storage
        - Log Analysis
        - Integration
    """,
    'author': 'Reliution',
    'website': 'https://www.reliution.com/',
    'license': 'AGPL-3',
    'category': 'Tools',
    'version': '18.0.0.1.0',
    'sequence': 0,
    'currency': 'USD',
    'price': '9',
    'depends': ['base'],
    'data': [
        'data/ir_sequence_data.xml',
        'security/ir.model.access.csv',
        'views/common_process_log.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
    "images": ['static/description/banner.gif']
}
