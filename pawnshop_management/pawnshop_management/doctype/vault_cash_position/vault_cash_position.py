# Copyright (c) 2026, Rabie Santillan and Eric Mendoza and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.naming import make_autoname
from frappe.utils import flt, getdate, now_datetime, today

from pawnshop_management.operations_access_control.access_control import is_system_manager
from pawnshop_management.pawnshop_management.doctype.fund_transfer.fund_transfer import (
	_lock_branch,
	create_cash_position_adjustment,
	get_fund_transfer_branch_code,
	get_latest_civ_balance,
	require_branch_vault_custodian,
)


PHP_DENOMINATIONS = (1000, 500, 200, 100, 50, 20, 10, 5, 1, 0.25)
USD_DENOMINATIONS = (100, 50, 20, 10, 5, 2, 1)
READ_PERMISSION_TYPES = {"read", "report", "print", "email", "export"}


class VaultCashPosition(Document):
	def autoname(self):
		branch_code = get_fund_transfer_branch_code(self.branch) or "VCP"
		self.name = make_autoname("VCP{0}-.YYYY.-.#####".format(branch_code))

	def before_insert(self):
		self.business_date = today()
		self.vault_custodian = frappe.session.user
		self.reconciliation_status = "Draft"
		self._ensure_denomination_rows()

	def validate(self):
		if not self.flags.ignore_vault_custodian_check:
			require_branch_vault_custodian(self.branch)
		if self.business_date and getdate(self.business_date) != getdate(today()) and not is_system_manager(
			frappe.session.user
		):
			frappe.throw(_("Vault Cash Positions cannot be backdated."))
		self._ensure_denomination_rows()
		self._calculate_actual_totals()

	def before_submit(self):
		require_branch_vault_custodian(self.branch)
		self._validate_unique_daily_position()
		self._validate_complete_tables()
		_lock_branch(self.branch)
		self.count_datetime = now_datetime()
		self.vault_custodian = frappe.session.user

		self.php_latest_fund_transfer, php_balance = _latest_transfer_snapshot(self.branch, "PHP")
		self.usd_latest_fund_transfer, usd_balance = _latest_transfer_snapshot(self.branch, "USD")
		self.is_opening_position = not self.php_latest_fund_transfer and not self.usd_latest_fund_transfer and not frappe.db.exists(
			"Vault Cash Position", {"branch": self.branch, "docstatus": 1}
		)

		if self.is_opening_position:
			self.php_system_civ_balance = self.php_actual_cash
			self.usd_system_civ_balance = self.usd_actual_cash
		else:
			self.php_system_civ_balance = php_balance
			self.usd_system_civ_balance = usd_balance

		self.php_variance = flt(self.php_actual_cash) - flt(self.php_system_civ_balance)
		self.usd_variance = flt(self.usd_actual_cash) - flt(self.usd_system_civ_balance)
		self.php_reconciled_ending_balance = self.php_system_civ_balance
		self.usd_reconciled_ending_balance = self.usd_system_civ_balance

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
		frappe.throw(_("Submitted Vault Cash Positions cannot be cancelled."))

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
		existing = frappe.db.exists(
			"Vault Cash Position",
			{
				"branch": self.branch,
				"business_date": self.business_date,
				"docstatus": ["!=", 2],
				"name": ["!=", self.name],
			},
		)
		if existing:
			frappe.throw(_("Vault Cash Position {0} already exists for this branch and date.").format(existing))


@frappe.whitelist()
def approve_reconciliation(name, comments=None):
	if not _is_accounting_analyst(frappe.session.user):
		frappe.throw(_("Only an Accounting Analyst can approve cash-position variances."), frappe.PermissionError)

	doc = frappe.get_doc("Vault Cash Position", name)
	if doc.docstatus != 1 or doc.reconciliation_status != "Pending Accounting Review":
		frappe.throw(_("This Vault Cash Position is not pending Accounting review."))

	_lock_branch(doc.branch)
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
	if is_system_manager(user) or _is_accounting_analyst(user):
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
	if _is_accounting_analyst(user):
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
		quantity = flt(row.quantity) if row else 0
		doc.append(
			fieldname,
			{
				"currency": currency,
				"denomination": denomination,
				"quantity": quantity,
				"amount": flt(denomination) * quantity,
			},
		)


def _calculate_table(rows):
	total = 0
	for row in rows:
		if flt(row.quantity) < 0:
			frappe.throw(_("Denomination quantities cannot be negative."))
		row.amount = flt(row.denomination) * flt(row.quantity)
		total += row.amount
	return total


def _validate_table(rows, denominations, currency):
	actual = [flt(row.denomination) for row in rows]
	expected = [flt(value) for value in denominations]
	if sorted(actual) != sorted(expected) or len(actual) != len(expected):
		frappe.throw(_("{0} denomination table is incomplete or contains duplicate denominations.").format(currency))


def _latest_transfer_snapshot(branch, currency):
	result = frappe.db.sql(
		"""
		select name, civ_balance
		from `tabFund Transfer`
		where branch=%s and currency=%s and docstatus=1 and status='Submitted'
		order by date_of_transfer desc, creation desc
		limit 1
		""",
		(branch, currency),
		as_dict=True,
	)
	return (result[0].name, flt(result[0].civ_balance)) if result else (None, 0)


def _is_accounting_analyst(user):
	return user == "Administrator" or "Accounting Analyst" in frappe.get_roles(user)
