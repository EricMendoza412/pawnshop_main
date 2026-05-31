import frappe

from pawnshop_management.pawnshop_management.doctype.smart_sms_log.smart_sms_log import get_reference_branch


def execute():
	if not frappe.db.has_column("SMART SMS Log", "branch"):
		return

	logs = frappe.get_all(
		"SMART SMS Log",
		filters={"branch": ["is", "not set"]},
		fields=["name", "reference_doctype", "reference_name"],
	)
	for log in logs:
		branch = get_reference_branch(log.reference_doctype, log.reference_name)
		if branch:
			frappe.db.set_value("SMART SMS Log", log.name, "branch", branch, update_modified=False)
