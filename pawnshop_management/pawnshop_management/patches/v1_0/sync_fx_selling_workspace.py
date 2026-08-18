import frappe


def execute():
	if not frappe.db.exists("DocType", "FX Selling") or not frappe.db.exists("Workspace", "Foreign Exchange"):
		return
	workspace = frappe.get_doc("Workspace", "Foreign Exchange")
	workspace.disable_user_customization = 1
	workspace.icon = "star"
	workspace.module = "Pawnshop Management"
	workspace.category = "Modules"
	workspace.set("links", [
		{"type": "Card Break", "label": "FX Documents", "link_to": "FX Selling", "link_type": "DocType"},
		{"type": "Link", "label": "FX Selling Transactions", "link_to": "FX Selling", "link_type": "DocType"},
		{"type": "Link", "label": "Fund Transfer", "link_to": "Fund Transfer", "link_type": "DocType"},
	])
	workspace.set("shortcuts", [
		{"type": "DocType", "label": "New FX Selling", "link_to": "FX Selling", "doc_view": "New"},
	])
	workspace.save(ignore_permissions=True)
	frappe.clear_cache()
