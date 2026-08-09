import frappe
from frappe.permissions import add_permission


DOCTYPES = ("Fund Transfer", "Vault Cash Position")


def execute():
	for doctype in DOCTYPES:
		if not frappe.db.exists("DocType", doctype):
			continue
		add_permission(doctype, "System Manager", 0, "read")
		permission = frappe.db.get_value(
			"Custom DocPerm",
			{"parent": doctype, "role": "System Manager", "permlevel": 0, "if_owner": 0},
		)
		frappe.db.set_value(
			"Custom DocPerm",
			permission,
			{"cancel": 1, "delete": 1},
			update_modified=False,
		)
		frappe.clear_cache(doctype=doctype)
