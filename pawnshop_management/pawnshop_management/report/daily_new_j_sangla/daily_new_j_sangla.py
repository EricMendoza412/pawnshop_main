import frappe
from frappe import _

from pawnshop_management.operations_access_control.vault_custodian import require_vault_custodian_access


def execute(filters=None):
	branch = require_vault_custodian_access(filters)
	columns = [
		{
			"fieldname": "old_pawn_ticket",
			"label": _("Old Pawn Ticket"),
			"fieldtype": "Data",
			"width": 180,
		},
	]
	data = frappe.db.sql(
		"""
		SELECT old_pawn_ticket
		FROM `tabPawn Ticket Jewelry`
		WHERE docstatus = 1
		AND old_pawn_ticket IS NOT NULL
		AND date_loan_granted = CURDATE()
		AND branch = %s
		""",
		(branch,),
		as_dict=True,
	)
	return columns, data
