"""Persist jewelry loan rates independently of changing promotion settings."""
import math

import frappe
from frappe.utils import cint, flt, getdate, nowdate

TICKET = "Pawn Ticket Jewelry"
ELIGIBLE_STATES = ("Active", "Expired", "Returned")


def valid_rate(value):
    try:
        return math.isfinite(float(value)) and 0 < float(value) <= 100
    except (TypeError, ValueError):
        return False


def inferred_rate(doc):
    principal, interest = flt(doc.desired_principal), flt(doc.interest)
    if not math.isfinite(principal) or not math.isfinite(interest) or principal <= 0 or interest <= 0:
        return None
    # Prefer a conventional percentage when it reproduces the recorded currency amount.
    raw = interest / principal * 100
    for precision in (2, 6):
        rate = round(raw, precision)
        if valid_rate(rate) and abs(principal * rate / 100 - interest) <= 0.005001:
            return rate
    return None


def resolve_rate(doc, persist=False, required=True):
    rate = doc.get("interest_rate")
    if not valid_rate(rate):
        rate = inferred_rate(doc)
    if not valid_rate(rate):
        if required:
            frappe.throw("Cannot establish the historical interest rate for {}. Administrator must amend the ticket and confirm Interest rate used before financial processing.".format(doc.name))
        return None
    rate = float(rate)
    if persist and not valid_rate(doc.get("interest_rate")):
        frappe.db.set_value(TICKET, doc.name, "interest_rate", rate, update_modified=False)
        doc.interest_rate = rate
    return rate


def validate_promo_settings(settings):
    rows = getattr(settings, "promo_schedule", None) or []
    if rows and not valid_rate(settings.get("promo_interest")):
        frappe.throw("Promo interest must be greater than zero and at most 100%.")
    for i, row in enumerate(rows):
        if not row.branch or not row.start_date or not row.end_date or getdate(row.start_date) > getdate(row.end_date):
            frappe.throw("Each promo schedule needs a branch and a valid Start Date / End Date range.")
        for other in rows[:i]:
            if row.branch == other.branch and getdate(row.start_date) <= getdate(other.end_date) and getdate(other.start_date) <= getdate(row.end_date):
                frappe.throw("Promo schedule dates overlap for {}.".format(row.branch))


def promo_eligible(settings, branch, loan_date, creation=None):
    today = getdate(nowdate())
    if not branch or not loan_date or getdate(loan_date) != today:
        return False
    if creation and getdate(creation) != today:
        return False
    return valid_rate(settings.get("promo_interest")) and any(
        row.branch == branch and getdate(row.start_date) <= today <= getdate(row.end_date)
        for row in settings.get("promo_schedule") or []
    )


def apply_ticket_rate(doc):
    previous = doc.get_doc_before_save()
    source_name = doc.get("amended_from") or doc.flags.get("interest_source_ticket")
    source = frappe.get_doc(TICKET, source_name) if source_name else None
    is_admin_amend = bool(doc.get("amended_from") and frappe.session.user == "Administrator" and (not previous or previous.docstatus == 0))
    # Existing finalized tickets keep their recorded amounts, even during status changes.
    if previous and previous.docstatus == 1:
        if flt(doc.get("interest_rate")) != flt(previous.get("interest_rate")) or cint(doc.get("use_promo_interest_rate")) != cint(previous.get("use_promo_interest_rate")):
            frappe.throw("A finalized ticket's interest rate can only be corrected by Administrator through amendment.")
        rate = resolve_rate(previous, required=False)
        if rate:
            doc.interest_rate = rate
        return
    if source:
        rate = resolve_rate(source, required=not is_admin_amend)
        if is_admin_amend:
            if not valid_rate(doc.get("interest_rate")):
                if not rate or previous or doc.get("interest_rate") not in (None, "", 0, 0.0):
                    frappe.throw("Administrator must enter a valid Interest rate used on this amendment.")
            else:
                rate = float(doc.interest_rate)
        doc.use_promo_interest_rate = cint(source.get("use_promo_interest_rate"))
    else:
        settings = frappe.get_single("Pawnshop Management Settings")
        if cint(doc.get("use_promo_interest_rate")):
            if not promo_eligible(settings, doc.branch, doc.date_loan_granted, doc.creation):
                frappe.throw("Initial promo tickets must be created and submitted on the same eligible day for the issuing branch.")
            rate = settings.promo_interest
        else:
            rate = settings.jewelry_interest_rate
    if not valid_rate(rate):
        frappe.throw("Interest rate used must be greater than zero and at most 100%.")
    try:
        principal = float(doc.desired_principal)
    except (TypeError, ValueError):
        principal = float('nan')
    if not math.isfinite(principal) or principal <= 0:
        frappe.throw("Desired Principal must be a positive number.")
    doc.interest_rate = float(rate)
    doc.interest = flt(flt(doc.desired_principal) * doc.interest_rate / 100, doc.precision("interest"))
    doc.net_proceeds = flt(flt(doc.desired_principal) - doc.interest, doc.precision("net_proceeds"))


@frappe.whitelist()
def get_interest_context(branch=None, loan_date=None, ticket=None, source=None):
    settings = frappe.get_single("Pawnshop Management Settings")
    result = {"eligible": promo_eligible(settings, branch, loan_date), "regular_rate": settings.jewelry_interest_rate, "promo_rate": settings.promo_interest}
    if ticket or source:
        doc = frappe.get_doc(TICKET, ticket or source)
        doc.check_permission("read")
        result.update(rate=resolve_rate(doc, required=False), promo=cint(doc.get("use_promo_interest_rate")))
        if ticket:
            result["eligible"] = promo_eligible(settings, branch, loan_date, doc.creation)
    return result


@frappe.whitelist()
def get_ticket_rate(ticket):
    doc = frappe.get_doc(TICKET, ticket)
    doc.check_permission("read")
    return resolve_rate(doc)


def prepare_receipt(doc):
    if doc.pawn_ticket_type != TICKET or not doc.pawn_ticket_no or doc.transaction_type == "Others":
        return
    ticket = frappe.get_doc(TICKET, doc.pawn_ticket_no)
    rate = resolve_rate(ticket, persist=True)
    if cint(ticket.get("use_promo_interest_rate")) and (
        doc.get("other_discount_st") not in (None, "", "None") or flt(doc.get("discount")) != 0
    ):
        frappe.throw("Promo loans are not eligible for the early-redemption discount. Remove the short-term discount and recalculate the receipt.")
    if abs(flt(doc.principal_amount) - flt(ticket.desired_principal)) > 0.005:
        frappe.throw("The ticket principal changed. Refresh the receipt before submitting.")
    if doc.transaction_type in ("Amortization", "Renewal w/ Amortization"):
        principal = flt(ticket.desired_principal) - flt(doc.additional_amortization)
        if principal < 0:
            frappe.throw("Amortization cannot exceed the remaining principal.")
        expected = flt(principal * rate / 100, doc.precision("advance_interest"))
        if abs(flt(doc.advance_interest) - expected) > 0.005:
            frappe.throw("Advance interest does not match the ticket's saved rate. Refresh the receipt and recalculate before submitting.")
