"""Fill rates only; never recalculate historical financial amounts."""
import frappe
from pawnshop_management.pawnshop_management.jewelry_interest import ELIGIBLE_STATES, resolve_rate


def execute():
    frappe.reload_doc("pawnshop_management", "doctype", "jewelry_promo_schedule")
    frappe.reload_doc("pawnshop_management", "doctype", "pawnshop_management_settings")
    frappe.reload_doc("pawnshop_management", "doctype", "pawn_ticket_jewelry")
    if frappe.db.get_single_value("Pawnshop Management Settings", "promo_interest") is None:
        frappe.db.set_single_value("Pawnshop Management Settings", "promo_interest", 1)
    unresolved = []
    for row in frappe.get_all("Pawn Ticket Jewelry", filters={"workflow_state": ["in", list(ELIGIBLE_STATES)], "docstatus": ["!=", 2]}, fields=["name"]):
        doc = frappe.get_doc("Pawn Ticket Jewelry", row.name)
        if resolve_rate(doc, persist=True, required=False) is None:
            unresolved.append(doc.name)
    if unresolved:
        frappe.log_error("Administrator amendment required for tickets with unresolved historical rates:\n" + "\n".join(unresolved), "Jewelry interest rate backfill")
