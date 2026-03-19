# Copyright 2025 Process Control
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

{
    "name": "Cantidades stock",
    "summary": "Cálculos de disponibilidad de stock personalizados por almacén",
    "version": "19.0.1.0.0",
    "license": "LGPL-3",
    "category": "Stock",
    "author": "Process Control",
    "website": "https://www.processcontrol.es",
    "depends": ["stock"],
    "external_dependencies": {"python": ["psycopg2"]},
    "data": [
        "views/product_view.xml",
        "views/stock_location.xml",
        "views/stock_warehouse.xml",
    ],
    "installable": True,
}
