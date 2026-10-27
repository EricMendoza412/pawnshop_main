"""Complete the active VCP workflow without changing reconciliation history."""

import frappe


def execute():
	for name in frappe.get_all("Workflow", filters={
		"document_type": "Vault Cash Position", "is_active": 1,
	}, pluck="name"):
		workflow = frappe.get_doc("Workflow", name)
		field = workflow.workflow_state_field
		if not field or not frappe.get_meta("Vault Cash Position").has_field(field):
			frappe.throw("Vault Cash Position workflow state field is missing.")
		cancelled = next((row for row in workflow.states if row.state == "Cancelled"), None)
		if cancelled and str(cancelled.doc_status) != "2":
			frappe.throw("Review the existing Cancelled VCP workflow state before migration.")
		if not frappe.db.exists("Workflow State", "Cancelled"):
			frappe.get_doc({"doctype": "Workflow State", "workflow_state_name": "Cancelled",
				"style": "Danger"}).insert(ignore_permissions=True)
		if not frappe.db.exists("Workflow Action Master", "Cancel"):
			frappe.get_doc({"doctype": "Workflow Action Master", "workflow_action_name": "Cancel"}).insert(ignore_permissions=True)
		changed = False
		if not cancelled:
			workflow.append("states", {"state": "Cancelled", "doc_status": "2", "allow_edit": "System Manager"})
			changed = True
		for state in workflow.states:
			if str(state.doc_status) != "1":
				continue
			if not any(row.state == state.state and row.next_state == "Cancelled"
				and row.allowed == "System Manager" for row in workflow.transitions):
				workflow.append("transitions", {"state": state.state, "action": "Cancel",
					"next_state": "Cancelled", "allowed": "System Manager", "allow_self_approval": 1})
				changed = True
		if changed:
			workflow.save(ignore_permissions=True)
		# The controller synchronizes standard/API cancellation. Repair only
		# records already cancelled, preserving reconciliation and audit fields.
		for row in frappe.get_all("Vault Cash Position", filters={"docstatus": 2}, fields=["name", field]):
			if row.get(field) != "Cancelled":
				frappe.db.set_value("Vault Cash Position", row.name, field, "Cancelled", update_modified=False)
	frappe.clear_cache(doctype="Vault Cash Position")
