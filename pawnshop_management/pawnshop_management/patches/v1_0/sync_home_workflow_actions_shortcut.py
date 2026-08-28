import frappe


SHORTCUT_LABEL = "My Workflow Actions"
SHORTCUT_LINK = "Workflow Action"


def execute():
	sync_home_workflow_actions_shortcut()
	frappe.clear_cache()


def sync_home_workflow_actions_shortcut():
	"""Expose the current user's open workflow actions without changing other Home shortcuts."""
	if not frappe.db.exists("Workspace", "Home"):
		return

	workspace = frappe.get_doc("Workspace", "Home")
	shortcut = next(
		(
			row
			for row in workspace.shortcuts
			if row.link_to == SHORTCUT_LINK or row.label == SHORTCUT_LABEL
		),
		None,
	)

	if shortcut is None:
		shortcut = workspace.append("shortcuts", {})

	shortcut.update(
		{
			"type": "DocType",
			"label": SHORTCUT_LABEL,
			"link_to": SHORTCUT_LINK,
			"doc_view": "List",
			"color": "Orange",
			"format": "{} Open",
			"stats_filter": '{"status":"Open"}',
		}
	)
	workspace.save(ignore_permissions=True)
