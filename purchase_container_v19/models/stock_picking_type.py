# Copyright 2025 Process Control
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class StockPickingType(models.Model):
    _inherit = "stock.picking.type"

    to_refund = fields.Boolean(
        string="Contabilizar cantidad regularizaciones",
        help="Si este campo está marcado, al hacerse una regularización negativa"
        " con este tipo de operación se tendrá en cuenta su stock a la hora de "
        "calcular la cantidad recibida en los pedidos de compra",
        copy=False,
    )
    container_manual_location_dest = fields.Boolean(
        "Selección manual ubicación recepción contenedor",
        copy=False,
        help="Los tipos de operación marcados con esta casilla estarán disponibles "
        "para seleccionar en los contenedores, cuando se quiere cambiar la ubicación "
        "destino de las recepciones a almacén",
    )
    merge_moves_keep_date = fields.Boolean(
        string="Conservar fecha programada al fusionar movimientos",
        help="Cuando se fusionen movimientos de stock (por transferir de mas en un "
        "paso anterior, modifcar cantidad en un pedido, etc) se conservará la fecha "
        "programada del movimiento más antiguo por fecha de creación. Debe marcarse "
        "en operaciones de tipo de descarga de contenedors (segundo paso de compras)",
        copy=False,
    )
