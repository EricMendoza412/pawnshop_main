import frappe


DOCTYPES = ("Fund Transfer", "FX Selling")


def execute():
	for permission_doctype in ("DocPerm", "Custom DocPerm"):
		for name in frappe.get_all(
			permission_doctype,
			filters={"parent": ["in", DOCTYPES], "role": "System Manager"},
			pluck="name",
		):
			frappe.db.set_value(
				permission_doctype,
				name,
				{"cancel": 0, "delete": 0},
				update_modified=False,
			)

	for doctype in DOCTYPES:
		frappe.clear_cache(doctype=doctype)
