# Copyright 2025 Process Control
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

{
    "name": "Intrastat Landed Cost",
    "version": "19.0.1.0.0",
    "summary": "Costes en destino: método de división por código arancelario",
    "license": "LGPL-3",
    "category": "Accounting & Finance",
    "author": "Process Control",
    "website": "https://www.processcontrol.es",
    "depends": ["stock_landed_costs", "account_intrastat"],
    "data": [
        "views/intrastat_code_view.xml",
        "views/stock_landed_cost_views.xml",
    ],
    "installable": True,
}
