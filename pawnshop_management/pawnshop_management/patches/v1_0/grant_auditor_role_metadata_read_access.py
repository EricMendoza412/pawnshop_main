import frappe
from frappe.permissions import add_permission


AUDITOR_READ_PERMISSIONS = {
	"Role": (0,),
	"Role Profile": (0, 1),
}


def execute():
	for doctype, permission_levels in AUDITOR_READ_PERMISSIONS.items():
		if not frappe.db.exists("DocType", doctype):
			continue

		for permission_level in permission_levels:
			add_permission(doctype, "Auditor", permission_level, "read")
			permission_name = frappe.db.get_value(
				"Custom DocPerm",
				{
					"parent": doctype,
					"role": "Auditor",
					"permlevel": permission_level,
					"if_owner": 0,
				},
			)
			if permission_name:
				frappe.db.set_value(
					"Custom DocPerm", permission_name, "read", 1, update_modified=False
				)

		frappe.clear_cache(doctype=doctype)
