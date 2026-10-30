import frappe

from pawnshop_management.pawnshop_management.loan_dates import LOAN_PERIOD_DEFAULTS


def execute():
    frappe.reload_doc("pawnshop_management", "doctype", "pawnshop_management_settings")
    for field, default in LOAN_PERIOD_DEFAULTS.items():
        value = frappe.db.get_value(
            "Singles",
            {"doctype": "Pawnshop Management Settings", "field": field},
            "value",
            order_by="field",
        )
        if value in (None, ""):
            frappe.db.set_single_value("Pawnshop Management Settings", field, default)
