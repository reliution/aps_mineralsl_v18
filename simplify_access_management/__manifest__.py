# -*- coding: utf-8 -*-

{
    "name": "Simplify Access Management",
    "version": "18.0.7.6.15",
    "sequence": 5,
    "author": "Reliution",
    "license": "OPL-1",
    "category": "Services",
    "summary": """All In One Access Management App for setting the correct access rights for fields, models, menus, views for any module and for any user.""",
    "description": "",
    "data": [
        "security/res_groups.xml",
        "security/ir.model.access.csv",
        "data/view_data.xml",
        "views/access_management_view.xml",
        "views/res_users_view.xml",
        "views/store_model_nodes_view.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "/simplify_access_management/static/src/js/action_menus.js",
            "/simplify_access_management/static/src/js/hide_chatter.js",
            "/simplify_access_management/static/src/js/cog_menu.js",
            "/simplify_access_management/static/src/js/form_controller.js",
            "/simplify_access_management/static/src/js/model_field_selector.js",
            "/simplify_access_management/static/src/js/search_bar_menu.js",
        ],
        "assets_backend_lazy": [
            "/simplify_access_management/static/src/js/pivot_grp_menu.js",
            "/simplify_access_management/static/src/js/pivot_renderer.js",
        ],
    },
    "depends": ["web", "advanced_web_domain_widget"],
    "post_init_hook": "post_install_action_dup_hook",
    "application": True,
    "installable": True,
    "auto_install": False,
}
