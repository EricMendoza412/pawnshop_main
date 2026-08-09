# Copyright (c) 2026, Rabie Santillan and Eric Mendoza and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.naming import make_autoname
from frappe.utils import flt, getdate, now_datetime, today
from frappe.utils.password import check_password

from pawnshop_management.operations_access_control.access_control import is_system_manager
TRANSFER_RULES = {
	"Vault to Pawnshop (-NCB)": {
		"currencies": {"PHP"},
		"source": "Vault",
		"destination": "Pawnshop Cashier",
		"impact": -1,
		"authorizer_field": "pawnshop_cashier",
		"legacy_field": "vc_to_ps_cashier",
	},
	"Pawnshop (-NCB) to Vault": {
		"currencies": {"PHP"},
		"source": "Pawnshop Cashier",
		"destination": "Vault",
		"impact": 1,
		"authorizer_field": "pawnshop_cashier",
		"legacy_field": "ps_cashier_to_vc",
	},
	"Vault to Remittance": {
		"currencies": {"PHP", "USD"},
		"source": "Vault",
		"destination": "Remittance Cashier",
		"impact": -1,
		"authorizer_field": "remittance_cashier",
		"legacy_field": "vc_to_wu_cashier",
	},
	"Remittance to Vault": {
		"currencies": {"PHP", "USD"},
		"source": "Remittance Cashier",
		"destination": "Vault",
		"impact": 1,
		"authorizer_field": "remittance_cashier",
		"legacy_field": "wu_cashier_to_vc",
	},
	"Vault to ForEx": {
		"currencies": {"PHP"},
		"source": "Vault",
		"destination": "ForEx Cashier",
		"impact": -1,
		"authorizer_field": "fx_cashier",
		"legacy_field": "vc_to_fx_cashier",
	},
	"ForEx to Vault": {
		"currencies": {"PHP", "USD"},
		"source": "ForEx Cashier",
		"destination": "Vault",
		"impact": 1,
		"authorizer_field": "fx_cashier",
		"legacy_field": "fx_cashier_to_vc",
	},
	"Armored Van to Vault": {
		"currencies": {"PHP", "USD"},
		"source": "Armored Van",
		"destination": "Vault",
		"impact": 1,
		"authorization": "none",
	},
	"Rover to Vault": {
		"currencies": {"PHP", "USD"},
		"source": "Rover",
		"destination": "Vault",
		"impact": 1,
		"authorization": "rover",
	},
	"Vault to Cash Manager": {
		"currencies": {"PHP", "USD"},
		"source": "Vault",
		"destination": "Cash Manager",
		"impact": -1,
		"authorization": "rover",
		"legacy_field": "vc_to_cm",
	},
	"Cash Manager to Vault": {
		"currencies": {"PHP", "USD"},
		"source": "Cash Manager",
		"destination": "Vault",
		"impact": 1,
		"authorization": "rover",
		"legacy_field": "cm_to_vc",
	},
	"Cash Position Adjustment": {
		"currencies": {"PHP", "USD"},
		"source": "Cash Position Reconciliation",
		"destination": "Vault",
		"authorization": "system",
	},
}

READ_PERMISSION_TYPES = {"read", "report", "print", "email", "export"}
BRANCH_PARTICIPANT_FIELDS = ("vault_custodian", "pawnshop_cashier", "fx_cashier", "remittance_cashier")


class FundTransfer(Document):
	def autoname(self):
		branch_code = get_fund_transfer_branch_code(self.branch)
		prefix = _safe_series_prefix(branch_code or self.branch or "FT")
		self.name = make_autoname("{0}-.######".format(prefix))
		self.fund_transfer_series = self.name

	def before_insert(self):
		if not self.business_date:
			self.business_date = today()
		if not self.initiated_by:
			self.initiated_by = frappe.session.user
		if not self.status:
			self.status = "Draft"
		if not self.source_system:
			self.source_system = "ERPNext"

	def validate(self):
		self._validate_immutable_submitted_document()
		self._validate_pending_transfer_definition()
		rule = get_transfer_rule(self.transfer_type)
		self._validate_rule(rule)
		self._set_derived_fields(rule)
		self._validate_pending_authorizer(rule)

		if self.is_new() and self.transfer_type != "Cash Position Adjustment":
			require_branch_vault_custodian(self.branch)

		if self.transfer_type == "Cash Position Adjustment" and not self.flags.system_adjustment:
			frappe.throw(_("Cash Position Adjustments can only be created by the reconciliation process."))

	def _validate_pending_authorizer(self, rule):
		if self.status != "Pending Cashier Approval":
			return
		if self.expected_authorizer:
			return

		role_label = {
			"pawnshop_cashier": _("Pawnshop Cashier"),
			"fx_cashier": _("Foreign Exchange Cashier"),
			"remittance_cashier": _("Remittance Cashier"),
		}.get(rule.get("authorizer_field"), _("cashier"))
		frappe.throw(
			_("No {0} is assigned to branch {1}. Assign one before submitting this Fund Transfer.").format(
				role_label, frappe.bold(self.branch)
			)
		)

	def before_submit(self):
		self._authorize_workflow_submission()
		self._validate_authorization()
		self.date_of_transfer = now_datetime()
		self.business_date = getdate(self.date_of_transfer)
		_lock_branch(self.branch)

		if self.currency == "USD" and self.transfer_type == "ForEx to Vault":
			self._validate_usd_availability()

		opening_balance = get_latest_civ_balance(self.branch, self.currency, lock=False)
		change = self._get_balance_change()
		closing_balance = flt(opening_balance) + flt(change)
		if closing_balance < 0:
			frappe.throw(
				_("Insufficient {0} Cash In Vault balance. Available balance is {1}.").format(
					self.currency, frappe.format_value(opening_balance, {"fieldtype": "Currency"})
				)
			)

		self.opening_civ_balance = opening_balance
		self.vault_balance_change = change
		self.civ_balance = closing_balance
		self.status = "Submitted"
		self._set_legacy_values()

	def _authorize_workflow_submission(self):
		# Legacy service methods still perform their own participant/password checks
		# before setting this flag. Native workflow submissions are authorized below.
		if self.flags.system_adjustment or (self.flags.authorized_submission and self.authorized_by):
			return

		previous_status = frappe.db.get_value("Fund Transfer", self.name, "status") or "Draft"
		rule = get_transfer_rule(self.transfer_type)
		authorization = rule.get("authorization", "cashier")

		if previous_status == "Draft" and authorization == "none":
			require_branch_vault_custodian(self.branch)
			self.authorized_by = frappe.session.user
		elif previous_status == "Pending Cashier Approval" and authorization == "cashier":
			expected = get_expected_authorizer(self.branch, rule)
			if frappe.session.user != expected:
				frappe.throw(_("Only the currently assigned cashier can approve this transfer."), frappe.PermissionError)
			self.expected_authorizer = expected
			self.authorized_by = frappe.session.user
		elif previous_status in {"Draft", "Pending Rover Confirmation"} and authorization == "rover":
			require_branch_vault_custodian(self.branch)
			self._verify_rover_password()
		else:
			frappe.throw(_("Use the available workflow action to submit this Fund Transfer."))

		self.authorization_datetime = now_datetime()

	def _verify_rover_password(self):
		rover = self.rover
		password = self.rover_password
		if not rover or not frappe.db.get_value("User", rover, "enabled") or "Rover" not in frappe.get_roles(rover):
			frappe.throw(_("Select an enabled User with the Rover role."), frappe.PermissionError)
		if rover == self.initiated_by:
			frappe.throw(_("The initiating Vault Custodian cannot authorize as Rover."), frappe.PermissionError)
		if not password:
			frappe.throw(_("The Rover password is required."), frappe.AuthenticationError)

		rate_limit_key = _rover_rate_limit_key(rover)
		if int(frappe.cache().get_value(rate_limit_key) or 0) >= 5:
			frappe.throw(
				_("Rover authorization is temporarily locked after repeated failed attempts. Try again in five minutes."),
				frappe.AuthenticationError,
			)
		try:
			check_password(rover, password)
		except frappe.AuthenticationError:
			attempts = int(frappe.cache().get_value(rate_limit_key) or 0) + 1
			frappe.cache().set_value(rate_limit_key, attempts, expires_in_sec=300)
			raise
		frappe.cache().delete_value(rate_limit_key)
		self.authorized_by = rover
		self.rover_password = None

	def on_submit(self):
		from pawnshop_management.pawnshop_management.fund_transfer_google import queue_google_uat_sync

		queue_google_uat_sync(self.name)

	def before_cancel(self):
		if not is_system_manager(frappe.session.user):
			frappe.throw(_("Submitted Fund Transfers cannot be cancelled or reversed."))

	def on_trash(self):
		if (self.docstatus == 1 or self.status == "Submitted") and not is_system_manager(frappe.session.user):
			frappe.throw(_("Submitted Fund Transfers cannot be deleted."))

	def _validate_rule(self, rule):
		if self.currency not in rule["currencies"]:
			frappe.throw(
				_("{0} is not allowed for transfer type {1}.").format(self.currency or _("No currency"), self.transfer_type)
			)
		if flt(self.amount) <= 0:
			frappe.throw(_("Transfer amount must be greater than zero."))
		if self.business_date and getdate(self.business_date) != getdate(today()) and not (
			is_system_manager(frappe.session.user) or self.flags.system_adjustment
		):
			frappe.throw(_("Fund Transfers cannot be backdated."))

	def _set_derived_fields(self, rule):
		if self.transfer_type == "Cash Position Adjustment":
			if flt(self.vault_balance_change) < 0:
				self.source = "Vault"
				self.destination = "Cash Position Reconciliation"
			else:
				self.source = "Cash Position Reconciliation"
				self.destination = "Vault"
		else:
			self.source = rule["source"]
			self.destination = rule["destination"]
		if self.transfer_type != "Cash Position Adjustment":
			self.expected_authorizer = get_expected_authorizer(self.branch, rule)
		if self.transfer_type == "Armored Van to Vault" and not self.external_party:
			self.external_party = "Armored Van"

	def _validate_authorization(self):
		rule = get_transfer_rule(self.transfer_type)
		authorization = rule.get("authorization", "cashier")
		if authorization == "cashier":
			expected = get_expected_authorizer(self.branch, rule)
			if not expected or self.authorized_by != expected:
				frappe.throw(_("The currently assigned cashier must authorize this transfer."), frappe.PermissionError)
		elif authorization == "rover":
			if not self.rover or self.authorized_by != self.rover or "Rover" not in frappe.get_roles(self.rover):
				frappe.throw(_("A valid Rover confirmation is required."), frappe.PermissionError)
		elif authorization == "none":
			require_branch_vault_custodian(self.branch)
		elif authorization == "system":
			if not self.flags.system_adjustment:
				frappe.throw(_("Invalid system adjustment authorization."), frappe.PermissionError)

	def _get_balance_change(self):
		if self.transfer_type == "Cash Position Adjustment":
			return flt(self.vault_balance_change)
		rule = get_transfer_rule(self.transfer_type)
		return flt(self.amount) * rule["impact"]

	def _validate_usd_availability(self):
		from pawnshop_management.pawnshop_management.fund_transfer_google import get_usd_availability

		availability = get_usd_availability(self.branch, self.business_date, exclude_transfer=self.name)
		self.purchased_usd = availability.purchased_usd
		self.previously_transferred_usd = availability.transferred_usd
		self.remaining_usd = flt(availability.available_usd) - flt(self.amount)
		if self.remaining_usd < 0:
			frappe.throw(
				_("Insufficient purchased USD volume. Remaining available USD is {0}.").format(
					frappe.format_value(availability.available_usd, {"fieldtype": "Currency"})
				)
			)

	def _set_legacy_values(self):
		for fieldname in (
			"vc_to_cm",
			"cm_to_vc",
			"vc_to_wu_cashier",
			"wu_cashier_to_vc",
			"vc_to_fx_cashier",
			"fx_cashier_to_vc",
			"vc_to_ps_cashier",
			"ps_cashier_to_vc",
		):
			self.set(fieldname, 0)
		legacy_field = get_transfer_rule(self.transfer_type).get("legacy_field")
		if legacy_field:
			self.set(legacy_field, self.amount)

		self.given_by = _given_by(self)
		self.received_by = _received_by(self)

	def _validate_immutable_submitted_document(self):
		if self.is_new():
			return
		previous = self.get_doc_before_save()
		if not previous or previous.docstatus != 1:
			return
		allowed = {
			"google_sync_status",
			"google_sync_datetime",
			"google_sync_attempts",
			"google_sync_error",
			"accounting_status",
			"journal_entry",
			"modified",
			"modified_by",
		}
		for field in self.meta.fields:
			if field.fieldname and field.fieldname not in allowed and self.get(field.fieldname) != previous.get(field.fieldname):
				frappe.throw(_("Submitted Fund Transfers are immutable."))

	def _validate_pending_transfer_definition(self):
		if self.is_new():
			return
		previous = self.get_doc_before_save()
		if not previous or previous.status == "Draft":
			return
		protected = {
			"branch",
			"business_date",
			"currency",
			"transfer_type",
			"amount",
			"initiated_by",
			"source_system",
			"legacy_transfer_id",
			"external_party",
		}
		if any(not _same_protected_value(self, previous, fieldname) for fieldname in protected):
			frappe.throw(_("Transfer details cannot be changed after authorization has been requested."))


def get_transfer_rule(transfer_type):
	rule = TRANSFER_RULES.get(transfer_type)
	if not rule:
		frappe.throw(_("Invalid Fund Transfer type."))
	return rule


def get_fund_transfer_branch_code(branch):
	if not branch:
		return None
	if frappe.get_meta("Branch").has_field("branch_code"):
		branch_code = frappe.db.get_value("Branch", branch, "branch_code")
		if branch_code:
			return str(branch_code).strip().upper()
	if " - " in branch:
		return branch.rsplit(" - ", 1)[-1].strip().upper()
	return str(branch).strip().upper()


def get_expected_authorizer(branch, rule):
	fieldname = rule.get("authorizer_field")
	return frappe.db.get_value("Branch", branch, fieldname) if fieldname else None


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def rover_user_query(doctype, txt, searchfield, start, page_len, filters):
	return frappe.db.sql(
		"""
		select distinct user.name, concat_ws(' ', user.first_name, user.middle_name, user.last_name)
		from `tabUser` user
		inner join `tabHas Role` user_role
			on user_role.parent = user.name
			and user_role.parenttype = 'User'
			and user_role.role = 'Rover'
		where user.enabled = 1
			and user.user_type != 'Website User'
			and user.name not in ('Administrator', 'Guest')
			and (
				user.name like %(txt)s
				or concat_ws(' ', user.first_name, user.middle_name, user.last_name) like %(txt)s
			)
		order by user.name
		limit %(page_len)s offset %(start)s
		""",
		{"txt": "%{0}%".format(txt), "page_len": page_len, "start": start},
	)


def require_branch_vault_custodian(branch, user=None):
	user = user or frappe.session.user
	if is_system_manager(user):
		return
	vault_custodian = frappe.db.get_value("Branch", branch, "vault_custodian")
	if not vault_custodian or vault_custodian != user:
		frappe.throw(_("Only the branch's current Vault Custodian can perform this action."), frappe.PermissionError)


def get_latest_civ_balance(branch, currency, lock=True):
	if lock:
		_lock_branch(branch)
	result = frappe.db.sql(
		"""
		select civ_balance
		from `tabFund Transfer`
		where branch=%s and currency=%s and docstatus=1 and status='Submitted'
		order by date_of_transfer desc, creation desc
		limit 1
		""",
		(branch, currency),
		as_dict=True,
	)
	if result:
		return flt(result[0].civ_balance)

	if frappe.db.exists("DocType", "Vault Cash Position"):
		fieldname = "php_reconciled_ending_balance" if currency == "PHP" else "usd_reconciled_ending_balance"
		opening = frappe.db.get_value(
			"Vault Cash Position",
			{"branch": branch, "docstatus": 1, "is_opening_position": 1},
			fieldname,
			order_by="business_date desc, creation desc",
		)
		if opening is not None:
			return flt(opening)
	return 0


def _lock_branch(branch):
	if not branch:
		frappe.throw(_("Branch is required."))
	frappe.db.sql("select name from `tabBranch` where name=%s for update", branch)


@frappe.whitelist()
def request_approval(name):
	doc = frappe.get_doc("Fund Transfer", name)
	doc.check_permission("write")
	require_branch_vault_custodian(doc.branch)
	if doc.docstatus != 0 or doc.status != "Draft":
		frappe.throw(_("Only a Draft Fund Transfer can be requested."))

	rule = get_transfer_rule(doc.transfer_type)
	authorization = rule.get("authorization", "cashier")
	if authorization == "cashier":
		doc.expected_authorizer = get_expected_authorizer(doc.branch, rule)
		if not doc.expected_authorizer:
			frappe.throw(_("No cashier is currently assigned to this branch for the selected transfer type."))
		doc.status = "Pending Cashier Approval"
		doc.save()
	elif authorization == "rover":
		doc.status = "Pending Rover Confirmation"
		doc.save()
	elif authorization == "none":
		doc.authorized_by = frappe.session.user
		doc.authorization_datetime = now_datetime()
		_submit_authorized(doc)
	else:
		frappe.throw(_("This transfer type cannot be requested manually."))
	return doc.as_dict()


@frappe.whitelist()
def approve_cashier_transfer(name):
	doc = frappe.get_doc("Fund Transfer", name)
	if doc.docstatus != 0 or doc.status != "Pending Cashier Approval":
		frappe.throw(_("This Fund Transfer is not awaiting cashier approval."))
	rule = get_transfer_rule(doc.transfer_type)
	expected = get_expected_authorizer(doc.branch, rule)
	if frappe.session.user != expected:
		frappe.throw(_("Only the currently assigned cashier can approve this transfer."), frappe.PermissionError)
	doc.expected_authorizer = expected
	doc.authorized_by = frappe.session.user
	doc.authorization_datetime = now_datetime()
	_submit_authorized(doc)
	return doc.as_dict()


@frappe.whitelist()
def reject_cashier_transfer(name, reason=None):
	doc = frappe.get_doc("Fund Transfer", name)
	if doc.docstatus != 0 or doc.status != "Pending Cashier Approval":
		frappe.throw(_("This Fund Transfer is not awaiting cashier approval."))
	rule = get_transfer_rule(doc.transfer_type)
	if frappe.session.user != get_expected_authorizer(doc.branch, rule):
		frappe.throw(_("Only the currently assigned cashier can reject this transfer."), frappe.PermissionError)
	doc.status = "Rejected"
	doc.authorized_by = frappe.session.user
	doc.authorization_datetime = now_datetime()
	if reason:
		doc.comments = _append_comment(doc.comments, _("Rejected: {0}").format(reason))
	doc.save(ignore_permissions=True)
	return doc.as_dict()


@frappe.whitelist()
def confirm_rover_transfer(name, rover, password):
	doc = frappe.get_doc("Fund Transfer", name)
	require_branch_vault_custodian(doc.branch)
	if doc.docstatus != 0 or doc.status != "Pending Rover Confirmation":
		frappe.throw(_("This Fund Transfer is not awaiting Rover confirmation."))
	if not rover or not frappe.db.get_value("User", rover, "enabled") or "Rover" not in frappe.get_roles(rover):
		frappe.throw(_("Select an enabled User with the Rover role."), frappe.PermissionError)
	if rover == doc.initiated_by:
		frappe.throw(_("The initiating Vault Custodian cannot authorize as Rover."), frappe.PermissionError)

	rate_limit_key = _rover_rate_limit_key(rover)
	if int(frappe.cache().get_value(rate_limit_key) or 0) >= 5:
		frappe.throw(
			_("Rover authorization is temporarily locked after repeated failed attempts. Try again in five minutes."),
			frappe.AuthenticationError,
		)
	try:
		check_password(rover, password)
	except frappe.AuthenticationError:
		attempts = int(frappe.cache().get_value(rate_limit_key) or 0) + 1
		frappe.cache().set_value(rate_limit_key, attempts, expires_in_sec=300)
		frappe.logger("fund_transfer").warning(
			"Failed Rover authorization: transfer=%s rover=%s ip=%s",
			doc.name,
			rover,
			getattr(frappe.local, "request_ip", None),
		)
		raise
	frappe.cache().delete_value(rate_limit_key)
	doc.rover = rover
	doc.authorized_by = rover
	doc.authorization_datetime = now_datetime()
	_submit_authorized(doc)
	return doc.as_dict()


@frappe.whitelist()
def cancel_pending_transfer(name):
	doc = frappe.get_doc("Fund Transfer", name)
	require_branch_vault_custodian(doc.branch)
	if doc.docstatus != 0 or doc.status not in {"Draft", "Pending Cashier Approval", "Pending Rover Confirmation"}:
		frappe.throw(_("Only a Draft or pending Fund Transfer can be cancelled."))
	doc.status = "Cancelled"
	doc.save(ignore_permissions=True)
	return doc.as_dict()


@frappe.whitelist()
def get_action_context(name):
	doc = frappe.get_doc("Fund Transfer", name)
	doc.check_permission("read")
	user = frappe.session.user
	rule = get_transfer_rule(doc.transfer_type)
	expected = get_expected_authorizer(doc.branch, rule)
	return {
		"is_vault_custodian": is_system_manager(user)
		or frappe.db.get_value("Branch", doc.branch, "vault_custodian") == user,
		"is_expected_cashier": bool(expected and expected == user),
		"is_rover_transfer": rule.get("authorization") == "rover",
	}


def create_cash_position_adjustment(cash_position, currency, variance):
	variance = flt(variance)
	if not variance:
		return None
	doc = frappe.new_doc("Fund Transfer")
	doc.branch = cash_position.branch
	doc.business_date = today()
	doc.currency = currency
	doc.transfer_type = "Cash Position Adjustment"
	doc.amount = abs(variance)
	doc.vault_balance_change = variance
	doc.initiated_by = frappe.session.user
	doc.authorized_by = frappe.session.user
	doc.authorization_datetime = now_datetime()
	doc.source_system = "System Adjustment"
	doc.cash_position = cash_position.name
	doc.comments = _("Cash Position variance adjustment for {0}.").format(cash_position.name)
	doc.flags.system_adjustment = True
	doc.flags.authorized_submission = True
	doc.insert(ignore_permissions=True)
	doc.flags.ignore_permissions = True
	doc.submit()
	return doc.name


def get_permission_query_conditions(user=None):
	user = user or frappe.session.user
	if is_system_manager(user) or "Accounting Analyst" in frappe.get_roles(user):
		return None
	escaped_user = frappe.db.escape(user)
	return (
		"("
		"exists (select `tabBranch`.`name` from `tabBranch` "
		"where `tabBranch`.`name`=`tabFund Transfer`.`branch` and ("
		+ " or ".join(
			"`tabBranch`.`{0}`={1}".format(fieldname, escaped_user) for fieldname in BRANCH_PARTICIPANT_FIELDS
		)
		+ ")) "
		f"or `tabFund Transfer`.`authorized_by`={escaped_user} "
		f"or `tabFund Transfer`.`expected_authorizer`={escaped_user} "
		f"or `tabFund Transfer`.`initiated_by`={escaped_user}"
		")"
	)


def has_permission(doc, ptype=None, user=None):
	user = user or frappe.session.user
	permission_type = ptype or "read"
	if is_system_manager(user):
		return True
	if permission_type in {"cancel", "delete"}:
		return False
	if permission_type == "create":
		return _user_is_any_vault_custodian(user)
	if permission_type in READ_PERMISSION_TYPES:
		return _can_read(doc, user)
	if permission_type == "submit":
		if doc.docstatus == 1:
			return _can_submit_workflow(doc, user)
		return _can_write_pending(doc, user)
	if permission_type == "write":
		if doc.docstatus == 1:
			return _can_submit_workflow(doc, user)
		return _can_write_pending(doc, user)
	return None


def _can_read(doc, user):
	if "Accounting Analyst" in frappe.get_roles(user):
		return True
	if user in {
		getattr(doc, "initiated_by", None),
		getattr(doc, "expected_authorizer", None),
		getattr(doc, "authorized_by", None),
	}:
		return True
	branch_values = frappe.db.get_value("Branch", doc.branch, BRANCH_PARTICIPANT_FIELDS, as_dict=True) or {}
	return user in set(branch_values.values())


def _can_write_pending(doc, user):
	status = doc.status
	if doc.docstatus == 0 and status == "Submitted" and getattr(doc, "name", None):
		status = frappe.db.get_value("Fund Transfer", doc.name, "status") or status
	if (
		frappe.db.get_value("Branch", doc.branch, "vault_custodian") == user
		and status in {"Draft", "Pending Cashier Approval", "Pending Rover Confirmation"}
	):
		return True
	if status == "Pending Cashier Approval":
		return user == get_expected_authorizer(doc.branch, get_transfer_rule(doc.transfer_type))
	return False


def _can_submit_workflow(doc, user):
	"""Authorize only a draft-to-submitted transition that is currently in progress."""
	stored = frappe.db.get_value("Fund Transfer", doc.name, ["docstatus", "status"], as_dict=True)
	if not stored or stored.docstatus != 0:
		return False

	if stored.status == "Pending Cashier Approval":
		return user == doc.expected_authorizer
	if stored.status == "Pending Rover Confirmation":
		return frappe.db.get_value("Branch", doc.branch, "vault_custodian") == user
	if stored.status == "Draft" and get_transfer_rule(doc.transfer_type).get("authorization") in {"none", "rover"}:
		return frappe.db.get_value("Branch", doc.branch, "vault_custodian") == user
	return False


def _user_is_any_vault_custodian(user):
	return bool(frappe.db.exists("Branch", {"vault_custodian": user}))


def _submit_authorized(doc):
	doc.flags.authorized_submission = True
	# Each public action performs its exact participant check before reaching this
	# point. Dynamic Branch assignments cannot be represented by static DocPerm
	# roles, so submission intentionally bypasses only the static role gate.
	doc.flags.ignore_permissions = True
	doc.submit()


def _safe_series_prefix(value):
	import re

	value = str(value or "FT").strip().upper()
	return re.sub(r"[^A-Z0-9]+", "-", value).strip("-") or "FT"


def _given_by(doc):
	if doc.source == "Vault":
		return doc.initiated_by
	if doc.source == "Armored Van":
		return doc.external_party or "Armored Van"
	return doc.authorized_by or doc.source


def _received_by(doc):
	if doc.destination == "Vault":
		return doc.initiated_by
	return doc.authorized_by or doc.destination


def _append_comment(current, addition):
	return "{0}\n{1}".format(current, addition).strip() if current else addition


def _same_protected_value(doc, previous, fieldname):
	"""Treat equivalent browser/DB representations as unchanged."""
	fieldtype = (doc.meta.get_field(fieldname) or {}).get("fieldtype")
	current_value = doc.get(fieldname)
	previous_value = previous.get(fieldname)
	if fieldtype in {"Currency", "Float", "Int", "Check", "Percent"}:
		return flt(current_value) == flt(previous_value)
	if fieldtype == "Date":
		return getdate(current_value) == getdate(previous_value) if current_value or previous_value else True
	return str(current_value or "").strip() == str(previous_value or "").strip()


def _rover_rate_limit_key(rover):
	request_ip = getattr(frappe.local, "request_ip", None) or "unknown"
	return "fund-transfer-rover-auth:{0}:{1}".format(rover, request_ip)
