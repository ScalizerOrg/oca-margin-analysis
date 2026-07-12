# Copyright 2018 Tecnativa - Sergio Teruel
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    margin_delivered = fields.Float(
        compute="_compute_margin_delivered",
        store=True,
        help="Total Margin of all delivered products.\n\n"
        "Formula: Delivered Quantities * (Unit Price with Discounts - "
        "Average Unit Cost of Delivered Products)\n\nValue may differ from "
        "Cost Price because Stock Valuation Layers are used instead of Cost on line.",
    )
    margin_delivered_percent = fields.Float(
        compute="_compute_margin_delivered",
        store=True,
        readonly=True,
        help="Margin percent between the Unit Price with discounts and "
        "Delivered Unit Cost.\n\n"
        "Formula: ((Unit Price with Discounts - Average Unit Cost of "
        "delivered products) / Unit Price with Discounts)",
    )
    purchase_price_delivery = fields.Float(
        compute="_compute_margin_delivered",
        store=True,
        help="Average Unit Cost of delivered products.\n\n"
        "Formula: Value Delivered / Quantity Delivered\n\n"
        "When using the FIFO method, the value of this field may not match the "
        "actual cost of the product delivered.\n"
        "There may also be differences with the costing of the Sales from "
        "Deliveries report, because when the sales order is created, it is not known "
        "exactly which units will actually be delivered to calculate their cost.\n"
        "This is because when the sales order is created, it is not known which "
        "units will actually be delivered to calculate their actual cost. You do not "
        "have this information until you validate the corresponding delivery note.",
    )

    # [MIG v19]: stock.valuation.layer was removed in Odoo 19 (replaced by
    # product.value). Original v18 code relied on move.stock_valuation_layer_ids
    # to compute delivered margin from actual outgoing/return valuation layers.
    # Until a proper v19 port is done, keep the fields declared but stub the
    # compute so the module loads. Values will remain 0.0 — do NOT rely on them
    # for reporting.
    # TODO: rewrite using product.value / stock.move accounting in v19.
    @api.depends("margin", "qty_delivered", "product_uom_qty")
    def _compute_margin_delivered(self):
        for line in self:
            line.margin_delivered = 0.0
            line.margin_delivered_percent = 0.0
            line.purchase_price_delivery = 0.0
