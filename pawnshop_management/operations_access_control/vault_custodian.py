import frappe

from pawnshop_management.operations_access_control.access_control import (
	get_branch_from_request_ip,
	normalize_branch,
	require_active_branch_role,
)


VAULT_CUSTODIAN_ROLE = "Vault Custodian"


def require_vault_custodian_access(filters=None, branch=None):
	branch = normalize_branch(branch) or _get_filter_branch(filters) or get_branch_from_request_ip()
	require_active_branch_role(frappe.session.user, branch, VAULT_CUSTODIAN_ROLE)
	return branch


def _get_filter_branch(filters):
	if not filters:
		return None

	if isinstance(filters, dict):
		return normalize_branch(filters.get("branch"))

	return normalize_branch(getattr(filters, "branch", None))
