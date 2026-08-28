import frappe


SHORTCUT_LABEL = "VC Turnovers for Acceptance"
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
			if row.link_to == SHORTCUT_LINK
			or row.label in {"My Workflow Actions", SHORTCUT_LABEL}
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
			"format": "{} Pending",
			"stats_filter": (
				'{"status":"Open","user":frappe.session.user,'
				'"reference_doctype":"VC Turnover Checklist",'
				'"workflow_state":"For Acceptance"}'
			),
		}
	)
	workspace.save(ignore_permissions=True)
