import frappe


def execute():
    frappe.reload_doc("pawnshop_management", "doctype", "pawnshop_management_settings")
    # Read the raw value so an absent Currency field is not converted to zero.
    value = frappe.db.get_value(
        "Singles",
        {"doctype": "Pawnshop Management Settings", "field": "jewelry_a_series_limit"},
        "value",
        order_by="field",
    )
    if value is None or value == "":
        frappe.db.set_single_value(
            "Pawnshop Management Settings", "jewelry_a_series_limit", 40000
        )
