import frappe


WORKFLOW_NAME = "Text Blast Workflow"


def execute():
	frappe.reload_doc("pawnshop_management", "doctype", "recipient_list")
	frappe.reload_doc("pawnshop_management", "doctype", "text_blast")
	ensure_master("Workflow State", "workflow_state_name", "Draft", "Inverse")
	ensure_master("Workflow State", "workflow_state_name", "For Approval", "Primary")
	ensure_master("Workflow State", "workflow_state_name", "Sent", "Success")
	ensure_master("Workflow Action Master", "workflow_action_name", "Submit for Approval")
	ensure_master("Workflow Action Master", "workflow_action_name", "Approve")
	ensure_workflow()


def ensure_master(doctype, fieldname, value, style=None):
	if frappe.db.exists(doctype, value):
		return
	values = {"doctype": doctype, fieldname: value}
	if style:
		values["style"] = style
	frappe.get_doc(values).insert(ignore_permissions=True)


def ensure_workflow():
	workflow = frappe.get_doc("Workflow", WORKFLOW_NAME) if frappe.db.exists("Workflow", WORKFLOW_NAME) else frappe.new_doc("Workflow")
	workflow.workflow_name = WORKFLOW_NAME
	workflow.document_type = "Text Blast"
	workflow.is_active = 1
	workflow.override_status = 0
	workflow.send_email_alert = 0
	workflow.workflow_state_field = "workflow_state"
	workflow.set("states", [
		{"state": "Draft", "doc_status": "0", "allow_edit": "All"},
		{"state": "For Approval", "doc_status": "0", "allow_edit": "System Manager"},
		{"state": "Sent", "doc_status": "1", "allow_edit": "System Manager"},
	])
	workflow.set("transitions", [
		{
			"state": "Draft", "action": "Submit for Approval", "next_state": "For Approval",
			"allowed": "All", "allow_self_approval": 1,
		},
		{
			"state": "For Approval", "action": "Approve", "next_state": "Sent",
			"allowed": "Operations Manager", "allow_self_approval": 0,
			"condition": (
				"frappe.db.get_value('Has Role', {'parenttype': 'Role Profile', "
				"'parent': frappe.db.get_value('User', frappe.session.user, 'role_profile_name'), "
				"'role': 'Operations Manager'}, 'name')"
			),
		},
		{
			"state": "For Approval", "action": "Approve", "next_state": "Sent",
			"allowed": "System Manager", "allow_self_approval": 1,
			"condition": "frappe.session.user == 'Administrator'",
		},
	])
	workflow.save(ignore_permissions=True)
	frappe.clear_cache(doctype="Text Blast")
