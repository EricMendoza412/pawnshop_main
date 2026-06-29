import frappe


MAIN_WORKSPACE_LINKS = [
	{"type": "Card Break", "label": "Tickets and Receipts", "link_type": "DocType"},
	{"type": "Link", "label": "Jewelry Pawn Ticket List", "link_to": "Pawn Ticket Jewelry", "link_type": "DocType"},
	{"type": "Link", "label": "Non Jewelry Pawn Ticket", "link_to": "Pawn Ticket Non Jewelry", "link_type": "DocType"},
	{"type": "Link", "label": "Provisional Receipt", "link_to": "Provisional Receipt", "link_type": "DocType"},
	{"type": "Link", "label": "Agreement to Sell", "link_to": "Agreement to Sell", "link_type": "DocType"},
	{"type": "Link", "label": "Acknowledgement Receipt", "link_to": "Acknowledgement Receipt", "link_type": "DocType"},
	{"type": "Card Break", "label": "Envelope Items", "link_to": "Models", "link_type": "DocType"},
	{"type": "Link", "label": "Jewelry Items", "link_to": "Jewelry Items", "link_type": "DocType"},
	{"type": "Link", "label": "Non Jewelry Items", "link_to": "Non Jewelry Items", "link_type": "DocType"},
	{"type": "Card Break", "label": "Gadgets", "link_to": "Models", "link_type": "DocType"},
	{"type": "Link", "label": "Models", "link_to": "Models", "link_type": "DocType"},
	{"type": "Link", "label": "Installment Agreement Forms", "link_to": "Installment Agreement Form", "link_type": "DocType"},
	{"type": "Link", "label": "Gadgets for Sale", "link_to": "Gadgets For Sale", "link_type": "Report", "is_query_report": 1},
	{"type": "Card Break", "label": "End of Day Reports", "link_to": "Pawnshop Transaction Log", "link_type": "DocType"},
	{"type": "Link", "label": "Cash Position Report", "link_to": "Cash Position Report", "link_type": "DocType"},
	{"type": "Link", "label": "Transaction Log Report", "link_to": "Pawnshop Transaction Log", "link_type": "DocType"},
	{"type": "Card Break", "label": "Text Blast", "link_to": "SMART SMS Log", "link_type": "DocType"},
	{"type": "Link", "label": "SMS Log", "link_to": "SMART SMS Log", "link_type": "DocType"},
]


VC_WORKSPACE_LINKS = [
	{"type": "Card Break", "label": "Operations", "link_type": "DocType"},
	{"type": "Link", "label": "VC Turnover Checklist", "link_to": "VC Turnover Checklist", "link_type": "DocType"},
	{"type": "Link", "label": "Transfer Tracker", "link_to": "Transfer Tracker", "link_type": "DocType"},
	{"type": "Card Break", "label": "Summary Reports", "link_type": "Report", "is_query_report": 1},
	{"type": "Link", "label": "VC Count Report", "link_to": "VC Count Consolidated", "link_type": "Report", "is_query_report": 1},
	{"type": "Link", "label": "Transaction Log Preview", "link_to": "VC Report", "link_type": "Report", "is_query_report": 1},
	{"type": "Link", "label": "VC Turnover Lists (J, NJ, SB)", "link_to": "VC Turnover List", "link_type": "Report", "is_query_report": 1},
	{"type": "Link", "label": "VC Agreement to Sell List", "link_to": "VC Agreement to Sell List", "link_type": "Report", "is_query_report": 1},
	{"type": "Card Break", "label": "End of Day Trackers", "link_type": "Report", "is_query_report": 1},
	{"type": "Link", "label": "VC Tracker (Jewelry)", "link_to": "J End of Day Report", "link_type": "Report", "is_query_report": 1},
	{"type": "Link", "label": "VC Tracker (Gadget)", "link_to": "NJ End of the Day Repor", "link_type": "Report", "is_query_report": 1},
	{"type": "Link", "label": "Jewelry Inventory A", "link_to": "Vault Custodian Jewelry Report A", "link_type": "Report", "is_query_report": 1},
	{"type": "Link", "label": "Jewelry Inventory B", "link_to": "Vault Custodian Jewelry Report B", "link_type": "Report", "is_query_report": 1},
	{"type": "Link", "label": "Non Jewelry Inventory", "link_to": "Vault Custodian Non Jewelry Report", "link_type": "Report", "is_query_report": 1},
	{"type": "Card Break", "label": "Daily Jewelry Reports", "link_type": "Report", "is_query_report": 1},
	{"type": "Link", "label": "Daily New J-Sangla", "link_to": "Daily New J-Sangla", "link_type": "Report", "is_query_report": 1},
	{"type": "Link", "label": "New Sangla Today (J)", "link_to": "New Sangla today (J)", "link_type": "Report", "is_query_report": 1},
	{"type": "Link", "label": "Renewed PT Today (J)", "link_to": "Renewed PT today (J)", "link_type": "Report", "is_query_report": 1},
	{"type": "Link", "label": "Redeemed PT Today (J)", "link_to": "Redeemed PT today (J)", "link_type": "Report", "is_query_report": 1},
]


VC_SHORTCUTS = [
	{"type": "DocType", "label": "New VC Turnover Checklist", "link_to": "VC Turnover Checklist", "doc_view": "New"},
	{"type": "DocType", "label": "New Transfer Tracker", "link_to": "Transfer Tracker", "doc_view": "New"},
]


def execute():
	sync_main_workspace()
	sync_extended_main_workspaces()
	sync_vc_workspace()
	frappe.clear_cache()


def sync_main_workspace():
	workspace = frappe.get_doc("Workspace", "Pawnshop Management")
	_set_main_workspace_values(workspace)
	workspace.save(ignore_permissions=True)


def sync_extended_main_workspaces():
	for workspace_name in frappe.get_all("Workspace", filters={"extends": "Pawnshop Management"}, pluck="name"):
		workspace = frappe.get_doc("Workspace", workspace_name)
		_set_main_workspace_values(workspace)
		workspace.save(ignore_permissions=True)


def _set_main_workspace_values(workspace):
	workspace.cards_label = "List"
	workspace.module = "Pawnshop Management"
	workspace.category = "Modules"
	workspace.disable_user_customization = 1
	workspace.set("links", [_normalize_link(link) for link in MAIN_WORKSPACE_LINKS])


def sync_vc_workspace():
	if frappe.db.exists("Workspace", "Vault Custodian Reports"):
		workspace = frappe.get_doc("Workspace", "Vault Custodian Reports")
	else:
		workspace = frappe.new_doc("Workspace")
		workspace.label = "Vault Custodian Reports"

	workspace.cards_label = "Vault Custodian"
	workspace.category = "Modules"
	workspace.developer_mode_only = 0
	workspace.disable_user_customization = 1
	workspace.extends_another_page = 0
	workspace.hide_custom = 0
	workspace.icon = "folder-normal"
	workspace.is_default = 0
	workspace.is_standard = 1
	workspace.module = "Pawnshop Management"
	workspace.pin_to_bottom = 0
	workspace.pin_to_top = 0
	workspace.shortcuts_label = "Shortcuts"
	workspace.set("charts", [])
	workspace.set("links", [_normalize_link(link) for link in VC_WORKSPACE_LINKS])
	workspace.set("shortcuts", VC_SHORTCUTS)
	workspace.save(ignore_permissions=True)


def _normalize_link(link):
	row = {
		"hidden": link.get("hidden", 0),
		"is_query_report": link.get("is_query_report", 0),
		"label": link["label"],
		"link_type": link.get("link_type", "DocType"),
		"onboard": link.get("onboard", 0),
		"type": link["type"],
	}
	if link.get("link_to"):
		row["link_to"] = link["link_to"]
	return row
