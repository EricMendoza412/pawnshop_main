"""Calendar-day terms shared by pawn ticket forms and server creation paths."""

import frappe
from frappe.utils import add_days, getdate


LOAN_PERIOD_DEFAULTS = {
    "jewelry_maturity_days": 30,
    "jewelry_expiry_days": 120,
    "non_jewelry_maturity_days": 30,
    "non_jewelry_expiry_days": 30,
}
TICKET_PREFIXES = {
    "Pawn Ticket Jewelry": "jewelry",
    "Pawn Ticket Non Jewelry": "non_jewelry",
}


def validate_loan_periods(settings):
    periods = {}
    for field in LOAN_PERIOD_DEFAULTS:
        value = getattr(settings, field, None)
        try:
            number = float(value)
            valid = number > 0 and number.is_integer()
        except (TypeError, ValueError):
            valid = False
        if not valid:
            frappe.throw("{} must be a positive whole number.".format(field.replace("_", " ").title()))
        periods[field] = int(number)
    for prefix in TICKET_PREFIXES.values():
        if periods[prefix + "_expiry_days"] < periods[prefix + "_maturity_days"]:
            frappe.throw("{} expiry period must be at least its maturity period.".format(prefix.replace("_", " ").title()))
    return periods


@frappe.whitelist()
def calculate_pawn_ticket_dates(pawn_ticket_type, date_loan_granted):
    if pawn_ticket_type not in TICKET_PREFIXES:
        frappe.throw("Unsupported pawn ticket type.")
    if not date_loan_granted:
        frappe.throw("Date Loan Granted is required.")
    settings = frappe.get_single("Pawnshop Management Settings")
    periods = validate_loan_periods(settings)
    prefix = TICKET_PREFIXES[pawn_ticket_type]
    return {
        "maturity_date": str(add_days(date_loan_granted, periods[prefix + "_maturity_days"])),
        "expiry_date": str(add_days(date_loan_granted, periods[prefix + "_expiry_days"])),
    }


def set_pawn_ticket_dates(doc):
    # Paper-jam replacements retain the original loan's contractual dates.
    if doc.flags.get("preserve_loan_dates") or not doc.date_loan_granted:
        return
    previous = doc.get_doc_before_save()
    if not previous and doc.get("amended_from"):
        previous = frappe.get_doc(doc.doctype, doc.amended_from)
    if previous and getdate(previous.date_loan_granted) == getdate(doc.date_loan_granted):
        doc.maturity_date = previous.maturity_date
        doc.expiry_date = previous.expiry_date
        return
    doc.update(calculate_pawn_ticket_dates(doc.doctype, doc.date_loan_granted))
