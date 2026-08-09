import frappe
from frappe.permissions import add_permission


PERMISSIONS = {
	"System Manager": {
		"read": 1,
		"write": 1,
		"create": 1,
		"submit": 1,
		"report": 1,
		"export": 1,
		"print": 1,
		"email": 1,
		"share": 1,
	},
	"All": {
		"read": 1,
		"write": 1,
		"create": 1,
		"submit": 1,
		"report": 1,
		"print": 1,
		"email": 1,
	},
	"Accounting Analyst": {
		"read": 1,
		"report": 1,
		"export": 1,
		"print": 1,
		"email": 1,
	},
	"Rover": {
		"read": 1,
		"report": 1,
		"print": 1,
		"email": 1,
	},
}


def execute():
	if not frappe.db.exists("DocType", "Fund Transfer"):
		return
	for role, values in PERMISSIONS.items():
		add_permission("Fund Transfer", role, 0, "read")
		name = frappe.db.get_value(
			"Custom DocPerm", {"parent": "Fund Transfer", "role": role, "permlevel": 0, "if_owner": 0}
		)
		reset_values = {
			"select": 0,
			"read": 0,
			"write": 0,
			"create": 0,
			"delete": 0,
			"submit": 0,
			"cancel": 0,
			"amend": 0,
			"report": 0,
			"export": 0,
			"import": 0,
			"share": 0,
			"print": 0,
			"email": 0,
		}
		reset_values.update(values)
		frappe.db.set_value("Custom DocPerm", name, reset_values, update_modified=False)
	frappe.clear_cache(doctype="Fund Transfer")
