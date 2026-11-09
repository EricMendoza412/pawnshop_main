import frappe


def execute():
	if not frappe.db.exists("Branch", "Bulk NJ"):
		return
	if frappe.db.exists("Branch IP Addressing", "Bulk NJ"):
		frappe.db.set_value("Branch IP Addressing", "Bulk NJ", "branch_code", "BN")
	else:
		frappe.get_doc({"doctype": "Branch IP Addressing", "branch": "Bulk NJ", "branch_code": "BN"}).insert(ignore_permissions=True)
	if not frappe.db.exists("Pawnshop Naming Series", "Bulk NJ"):
		frappe.get_doc({"doctype": "Pawnshop Naming Series", "branch": "Bulk NJ", "nj_transfer_form": 1}).insert(ignore_permissions=True)
