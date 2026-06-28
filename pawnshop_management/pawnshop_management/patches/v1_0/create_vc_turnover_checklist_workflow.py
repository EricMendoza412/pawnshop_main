import frappe


WORKFLOW_NAME = "VC Turnover Checklist Workflow"
WORKFLOW_STATES = ("Draft", "For Acceptance", "Accepted", "Rejected")
WORKFLOW_ACTIONS = ("Submit", "Accept Turnover", "Reject")


def execute():
	frappe.reload_doc("pawnshop_management", "doctype", "vc_turnover_checklist")
	ensure_workflow_states()
	ensure_workflow_actions()
	ensure_workflow()
	backfill_existing_workflow_states()


def ensure_workflow_states():
	for state in WORKFLOW_STATES:
		if frappe.db.exists("Workflow State", state):
			continue

		frappe.get_doc(
			{
				"doctype": "Workflow State",
				"workflow_state_name": state,
				"style": _get_state_style(state),
			}
		).insert(ignore_permissions=True)


def ensure_workflow_actions():
	for action in WORKFLOW_ACTIONS:
		if frappe.db.exists("Workflow Action Master", action):
			continue

		frappe.get_doc(
			{
				"doctype": "Workflow Action Master",
				"workflow_action_name": action,
			}
		).insert(ignore_permissions=True)


def ensure_workflow():
	if frappe.db.exists("Workflow", WORKFLOW_NAME):
		workflow = frappe.get_doc("Workflow", WORKFLOW_NAME)
	else:
		workflow = frappe.new_doc("Workflow")
		workflow.workflow_name = WORKFLOW_NAME

	workflow.document_type = "VC Turnover Checklist"
	workflow.is_active = 1
	workflow.override_status = 0
	workflow.send_email_alert = 0
	workflow.workflow_state_field = "workflow_state"

	workflow.set(
		"states",
		[
			{
				"state": "Draft",
				"doc_status": "0",
				"allow_edit": "All",
			},
			{
				"state": "For Acceptance",
				"doc_status": "1",
				"allow_edit": "All",
			},
			{
				"state": "Accepted",
				"doc_status": "1",
				"allow_edit": "System Manager",
			},
			{
				"state": "Rejected",
				"doc_status": "2",
				"allow_edit": "System Manager",
			},
		],
	)
	workflow.set(
		"transitions",
		[
			{
				"state": "Draft",
				"action": "Submit",
				"next_state": "For Acceptance",
				"allowed": "All",
				"allow_self_approval": 1,
			},
			{
				"state": "For Acceptance",
				"action": "Accept Turnover",
				"next_state": "Accepted",
				"allowed": "All",
				"allow_self_approval": 1,
				"condition": "doc.received_by == frappe.session.user",
			},
			{
				"state": "For Acceptance",
				"action": "Reject",
				"next_state": "Rejected",
				"allowed": "System Manager",
				"allow_self_approval": 1,
			},
		],
	)

	workflow.save(ignore_permissions=True)
	frappe.clear_cache(doctype="VC Turnover Checklist")


def backfill_existing_workflow_states():
	frappe.db.sql(
		"""
		update `tabVC Turnover Checklist`
		set workflow_state = 'For Acceptance'
		where docstatus = 1
			and (workflow_state is null or workflow_state = '' or workflow_state = 'Draft')
		"""
	)
	frappe.db.sql(
		"""
		update `tabVC Turnover Checklist`
		set workflow_state = 'Draft'
		where docstatus = 0
			and (workflow_state is null or workflow_state = '')
		"""
	)
	frappe.db.sql(
		"""
		update `tabVC Turnover Checklist`
		set workflow_state = 'Rejected'
		where docstatus = 2
			and workflow_state != 'Rejected'
		"""
	)


def _get_state_style(state):
	if state == "Accepted":
		return "Success"
	if state == "For Acceptance":
		return "Primary"
	if state == "Rejected":
		return "Danger"
	return "Secondary"
