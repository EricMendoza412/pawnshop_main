import frappe

from pawnshop_management.pawnshop_management.patches.v1_0.sync_vault_custodian_reports_workspace import (
	sync_main_workspace,
	sync_vc_workspace,
)


def execute():
	sync_main_workspace()
	# Patches run before new DocTypes are synchronized. The standard Workspace JSON
	# will add these links later in the same migrate; only force the VC sync when all
	# link targets already exist (upgrades after the first installation).
	if frappe.db.exists("DocType", "Vault Cash Position"):
		sync_vc_workspace()
	for workspace_name in ("Foreign Exchange", "Remittance"):
		if frappe.db.exists("Workspace", workspace_name):
			workspace = frappe.get_doc("Workspace", workspace_name)
			workspace.disable_user_customization = 1
			workspace.icon = "star"
			workspace.module = "Pawnshop Management"
			workspace.category = "Modules"
			workspace.save(ignore_permissions=True)
	frappe.clear_cache()
