"""Install direct participant confirmation without rewriting historical transfers."""

import frappe

from pawnshop_management.pawnshop_management.patches.v1_0.create_fund_transfer_workflow import (
	ensure_workflow,
	ensure_workflow_actions,
	ensure_workflow_states,
)


ABANDONED_STATES = ("Draft", "Pending Cashier Approval", "Pending Rover Confirmation")


def execute():
	frappe.reload_doc("pawnshop_management", "doctype", "fund_transfer", force=True)
	ensure_workflow_states()
	ensure_workflow_actions()
	ensure_workflow()


def cleanup_abandoned_transfers(delete=False, expected_names=None):
	"""Explicit maintenance operation; never delete transactions during app migration.

	Call as Administrator after reviewing the returned inventory. Normal Frappe
	link checks and Deleted Document archives remain in effect. The caller owns
	the transaction, so a linked record aborts the entire cleanup.
	"""
	if frappe.session.user != "Administrator":
		frappe.throw("Only Administrator can clean up abandoned transfers.", frappe.PermissionError)
	rows = frappe.get_all(
		"Fund Transfer",
		filters={"docstatus": 0, "status": ["in", ABANDONED_STATES]},
		fields=["name", "branch", "transfer_type", "status", "fx_selling", "cash_position"],
		order_by="name",
	)
	if delete:
		if expected_names is None or set(expected_names) != {row.name for row in rows}:
			frappe.throw("Review the current cleanup inventory before deleting Fund Transfers.")
		for row in rows:
			doc = frappe.get_doc("Fund Transfer", row.name, for_update=True)
			if doc.docstatus != 0 or doc.status not in ABANDONED_STATES:
				frappe.throw("Fund Transfer changed during cleanup: " + doc.name)
			if doc.fx_selling or doc.cash_position:
				frappe.throw("Review linked transaction before cleanup: " + doc.name)
			frappe.delete_doc("Fund Transfer", doc.name)
	return rows
