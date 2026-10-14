# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
# The v19 migration left the delivered margin stubbed to 0.0: recompute it on
# every delivered line now that it is computed from stock.move.value.
from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    lines = env["sale.order.line"].search([("qty_delivered", "!=", 0)])
    model = env["sale.order.line"]
    for fname in (
        "margin_delivered",
        "margin_delivered_percent",
        "purchase_price_delivery",
    ):
        env.add_to_compute(model._fields[fname], lines)
    env.flush_all()
