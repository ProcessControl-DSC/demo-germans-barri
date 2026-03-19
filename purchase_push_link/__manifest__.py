# Copyright 2025 Process Control
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

{
    "name": "Purchase Push Link",
    "summary": "Relacionar albaranes secundarios con el pedido de compra original",
    "version": "19.0.1.0.0",
    "category": "Purchases",
    "license": "LGPL-3",
    "author": "Process Control",
    "website": "https://www.processcontrol.es",
    "depends": ["purchase_stock"],
    "data": ["views/stock_picking_type_view.xml"],
    "installable": True,
}
