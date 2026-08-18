"""Load the FX DocTypes, then synchronize the workspace during migrate."""

import frappe

from pawnshop_management.pawnshop_management.patches.v1_0.sync_fx_selling_workspace import (
	execute as sync_workspace,
)


def execute():
	# Frappe v13 runs even final patches before its general DocType sync. Explicitly
	# load the link targets so this patch also works on a fresh deployment.
	for doctype in ("fx_selling_currency", "fx_selling_settings", "fx_selling"):
		frappe.reload_doc("pawnshop_management", "doctype", doctype)
	sync_workspace()
