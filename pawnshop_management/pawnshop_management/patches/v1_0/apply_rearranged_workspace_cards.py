import frappe

from pawnshop_management.pawnshop_management.patches.v1_0.sync_vault_custodian_reports_workspace import (
	sync_main_workspace,
	sync_vc_workspace,
)


def execute():
	"""Apply the current canonical card layout to the two standard workspaces."""
	sync_main_workspace()
	sync_vc_workspace()
	frappe.clear_cache()
