import frappe


WORKFLOW_NAME = "Branch Role Assignment Workflow"
WORKFLOW_STATES = ("For Acceptance", "Completed", "Rejected")
WORKFLOW_ACTIONS = ("Accept Role", "Reject")
ASSIGNMENT_IS_TODAY = (
	"frappe.utils.get_datetime(doc.date) <= frappe.utils.now_datetime() "
	"and frappe.utils.add_to_date(frappe.utils.get_datetime(doc.date), days=1) > frappe.utils.now_datetime()"
)


def execute():
	ensure_branch_role_assignment_doctype()
	ensure_workflow_states()
	ensure_workflow_actions()
	ensure_workflow()


def ensure_branch_role_assignment_doctype():
	frappe.reload_doc("operations_access_control", "doctype", "branch_role_assignment")


def ensure_workflow_states():
	for state in WORKFLOW_STATES:
		if frappe.db.exists("Workflow State", state):
			continue

		style = {
			"For Acceptance": "Primary",
			"Completed": "Success",
			"Rejected": "Danger",
		}[state]

		frappe.get_doc(
			{
				"doctype": "Workflow State",
				"workflow_state_name": state,
				"style": style,
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

	workflow.document_type = "Branch Role Assignment"
	workflow.is_active = 1
	workflow.override_status = 0
	workflow.send_email_alert = 0
	workflow.workflow_state_field = "workflow_state"

	workflow.set(
		"states",
		[
			{
				"state": "For Acceptance",
				"doc_status": "0",
				"allow_edit": "System Manager",
			},
			{
				"state": "Completed",
				"doc_status": "1",
				"allow_edit": "System Manager",
			},
			{
				"state": "Rejected",
				"doc_status": "0",
				"allow_edit": "System Manager",
			},
		],
	)
	workflow.set(
		"transitions",
		[
			{
				"state": "For Acceptance",
				"action": "Accept Role",
				"next_state": "Completed",
				"allowed": "All",
				"allow_self_approval": 1,
				"condition": f"doc.assigned_user == frappe.session.user and {ASSIGNMENT_IS_TODAY}",
			},
			{
				"state": "For Acceptance",
				"action": "Reject",
				"next_state": "Rejected",
				"allowed": "All",
				"allow_self_approval": 1,
				"condition": "frappe.session.user in [doc.owner, doc.assigned_by]",
			},
			{
				"state": "For Acceptance",
				"action": "Reject",
				"next_state": "Rejected",
				"allowed": "Operations Manager",
				"allow_self_approval": 1,
			},
			{
				"state": "For Acceptance",
				"action": "Reject",
				"next_state": "Rejected",
				"allowed": "Supervisor",
				"allow_self_approval": 1,
			},
		],
	)

	workflow.save(ignore_permissions=True)
	frappe.clear_cache(doctype="Branch Role Assignment")
