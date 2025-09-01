# -*- coding: utf-8 -*-

{
    "name": "Execute Python Code",
    "description": """
        Installing this module, user will able to execute python code from Odoo
    """,
    "category": "Extra Tools",
    "website": "",
    "maintainer": "",
    "version": "18.0",
    "author": "Reliution",
    "license": "LGPL-3",
    "depends": ["base"],
    "data": [
        "security/ir.model.access.csv",
        "view/python_code_view.xml",
    ],
    "sequence": 0,
    "installable": True,
    "auto_install": False,
    "application": True,
}
