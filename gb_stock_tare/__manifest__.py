# -*- coding: utf-8 -*-
{
    'name': 'Germans Barri - Gestión de Tara',
    'version': '19.0.2.0.0',
    'summary': 'Tara automática por producto en recepciones y expediciones',
    'author': 'Process Control',
    'category': 'Inventory',
    'depends': ['stock', 'product'],
    'data': [
        'security/ir.model.access.csv',
        'views/stock_picking_views.xml',
    ],
    'installable': True,
    'license': 'LGPL-3',
}
