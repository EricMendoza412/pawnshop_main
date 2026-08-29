import frappe

from pawnshop_management.pawnshop_management.doctype.vc_turnover_checklist.vc_turnover_checklist import (
	sync_acceptance_workflow_action,
)


def execute():
	checklists = frappe.get_all(
		"VC Turnover Checklist",
		fields=["name", "docstatus", "workflow_state", "received_by"],
	)

	for checklist in checklists:
		sync_acceptance_workflow_action(checklist)
