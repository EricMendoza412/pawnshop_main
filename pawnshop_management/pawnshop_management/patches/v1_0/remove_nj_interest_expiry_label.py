import frappe


def execute():
    name = "Interest Computation NJ"
    html = frappe.db.get_value("Print Format", name, "html")
    if html and "(EXPIRY)" in html:
        frappe.db.set_value("Print Format", name, "html", html.replace("(EXPIRY)", ""))
