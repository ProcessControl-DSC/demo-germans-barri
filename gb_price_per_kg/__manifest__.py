# -*- coding: utf-8 -*-
{
    'name': 'Germans Barri - Precio por KG',
    'version': '19.0.1.0.0',
    'summary': 'Muestra el precio por kilogramo en líneas de venta y albarán',
    'author': 'Process Control',
    'category': 'Sales',
    'depends': ['sale_stock'],
    'data': [
        'views/product_template_views.xml',
        'views/sale_order_views.xml',
        'views/stock_picking_views.xml',
    ],
    'installable': True,
    'license': 'LGPL-3',
}
