import json

import frappe
from frappe import _
from frappe.utils import getdate, today


TEMPORARY_ROLE_ALIASES = {
	"FX Cashier": "Foreign Exchange Cashier",
	"Vault Custodian": "Vault Custodian",
	"Pawnshop Cashier": "Pawnshop Cashier",
	"Foreign Exchange Cashier": "Foreign Exchange Cashier",
	"Remittance Cashier": "Remittance Cashier",
}

BRANCH_FILTER_ROLE_PROFILES = {
	"Cashier",
	"Operations Supervisor/Cashier",
	"Appraiser/Cashier",
	"Senior Appraiser",
	"Junior Appraiser",
	"Appraiser",
	"Operations Supervisor",
	"Vault Custodian",
}

BRANCH_BY_IP_KEY = {
	"cavite_city": "Garcia''s Pawnshop - CC",
	"poblacion": "Garcia''s Pawnshop - POB",
	"molino": "Garcia''s Pawnshop - MOL",
	"gtc": "Garcia''s Pawnshop - GTC",
	"tanza": "Garcia''s Pawnshop - TNZ",
	"alapan": "Garcia''s Pawnshop - BUC",
	"noveleta": "Garcia''s Pawnshop - NOV",
	"pascam": "Garcia''s Pawnshop - PSC",
	"test": "TEST",
}


def normalize_branch_role(role):
	return TEMPORARY_ROLE_ALIASES.get(role, role)


def has_active_branch_role(user, branch, role):
	"""Return True when user currently holds the operational role for the branch."""
	user = user or frappe.session.user
	branch = normalize_branch(branch)
	role = normalize_branch_role(role)

	if not (user and branch and role):
		return False

	if role == "Vault Custodian":
		return get_registered_vault_custodian(branch) == user

	assignment = get_active_branch_role_assignment(branch, role)
	return bool(assignment and assignment.assigned_user == user)


def get_active_branch_role_assignment(branch, role):
	branch = normalize_branch(branch)
	role = normalize_branch_role(role)

	if not (branch and role):
		return None

	assignments = frappe.get_all(
		"Branch Role Assignment",
		filters={
			"branch": branch,
			"operational_role": role,
			"docstatus": 1,
			"workflow_state": "Completed",
			"date": ["<=", getdate(today())],
		},
		fields=["name", "assigned_user", "branch", "operational_role", "date"],
		order_by="date desc, accepted_datetime desc, modified desc",
		limit=1,
	)
	return assignments[0] if assignments else None


def get_active_branch_role_user(branch, role):
	branch = normalize_branch(branch)
	role = normalize_branch_role(role)

	if role == "Vault Custodian":
		return get_registered_vault_custodian(branch)

	assignment = get_active_branch_role_assignment(branch, role)
	return assignment.assigned_user if assignment else None


def get_registered_vault_custodian(branch):
	branch = normalize_branch(branch)
	if not branch:
		return None

	return frappe.db.get_value("Branch", branch, "vault_custodian")


def require_active_branch_role(user, branch, role):
	if is_system_manager(user):
		return

	if has_active_branch_role(user, branch, role):
		return

	frappe.throw(
		_("You are not the active {0} for branch {1}.").format(normalize_branch_role(role), branch or _("Unknown")),
		frappe.PermissionError,
	)


def normalize_branch(branch):
	if isinstance(branch, (list, tuple)):
		return branch[0] if branch else None

	if isinstance(branch, str):
		return branch.strip() or None

	return branch


def get_branch_from_request_ip():
	current_ip = getattr(frappe.local, "request_ip", None)
	if not current_ip:
		return None

	return frappe.db.get_value("Branch IP Addressing", {"ip_address": current_ip}, "name")


def user_has_any_role(user, roles):
	return bool(set(frappe.get_roles(user)).intersection(roles))


def is_system_manager(user):
	return user == "Administrator" or user_has_any_role(user, {"System Manager"})


def has_branch_filter_role_profile(user):
	role_profile_name = frappe.db.get_value("User", user or frappe.session.user, "role_profile_name")
	return role_profile_name in BRANCH_FILTER_ROLE_PROFILES


def get_branch_filter_condition(doctype, user=None, branch_field="branch"):
	user = user or frappe.session.user
	if not has_branch_filter_role_profile(user):
		return None

	branch = get_branch_from_legacy_ip_settings()
	if not branch:
		return None

	return f"(`tab{doctype}`.{branch_field} = '{branch}')"


def get_branch_from_legacy_ip_settings():
	from pawnshop_management.pawnshop_management.custom_codes.get_ip import get_ip_from_settings

	current_ip = getattr(frappe.local, "request_ip", None)
	if not current_ip:
		return None

	branch_ip = get_ip_from_settings()
	for ip_key, branch in BRANCH_BY_IP_KEY.items():
		if str(current_ip) == str(branch_ip.get(ip_key)):
			return branch

	return None


def form_filter_has_value(fieldname):
	filters = frappe.form_dict.get("filters")
	if not filters:
		return False

	try:
		filters = json.loads(filters)
	except json.JSONDecodeError:
		return False

	if not isinstance(filters, list):
		return False

	for filter_item in filters:
		if isinstance(filter_item, list) and len(filter_item) > 3:
			key, value = filter_item[1], filter_item[3]
			if key == fieldname and value:
				return True

	return False


@frappe.whitelist()
def get_active_branch_roles(branch=None):
	matches_branch_filter_role_profile = has_branch_filter_role_profile(frappe.session.user)

	if is_system_manager(frappe.session.user):
		active_roles = {role: True for role in TEMPORARY_ROLE_ALIASES}
		active_roles["matches_branch_filter_role_profile"] = matches_branch_filter_role_profile
		return active_roles

	branch = normalize_branch(branch) or get_branch_from_request_ip()
	if not branch:
		return {"matches_branch_filter_role_profile": matches_branch_filter_role_profile}

	active_roles = {}
	for role in TEMPORARY_ROLE_ALIASES:
		normalized_role = normalize_branch_role(role)
		active_roles[role] = has_active_branch_role(frappe.session.user, branch, normalized_role)

	active_roles["matches_branch_filter_role_profile"] = matches_branch_filter_role_profile
	return active_roles
