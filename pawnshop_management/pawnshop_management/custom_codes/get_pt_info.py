import frappe

@frappe.whitelist()
def if_printed(pawn_ticket):
    pr_renewal_check = frappe.get_all("Access Log", filters={"method": "Print", "reference_document": pawn_ticket}, fields=["reference_document"])
    if pr_renewal_check:
        return True
    else:
        return False