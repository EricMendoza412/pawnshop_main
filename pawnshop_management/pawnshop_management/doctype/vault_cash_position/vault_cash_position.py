# Copyright (c) 2026, Rabie Santillan and Eric Mendoza and contributors
# For license information, please see license.txt

import hashlib
import json

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.naming import make_autoname
from frappe.utils import escape_html, flt, getdate, now_datetime, today

from pawnshop_management.operations_access_control.access_control import is_system_manager
from pawnshop_management.pawnshop_management.doctype.fund_transfer.fund_transfer import (
	_lock_branch,
	create_cash_position_adjustment,
	get_fund_transfer_branch_code,
	get_latest_civ_balance,
)


PHP_DENOMINATIONS = (1000, 500, 200, 100, 50, 20, 10, 5, 1, 0.25)
USD_DENOMINATIONS = (100, 50, 20, 10, 5, 2, 1)
READ_ALL_ROLES = {"Accounting Analyst", "Auditor", "Operations Manager", "Settlement Member"}
READ_PERMISSION_TYPES = {"read", "report", "print", "email", "export"}


class VaultCashPosition(Document):
	def before_print(self, settings=None):
		# Existing records may predate the hidden currency field. Set it in memory so
		# standard print formatting always renders the USD summary with a dollar sign.
		self.usd_currency = "USD"
		vault_custodian_name = (
			frappe.db.get_value("User", self.vault_custodian, "full_name") or self.vault_custodian or ""
		)
		self.signature_over_printed_name = _print_signature_line(vault_custodian_name)
		self.managers_spot_check = _print_signature_line()

	def autoname(self):
		branch_code = get_fund_transfer_branch_code(self.branch) or "VCP"
		self.naming_series = "VCP{0}-.YYYY.-.#####".format(branch_code)
		self.name = make_autoname(self.naming_series)

	def before_insert(self):
		self.branch = require_vcp_branch(self.branch)
		if self.get("amended_from"):
			original_branch = frappe.db.get_value("Vault Cash Position", self.amended_from, "branch")
			if self.branch != original_branch:
				frappe.throw(_("An amended Vault Cash Position must retain the original branch."))
		self.business_date = today()
		self.vault_custodian = frappe.session.user
		self.reconciliation_status = "Draft"
		# Amendments can carry the cancelled document's workflow field.
		workflow_name = self.meta.get_workflow()
		if workflow_name:
			workflow = frappe.get_doc("Workflow", workflow_name)
			self.set(workflow.workflow_state_field, workflow.states[0].state)
		self._ensure_denomination_rows()

	def validate(self):
		self.usd_currency = "USD"
		require_vcp_branch(self.branch)
		if self.business_date and getdate(self.business_date) != getdate(today()) and not is_system_manager(
			frappe.session.user
		):
			frappe.throw(_("Vault Cash Positions cannot be backdated."))
		self._ensure_denomination_rows()
		self._calculate_actual_totals()
		self._validate_balance_snapshot()

	def before_submit(self):
		require_vcp_branch(self.branch)
		self._validate_complete_tables()
		_lock_branch(self.branch)
		self._validate_unique_daily_position()
		self.count_datetime = now_datetime()
		self.vault_custodian = frappe.session.user

		# Recheck under the branch lock immediately before closing the day.
		self._validate_balance_snapshot()
		self.php_reconciled_ending_balance = self.php_system_civ_balance
		self.usd_reconciled_ending_balance = self.usd_system_civ_balance

	def _validate_balance_snapshot(self):
		_lock_branch(self.branch)
		snapshot = _balance_snapshot(self.branch)
		if self.get("_vault_balance_snapshot") != snapshot["token"]:
			frappe.throw(_("Vault transactions have changed or balances have not been loaded. Refresh the form and review your cash count before saving or submitting again."))
		self.is_opening_position = snapshot["is_opening_position"]
		for currency in ("php", "usd"):
			self.set(currency + "_latest_fund_transfer", snapshot[currency + "_latest_fund_transfer"])
			actual = flt(self.get(currency + "_actual_cash"))
			balance = actual if self.is_opening_position else snapshot[currency + "_system_civ_balance"]
			self.set(currency + "_system_civ_balance", balance)
			self.set(currency + "_variance", flt(actual - balance, 2))

	def on_submit(self):
		if not flt(self.php_variance) and not flt(self.usd_variance):
			self.db_set(
				{
					"reconciliation_status": "Balanced",
					"php_reconciled_ending_balance": self.php_actual_cash,
					"usd_reconciled_ending_balance": self.usd_actual_cash,
				},
				update_modified=False,
			)
		else:
			self.db_set("reconciliation_status", "Pending Accounting Review", update_modified=False)

	def before_cancel(self):
		_lock_branch(self.branch)
		if not is_system_manager(frappe.session.user):
			frappe.throw(_("Submitted Vault Cash Positions cannot be cancelled."))
		workflow_name = self.meta.get_workflow()
		if workflow_name:
			workflow = frappe.get_doc("Workflow", workflow_name)
			if not any(row.state == "Cancelled" and str(row.doc_status) == "2" for row in workflow.states):
				frappe.throw(_("The Vault Cash Position workflow must include a Cancelled state before cancellation."))
			self.set(workflow.workflow_state_field, "Cancelled")

	def _ensure_denomination_rows(self):
		_ensure_table(self, "php_denominations", PHP_DENOMINATIONS, "PHP")
		_ensure_table(self, "usd_denominations", USD_DENOMINATIONS, "USD")

	def _calculate_actual_totals(self):
		self.php_actual_cash = _calculate_table(self.php_denominations)
		self.usd_actual_cash = _calculate_table(self.usd_denominations)

	def _validate_complete_tables(self):
		_validate_table(self.php_denominations, PHP_DENOMINATIONS, "PHP")
		_validate_table(self.usd_denominations, USD_DENOMINATIONS, "USD")

	def _validate_unique_daily_position(self):
		existing = frappe.db.sql("""
			select name from `tabVault Cash Position`
			where branch=%s and business_date=%s and docstatus != 2 and name != %s
			limit 1 for update
			""", (self.branch, self.business_date, self.name))
		if existing:
			frappe.throw(_("Vault Cash Position {0} already exists for this branch and date.").format(existing[0][0]))



def _print_signature_line(printed_name=""):
	content = escape_html(printed_name) if printed_name else "&nbsp;"
	return (
		'<span style="display:inline-block;min-width:280px;padding:0 28px;'
		'border-bottom:1px solid #000;text-align:center;box-sizing:border-box;">'
		f"{content}</span>"
	)


@frappe.whitelist()
def approve_reconciliation(name, comments=None):
	if not _is_accounting_analyst(frappe.session.user):
		frappe.throw(_("Only an Accounting Analyst can approve cash-position variances."), frappe.PermissionError)

	doc = frappe.get_doc("Vault Cash Position", name)
	if doc.docstatus != 1 or doc.reconciliation_status != "Pending Accounting Review":
		frappe.throw(_("This Vault Cash Position is not pending Accounting review."))

	_lock_branch(doc.branch)
	# Reload the locked position: another reviewer may have reconciled it while
	# this request waited for the branch lock.
	doc = frappe.get_doc("Vault Cash Position", name, for_update=True)
	if doc.docstatus != 1 or doc.reconciliation_status != "Pending Accounting Review":
		frappe.throw(_("This Vault Cash Position is not pending Accounting review."))
	php_adjustment = create_cash_position_adjustment(doc, "PHP", doc.php_variance)
	usd_adjustment = create_cash_position_adjustment(doc, "USD", doc.usd_variance)
	php_balance = get_latest_civ_balance(doc.branch, "PHP", lock=False)
	usd_balance = get_latest_civ_balance(doc.branch, "USD", lock=False)
	frappe.db.set_value(
		"Vault Cash Position",
		doc.name,
		{
			"reconciliation_status": "Reconciled",
			"reconciled_by": frappe.session.user,
			"reconciliation_datetime": now_datetime(),
			"reconciliation_comments": comments,
			"php_adjustment_fund_transfer": php_adjustment,
			"usd_adjustment_fund_transfer": usd_adjustment,
			"php_reconciled_ending_balance": php_balance,
			"usd_reconciled_ending_balance": usd_balance,
		},
		update_modified=True,
	)
	return frappe.get_doc("Vault Cash Position", doc.name).as_dict()


@frappe.whitelist()
def get_action_context(name):
	doc = frappe.get_doc("Vault Cash Position", name)
	doc.check_permission("read")
	return {
		"can_reconcile": _is_accounting_analyst(frappe.session.user)
		and doc.docstatus == 1
		and doc.reconciliation_status == "Pending Accounting Review"
	}


def get_permission_query_conditions(user=None):
	user = user or frappe.session.user
	if is_system_manager(user) or _has_read_all_role(user):
		return None
	escaped_user = frappe.db.escape(user)
	return (
		"exists (select `tabBranch`.`name` from `tabBranch` "
		"where `tabBranch`.`name`=`tabVault Cash Position`.`branch` "
		f"and `tabBranch`.`vault_custodian`={escaped_user})"
	)


def has_permission(doc, ptype=None, user=None):
	user = user or frappe.session.user
	permission_type = ptype or "read"
	if is_system_manager(user):
		return True
	if permission_type in {"cancel", "delete"}:
		return False
	if _has_read_all_role(user):
		return permission_type in READ_PERMISSION_TYPES
	is_custodian = frappe.db.get_value("Branch", doc.branch, "vault_custodian") == user
	if permission_type == "create":
		return bool(frappe.db.exists("Branch", {"vault_custodian": user}))
	if permission_type in READ_PERMISSION_TYPES:
		return is_custodian
	if permission_type == "write":
		return is_custodian and (doc.docstatus == 0 or _is_draft_submission(doc))
	if permission_type == "submit":
		return is_custodian and (doc.docstatus == 0 or _is_draft_submission(doc))
	return None


def _is_draft_submission(doc):
	"""Return whether the submitted in-memory document is still a draft in the database."""
	if doc.docstatus != 1 or not getattr(doc, "name", None):
		return False
	return frappe.db.get_value("Vault Cash Position", doc.name, "docstatus") == 0


def _ensure_table(doc, fieldname, denominations, currency):
	existing = {}
	for row in doc.get(fieldname):
		denomination = flt(row.denomination)
		if denomination in denominations and denomination not in existing:
			existing[denomination] = row

	doc.set(fieldname, [])
	for denomination in denominations:
		row = existing.get(flt(denomination))
		amount = flt(row.amount) if row else 0
		doc.append(
			fieldname,
			{
				"currency": currency,
				"denomination": denomination,
				"quantity": amount / flt(denomination),
				"amount": amount,
			},
		)


def _calculate_table(rows):
	total = 0
	for row in rows:
		amount = flt(row.amount)
		denomination = flt(row.denomination)
		if amount < 0:
			frappe.throw(_("Denomination amounts cannot be negative."))
		quantity = amount / denomination
		if abs(quantity - round(quantity)) > 0.000001:
			frappe.throw(
				_("Amount {0} must be a whole-number multiple of denomination {1}.").format(
					frappe.bold(row.amount), frappe.bold(row.denomination)
				)
			)
		row.quantity = round(quantity)
		total += amount
	return total


def _validate_table(rows, denominations, currency):
	actual = [flt(row.denomination) for row in rows]
	expected = [flt(value) for value in denominations]
	if sorted(actual) != sorted(expected) or len(actual) != len(expected):
		frappe.throw(_("{0} denomination table is incomplete or contains duplicate denominations.").format(currency))


@frappe.whitelist()
def get_creation_context():
	user = frappe.session.user
	branches = frappe.get_all("Branch", filters={"vault_custodian": user}, pluck="name", limit_page_length=2)
	if user == "Administrator":
		return {"allowed": True, "administrator": True, "branch": branches[0] if len(branches) == 1 else None}
	if len(branches) == 1:
		return {"allowed": True, "administrator": False, "branch": branches[0]}
	message = (_("Your account is assigned as Vault Custodian to multiple branches. Contact your administrator to correct the assignments before creating a Vault Cash Position.")
		if branches else _("Your account is not assigned as Vault Custodian to a branch. Contact your administrator before creating a Vault Cash Position."))
	return {"allowed": False, "administrator": False, "message": message}


def require_vcp_branch(branch):
	context = get_creation_context()
	if not context["allowed"]:
		frappe.throw(context["message"], frappe.PermissionError)
	if context["administrator"]:
		if not branch:
			frappe.throw(_("Select a branch for this Vault Cash Position."))
		return branch
	if branch and branch != context["branch"]:
		frappe.throw(_("You can only prepare a Vault Cash Position for your assigned branch."), frappe.PermissionError)
	return context["branch"]


@frappe.whitelist()
def get_balance_preview(branch):
	"""Read a consistent preview; the caller must retain its token until reload."""
	require_vcp_branch(branch)
	_lock_branch(branch)
	return _balance_snapshot(branch)


def _balance_snapshot(branch):
	# Current reads, including aggregate revisions, avoid a stale transaction snapshot.
	transfers = frappe.db.sql("""
		select count(*), max(modified) from `tabFund Transfer`
		where branch=%s and docstatus=1 and status='Submitted' for update
	""", branch)
	positions = frappe.db.sql("""
		select count(*), max(modified) from `tabVault Cash Position`
		where branch=%s and docstatus=1 for update
	""", branch)
	result = {}
	for currency in ("PHP", "USD"):
		name, balance = _latest_transfer_snapshot(branch, currency)
		result[currency.lower() + "_latest_fund_transfer"] = name
		result[currency.lower() + "_system_civ_balance"] = balance
	result["is_opening_position"] = not transfers[0][0] and not positions[0][0]
	result["token"] = hashlib.sha256(json.dumps(
		[branch, str(today()), transfers, positions, result], sort_keys=True, default=str
	).encode()).hexdigest()
	return result


def _latest_transfer_snapshot(branch, currency):
	result = frappe.db.sql(
		"""
		select name, civ_balance
		from `tabFund Transfer`
		where branch=%s and currency=%s and docstatus=1 and status='Submitted'
		order by date_of_transfer desc, creation desc
		limit 1 for update
		""",
		(branch, currency),
		as_dict=True,
	)
	if result:
		return result[0].name, flt(result[0].civ_balance)
	# A currency may not have a Fund Transfer after its cutover opening position.
	# Use the same opening-position fallback as Fund Transfer's canonical CIV lookup.
	return None, get_latest_civ_balance(branch, currency, lock=False)


def _is_accounting_analyst(user):
	return user == "Administrator" or "Accounting Analyst" in frappe.get_roles(user)


def _has_read_all_role(user):
	return bool(set(frappe.get_roles(user)).intersection(READ_ALL_ROLES))
