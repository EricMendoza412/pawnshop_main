import frappe


WORKFLOW_NAME = "Fund Transfer Workflow"
WORKFLOW_STATES = {
	"Draft": "Inverse",
	"Pending Cashier Approval": "Warning",
	"Pending Rover Confirmation": "Warning",
	"Submitted": "Success",
	"Rejected": "Danger",
	"Cancelled": "Danger",
}
WORKFLOW_ACTIONS = ("Submit", "Approve", "Reject", "Confirm with Rover Password", "Cancel Pending Transfer")
CASHIER_TYPES = (
	"Vault to Pawnshop (-NCB)",
	"Pawnshop (-NCB) to Vault",
	"Vault to Remittance",
	"Remittance to Vault",
	"Vault to ForEx",
	"ForEx to Vault",
)
ROVER_TYPES = ("Rover to Vault", "Vault to Cash Manager", "Cash Manager to Vault")


def execute():
	frappe.reload_doc("pawnshop_management", "doctype", "fund_transfer")
	ensure_workflow_states()
	ensure_workflow_actions()
	ensure_workflow()


def ensure_workflow_states():
	for state, style in WORKFLOW_STATES.items():
		if not frappe.db.exists("Workflow State", state):
			frappe.get_doc(
				{"doctype": "Workflow State", "workflow_state_name": state, "style": style}
			).insert(ignore_permissions=True)


def ensure_workflow_actions():
	for action in WORKFLOW_ACTIONS:
		if not frappe.db.exists("Workflow Action Master", action):
			frappe.get_doc(
				{"doctype": "Workflow Action Master", "workflow_action_name": action}
			).insert(ignore_permissions=True)


def ensure_workflow():
	workflow = frappe.get_doc("Workflow", WORKFLOW_NAME) if frappe.db.exists("Workflow", WORKFLOW_NAME) else frappe.new_doc("Workflow")
	workflow.workflow_name = WORKFLOW_NAME
	workflow.document_type = "Fund Transfer"
	workflow.is_active = 1
	workflow.override_status = 0
	workflow.send_email_alert = 0
	workflow.workflow_state_field = "status"
	workflow.set(
		"states",
		[
			{"state": "Draft", "doc_status": "0", "allow_edit": "All"},
			{"state": "Pending Cashier Approval", "doc_status": "0", "allow_edit": "All"},
			{"state": "Pending Rover Confirmation", "doc_status": "0", "allow_edit": "All"},
			{"state": "Submitted", "doc_status": "1", "allow_edit": "System Manager"},
			{"state": "Rejected", "doc_status": "0", "allow_edit": "System Manager"},
			{"state": "Cancelled", "doc_status": "0", "allow_edit": "System Manager"},
		],
	)
	workflow.set(
		"transitions",
		[
			transition("Draft", "Submit", "Pending Cashier Approval", f"doc.transfer_type in {CASHIER_TYPES!r}"),
			transition("Draft", "Submit", "Submitted", f"doc.transfer_type in {ROVER_TYPES!r}"),
			transition("Draft", "Submit", "Submitted", "doc.transfer_type == 'Armored Van to Vault'"),
			transition("Pending Cashier Approval", "Approve", "Submitted", "doc.expected_authorizer == frappe.session.user"),
			transition("Pending Cashier Approval", "Reject", "Rejected", "doc.expected_authorizer == frappe.session.user"),
			transition("Pending Cashier Approval", "Cancel Pending Transfer", "Cancelled", vault_custodian_condition()),
			transition("Pending Rover Confirmation", "Confirm with Rover Password", "Submitted", vault_custodian_condition()),
			transition("Pending Rover Confirmation", "Cancel Pending Transfer", "Cancelled", vault_custodian_condition()),
		],
	)
	workflow.save(ignore_permissions=True)
	frappe.clear_cache(doctype="Fund Transfer")


def transition(state, action, next_state, condition):
	return {
		"state": state,
		"action": action,
		"next_state": next_state,
		"allowed": "All",
		"allow_self_approval": 1,
		"condition": condition,
	}


def vault_custodian_condition():
	return "frappe.db.get_value('Branch', doc.branch, 'vault_custodian') == frappe.session.user"
