# Copyright (c) 2026, Rabie Santillan and Eric Mendoza and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.naming import make_autoname
from frappe.utils import getdate, now_datetime, today

from pawnshop_management.pawnshop_management.doctype.pawnshop_transaction_log.pawnshop_transaction_log import (
	get_branch_code,
)


ROLE_TO_BRANCH_FIELD = {
	"Pawnshop Cashier": "pawnshop_cashier",
	"Foreign Exchange Cashier": "fx_cashier",
	"Remittance Cashier": "remittance_cashier",
}

MANAGER_ROLES = {"Operations Manager", "Supervisor"}


class BranchRoleAssignment(Document):
	def autoname(self):
		branch_code = get_branch_code(self.branch)
		if branch_code:
			self.name = make_autoname(f"BRA{branch_code}-.######")
			return

		self.name = make_autoname("BRA-.######")

	def before_insert(self):
		self.validate_create_permission()

		if not self.assigned_by:
			self.assigned_by = frappe.session.user

		if not self.branch:
			self.branch = get_branch_from_request_ip()

		if not self.date:
			self.date = today()

	def validate(self):
		self.validate_operational_role()
		self.validate_acceptance()
		self.validate_edit_permission()

	def before_submit(self):
		if self.workflow_state != "Completed":
			frappe.throw(_("Use the Accept Role workflow action to complete this assignment."))

		self.validate_acceptance()

	def on_submit(self):
		if self.workflow_state == "Completed":
			self.update_branch_cashier()

	def validate_operational_role(self):
		if self.operational_role not in ROLE_TO_BRANCH_FIELD:
			frappe.throw(_("Invalid operational role. Vault Custodian is not allowed here."))

	def validate_acceptance(self):
		if self.workflow_state != "Completed":
			return

		if frappe.session.user != self.assigned_user:
			frappe.throw(_("Only the assigned user can accept this role."), frappe.PermissionError)

		if getdate(self.date) != getdate(today()):
			frappe.throw(_("This role can only be accepted on the assignment date."))

		if not self.accepted_by:
			self.accepted_by = frappe.session.user

		if not self.accepted_datetime:
			self.accepted_datetime = now_datetime()

		if not (self.accepted_by and self.accepted_datetime):
			frappe.throw(_("Accepted By and Accepted Date and Time are required before completion."))

	def validate_create_permission(self):
		if not _user_has_any_role(frappe.session.user, MANAGER_ROLES):
			frappe.throw(
				_("Only users with Supervisor or Operations Manager role can create Branch Role Assignment documents."),
				frappe.PermissionError,
			)

	def validate_edit_permission(self):
		if self.is_new():
			return

		if _is_system_manager(frappe.session.user):
			return

		if self.flags.in_submit or getattr(self, "_action", None) == "submit":
			return

		if self._is_rejection_transition():
			return

		frappe.throw(_("Branch Role Assignment documents are read-only after creation."), frappe.PermissionError)

	def _is_rejection_transition(self):
		if not self._can_reject_assignment(frappe.session.user):
			return False

		previous_doc = self.get_doc_before_save()
		if not previous_doc:
			return False

		if previous_doc.workflow_state != "For Acceptance" or self.workflow_state != "Rejected":
			return False

		allowed_changes = {"workflow_state", "modified", "modified_by"}
		for field in self.meta.fields:
			fieldname = field.fieldname
			if not fieldname or fieldname in allowed_changes:
				continue
			if self.get(fieldname) != previous_doc.get(fieldname):
				return False

		return True

	def _can_reject_assignment(self, user):
		if self.docstatus != 0 or self.workflow_state != "For Acceptance":
			return False

		if user in {self.owner, self.assigned_by}:
			return True

		return _user_has_any_role(user, MANAGER_ROLES)

	def update_branch_cashier(self):
		branch_field = ROLE_TO_BRANCH_FIELD[self.operational_role]
		frappe.db.set_value("Branch", self.branch, branch_field, self.assigned_user)
		frappe.clear_cache(doctype="Branch")


def get_branch_from_request_ip():
	current_ip = getattr(frappe.local, "request_ip", None)
	if not current_ip:
		return None

	branch = frappe.db.get_value(
		"Branch IP Addressing",
		{"ip_address": current_ip},
		["name", "branch"],
		as_dict=True,
	)

	if not branch:
		return None

	return branch.name or branch.branch


def clear_branch_cashier_assignments():
	values = {fieldname: None for fieldname in ROLE_TO_BRANCH_FIELD.values()}

	for branch in frappe.get_all("Branch", pluck="name"):
		frappe.db.set_value("Branch", branch, values, update_modified=False)

	frappe.clear_cache(doctype="Branch")


def get_permission_query_conditions(user=None):
	user = user or frappe.session.user

	if _is_system_manager(user) or _user_has_any_role(user, MANAGER_ROLES):
		return None

	escaped_user = frappe.db.escape(user)
	return (
		f"(`tabBranch Role Assignment`.`assigned_user` = {escaped_user} "
		f"or `tabBranch Role Assignment`.`assigned_by` = {escaped_user} "
		f"or `tabBranch Role Assignment`.`owner` = {escaped_user})"
	)


def has_permission(doc, ptype=None, user=None):
	user = user or frappe.session.user
	permission_type = ptype or "read"

	if permission_type == "create":
		return _user_has_any_role(user, MANAGER_ROLES)

	if permission_type == "write":
		return (
			_is_system_manager(user)
			or doc._can_reject_assignment(user)
			or (
				doc.workflow_state == "Completed" and user == doc.assigned_user
			)
		)

	if permission_type in {"cancel", "delete"}:
		return _is_system_manager(user)

	if permission_type == "submit":
		return doc.workflow_state == "Completed" and user == doc.assigned_user

	if _is_system_manager(user):
		return True

	if permission_type == "read":
		if _user_has_any_role(user, MANAGER_ROLES):
			return True
		return user in {doc.assigned_user, doc.assigned_by, doc.owner}

	return None


def _user_has_any_role(user, roles):
	return bool(set(frappe.get_roles(user)).intersection(roles))


def _is_system_manager(user):
	return user == "Administrator" or _user_has_any_role(user, {"System Manager"})
