import frappe


def execute():
	# Patches run before newly added standard DocTypes are synchronized.
	if not frappe.db.exists("DocType", "FX Selling") or not frappe.db.exists("Workspace", "Foreign Exchange"):
		return
	workspace = frappe.get_doc("Workspace", "Foreign Exchange")
	links = [row.as_dict() for row in workspace.links]
	wanted = [
		{"type": "Card Break", "label": "FX Selling", "link_type": "DocType"},
		{"type": "Link", "label": "New FX Selling", "link_to": "FX Selling", "link_type": "DocType"},
		{"type": "Link", "label": "FX Selling Transactions", "link_to": "FX Selling", "link_type": "DocType"},
	]
	existing_labels = {row.get("label") for row in links}
	workspace.set("links", [row for row in wanted if row["label"] not in existing_labels] + links)
	workspace.save(ignore_permissions=True)
	frappe.clear_cache()
