"""Authoritative calculations for non-jewelry drafts and replacement loans."""
import math

import frappe
from frappe.utils import flt
from pawnshop_management.pawnshop_management.jewelry_interest import inferred_rate, valid_rate

TICKET = "Pawn Ticket Non Jewelry"


def historical_rate(doc):
    rate = doc.get("interest_rate")
    if not valid_rate(rate):
        rate = inferred_rate(doc)
    if not valid_rate(rate):
        frappe.throw("Cannot establish the historical interest rate for {}. Review the source ticket before proceeding.".format(doc.name))
    return float(rate)


def apply_ticket_rate(doc):
    previous = doc.get_doc_before_save()
    if previous and previous.docstatus == 1:
        return
    source = doc.get("amended_from") or doc.flags.get("interest_source_ticket")
    if source:
        rate = historical_rate(frappe.get_doc(TICKET, source))
    elif previous and valid_rate(previous.get("interest_rate")):
        rate = float(previous.interest_rate)
    else:
        rate = frappe.get_single("Pawnshop Management Settings").gadget_interest_rate
    if not valid_rate(rate):
        frappe.throw("Gadget interest rate must be greater than zero and at most 100%.")
    try:
        principal = float(doc.desired_principal)
    except (TypeError, ValueError):
        principal = float('nan')
    if not math.isfinite(principal) or principal <= 0:
        frappe.throw("Desired Principal must be a positive number.")
    doc.interest_rate = float(rate)
    doc.interest = flt(principal * doc.interest_rate / 100, doc.precision("interest"))
    doc.net_proceeds = flt(principal - doc.interest, doc.precision("net_proceeds"))


@frappe.whitelist()
def get_interest_rate(ticket=None, source=None):
    if ticket or source:
        doc = frappe.get_doc(TICKET, ticket or source)
        doc.check_permission("read")
        return historical_rate(doc)
    rate = frappe.get_single("Pawnshop Management Settings").gadget_interest_rate
    if not valid_rate(rate):
        frappe.throw("Gadget interest rate must be greater than zero and at most 100%.")
    return float(rate)
