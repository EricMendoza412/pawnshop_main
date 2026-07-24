import frappe

@frappe.whitelist()
def get_latest_cpr(branch):
    filters = {
        "branch": branch,
        "docstatus": 1
    }

    if frappe.db.exists('Cash Position Report', filters):
        cpr = frappe.get_last_doc(
            'Cash Position Report',
            filters=filters,
            order_by="date desc, creation desc"
        )
        return cpr.total_cash
