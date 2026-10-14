# Copyright 2018 Tecnativa - Sergio Teruel
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, tools


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

    def _get_delivered_margin_moves(self):
        """Gets all done Stock Moves that should be considered for Delivered
        Margin calculation: valued outgoing moves and customer returns to
        refund."""
        self.ensure_one()
        return self.move_ids.filtered(
            lambda m: m.state == "done"
            and (
                m.is_out
                or (m.is_in and m.to_refund and m.location_id.usage == "customer")
            )
        )

    @api.depends(
        "margin",
        "qty_delivered",
        "product_uom_qty",
        "move_ids.state",
        "move_ids.value",
    )
    def _compute_margin_delivered(self):
        """Computes the Delivered Margin of the Lines.

        It is calculated based on the value of the Stock Moves of each Line
        (v19: stock.valuation.layer was replaced by stock.move.value).
        """
        digits = self.env["decimal.precision"].precision_get("Product Price")
        self.margin_delivered = 0.0
        self.margin_delivered_percent = 0.0
        self.purchase_price_delivery = 0.0
        for line in self.filtered("qty_delivered"):
            # we need to compute the price reduce to avoid rounding issues
            # the one stored in the line is rounded to the product price precision
            price_reduce_taxexcl = (
                line.price_subtotal / line.product_uom_qty
                if line.product_uom_qty
                else 0.0
            )

            if not line.product_id.is_storable:
                currency = (
                    line.order_id.pricelist_id.currency_id
                    or line.company_id.currency_id
                )
                price = line.purchase_price
                line.margin_delivered = currency.round(
                    line.price_subtotal - (price * line.qty_delivered)
                )
                line.purchase_price_delivery = price
            else:
                # v19 move values and valued quantities are unsigned: outgoing
                # moves are counted negative, like the v18 valuation layers
                value_delivered = qty_delivered = 0.0
                for move in line._get_delivered_margin_moves():
                    sign = -1 if move.is_out else 1
                    value_delivered += sign * move.value
                    qty_delivered += sign * move.product_id.uom_id._compute_quantity(
                        move._get_valued_qty(), line.product_uom_id
                    )
                qty_delivered = qty_delivered or -line.qty_delivered
                # purchase_price_delivery always will be positive
                # because division of same signs
                line.purchase_price_delivery = tools.float_round(
                    value_delivered / qty_delivered, precision_digits=digits
                )
                # Inverse qty_delivered because outgoing quantities are negative
                line.margin_delivered = -qty_delivered * (
                    price_reduce_taxexcl - line.purchase_price_delivery
                )
            # compute percent margin based on delivered quantities or ordered
            # quantities
            if price_reduce_taxexcl:
                line.margin_delivered_percent = (
                    price_reduce_taxexcl - line.purchase_price_delivery
                ) / price_reduce_taxexcl
