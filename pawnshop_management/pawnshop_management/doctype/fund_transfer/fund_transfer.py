# Copyright (c) 2026, Rabie Santillan and Eric Mendoza and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.naming import make_autoname
from frappe.utils import flt, getdate, now_datetime, today
from frappe.utils.password import check_password

from pawnshop_management.operations_access_control.access_control import get_branch_from_request_ip, is_system_manager

READ_ALL_ROLES = {"Accounting Analyst", "Auditor", "Operations Manager", "Settlement Member"}
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
	"Uncollected FX to Vault": {
		"currencies": {"USD"},
		"source": "Uncollected FX",
		"destination": "Vault",
		"impact": 1,
		"authorization": "none",
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


class FundTransfer(Document):
	def autoname(self):
		branch_code = get_fund_transfer_branch_code(self.branch)
		prefix = _safe_series_prefix(branch_code or self.branch or "FT")
		self.naming_series = "{0}-.######".format(prefix)
		self.name = make_autoname(self.naming_series)
		self.fund_transfer_series = self.name

	def before_insert(self):
		if not self.business_date:
			self.business_date = today()
		if not (self.flags.fx_selling_submission or self.flags.system_adjustment):
			self.initiated_by = frappe.session.user
		if not self.status:
			self.status = "Draft"
		if not self.source_system:
			self.source_system = "ERPNext"

	def validate(self):
		self._validate_imported_historical_document()
		self._validate_immutable_submitted_document()
		self._validate_pending_transfer_definition()
		rule = get_transfer_rule(self.transfer_type)
		self._validate_rule(rule)
		self._set_derived_fields(rule)
		self._validate_uncollected_fx_fields()

		if self.flags.fx_selling_submission:
			self._validate_fx_selling_submission()
		elif self.transfer_type == "Cash Position Adjustment":
			if not self.flags.system_adjustment:
				frappe.throw(_("Cash Position Adjustments can only be created by the reconciliation process."))
		else:
			self._validate_manual_transfer()

		if self.is_new():
			self._validate_day_open()

		# Credentials are used only by this submission, never by an ordinary save.
		if self._action != "submit":
			self.confirmation_password = None
			self.rover_password = None
			if self.docstatus == 0 and not (self.flags.fx_selling_submission or self.flags.system_adjustment):
				self.authorized_by = None
				self.authorization_datetime = None

	def _validate_manual_transfer(self):
		if self.docstatus == 2:
			return
		if self.transfer_type == "Cash Manager to Vault":
			frappe.throw(_("Cash Manager to Vault is retired. Use Rover to Vault for new deliveries."))
		if self.status not in {"Draft", "Submitted", "Cancelled"}:
			frappe.throw(_("Pending approvals are retired. Create a new Fund Transfer."))
		previous = self.get_doc_before_save()
		if previous and self.initiated_by != previous.initiated_by:
			frappe.throw(_("The Fund Transfer initiator cannot be changed."), frappe.PermissionError)
		require_transfer_initiator(self)
		if self._action == "submit" and self.initiated_by != frappe.session.user:
			frappe.throw(_("Only the original initiator can submit this Fund Transfer. Recreate it if assignments changed."), frappe.PermissionError)

	def _validate_day_open(self, posting_date=None):
		_lock_branch(self.branch)
		# Only the internal reconciliation path may post after closing. Do not trust
		# a transfer type or client-provided document fields as an exemption.
		if self.flags.system_adjustment and self.transfer_type == "Cash Position Adjustment":
			self._validate_reconciliation_adjustment()
			return
		validate_fund_transfer_day_open(self.branch, posting_date)

	def _validate_reconciliation_adjustment(self):
		from pawnshop_management.pawnshop_management.doctype.vault_cash_position.vault_cash_position import _is_accounting_analyst

		if not self.cash_position or not _is_accounting_analyst(frappe.session.user):
			frappe.throw(_("Invalid reconciliation adjustment."), frappe.PermissionError)
		position = frappe.get_doc("Vault Cash Position", self.cash_position, for_update=True)
		variance = position.get(self.currency.lower() + "_variance") if position else None
		if (not position or position.branch != self.branch or position.docstatus != 1
			or position.reconciliation_status != "Pending Accounting Review"
			or not flt(variance) or flt(self.vault_balance_change) != flt(variance)
			or flt(self.amount) != abs(flt(variance))):
			frappe.throw(_("The adjustment must match a submitted Vault Cash Position awaiting reconciliation."), frappe.PermissionError)

	def before_submit(self):
		# Serialize with VCP submission/cancellation before checking today's close.
		_lock_branch(self.branch)
		self.date_of_transfer = now_datetime()
		self.business_date = getdate(self.date_of_transfer)
		self._validate_day_open(self.business_date)
		self._authorize_workflow_submission()
		self._validate_authorization()

		if self.currency == "USD" and self.transfer_type == "ForEx to Vault":
			self._validate_usd_availability()
		elif self.transfer_type == "Uncollected FX to Vault":
			self._validate_uncollected_fx_source()

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
		if self.flags.system_adjustment or self.flags.fx_selling_submission:
			return
		previous_status = frappe.db.get_value("Fund Transfer", self.name, "status") or "Draft"
		if previous_status != "Draft":
			frappe.throw(_("Only a Draft Fund Transfer can be submitted."))
		require_transfer_initiator(self)
		if self.initiated_by != frappe.session.user:
			frappe.throw(_("Only the original initiator can submit this Fund Transfer."), frappe.PermissionError)
		rule = get_transfer_rule(self.transfer_type)
		authorization = rule.get("authorization", "cashier")
		try:
			if authorization == "none":
				self.authorized_by = frappe.session.user
			elif authorization == "cashier":
				confirmer = get_expected_authorizer(self.branch, rule)
				if not confirmer:
					frappe.throw(_("No {0} is assigned to branch {1}.").format(
						PARTICIPANT_LABELS[get_confirmer_field(rule)], self.branch))
				_verify_confirmation_password(confirmer, self.confirmation_password, self.initiated_by)
				self.expected_authorizer = confirmer
				self.authorized_by = confirmer
			elif authorization == "rover":
				if not self.rover or "Rover" not in frappe.get_roles(self.rover):
					frappe.throw(_("Select an enabled User with the Rover role."), frappe.PermissionError)
				_verify_confirmation_password(self.rover, self.rover_password, self.initiated_by)
				self.authorized_by = self.rover
			else:
				frappe.throw(_("This transfer type cannot be submitted manually."))
		finally:
			self.confirmation_password = None
			self.rover_password = None
		self.authorization_datetime = now_datetime()

	def on_submit(self):
		from pawnshop_management.pawnshop_management.fund_transfer_google import queue_google_uat_sync

		queue_google_uat_sync(self.name)

	def before_cancel(self):
		if frappe.session.user != "Administrator":
			frappe.throw(_("Submitted Fund Transfers cannot be cancelled or reversed."))
		if self.fx_selling and not self.flags.coordinated_fx_lifecycle:
			frappe.throw(
				_("Use Cancel Linked Transaction to cancel this Fund Transfer and its FX Selling document together.")
			)

	def on_trash(self):
		if self.status == "Imported Historical":
			frappe.throw(_("Imported Historical Fund Transfers cannot be deleted."))
		if (self.docstatus == 1 or self.status == "Submitted") and frappe.session.user != "Administrator":
			frappe.throw(_("Submitted Fund Transfers cannot be deleted."))
		if self.fx_selling and not self.flags.coordinated_fx_lifecycle:
			frappe.throw(
				_("Use Delete Linked Transaction to delete this Fund Transfer and its FX Selling document together.")
			)

	def _validate_imported_historical_document(self):
		if self.status != "Imported Historical" or self.is_new() or self.flags.importing_historical:
			return
		frappe.throw(_("Imported Historical Fund Transfers are read-only."), frappe.PermissionError)

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
		if self.flags.fx_selling_submission:
			self._validate_fx_selling_submission()
			return
		rule = get_transfer_rule(self.transfer_type)
		authorization = rule.get("authorization", "cashier")
		if authorization == "cashier":
			expected = get_expected_authorizer(self.branch, rule)
			if not expected or self.authorized_by != expected:
				frappe.throw(_("The currently assigned receiving person must confirm this transfer."), frappe.PermissionError)
		elif authorization == "rover":
			if not self.rover or self.authorized_by != self.rover or "Rover" not in frappe.get_roles(self.rover):
				frappe.throw(_("A valid Rover confirmation is required."), frappe.PermissionError)
		elif authorization == "none":
			require_branch_vault_custodian(self.branch)
		elif authorization == "system":
			if not self.flags.system_adjustment:
				frappe.throw(_("Invalid system adjustment authorization."), frappe.PermissionError)

	def _validate_fx_selling_submission(self):
		if self.currency != "USD" or self.transfer_type != "Vault to Cash Manager" or not self.fx_selling:
			frappe.throw(_("Invalid FX Selling Fund Transfer."), frappe.PermissionError)
		if not self.customer_name:
			frappe.throw(_("Customer Name is required for an FX Selling Fund Transfer."))
		if not frappe.db.exists("FX Selling", self.fx_selling):
			frappe.throw(_("The linked FX Selling document does not exist."))

		fx_selling = frappe.get_doc("FX Selling", self.fx_selling)
		if fx_selling.docstatus != 1:
			frappe.throw(_("The linked FX Selling document must be submitted."), frappe.PermissionError)
		if self.branch != fx_selling.branch:
			frappe.throw(_("The Fund Transfer branch must match the linked FX Selling branch."), frappe.PermissionError)
		if self.customer_name != fx_selling.customer_name:
			frappe.throw(_("The Fund Transfer customer must match the linked FX Selling customer."), frappe.PermissionError)

		usd_amount = sum(flt(row.amount) for row in fx_selling.currencies if row.currency == "USD")
		if not usd_amount or flt(self.amount) != usd_amount:
			frappe.throw(_("The Fund Transfer amount must match the linked FX Selling USD amount."), frappe.PermissionError)
		if not self.authorized_by or self.authorized_by != fx_selling.seller or self.authorized_by != frappe.session.user:
			frappe.throw(_("The submitting FX Cashier must authorize the linked Fund Transfer."), frappe.PermissionError)

		vault_custodian = frappe.db.get_value("Branch", self.branch, "vault_custodian")
		if not vault_custodian or self.initiated_by != vault_custodian:
			frappe.throw(_("The branch's assigned Vault Custodian must be Given By."), frappe.PermissionError)

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

	def _validate_uncollected_fx_fields(self):
		fields = (self.get("fx_cpr_date"), self.get("fx_expected_amount"))
		if self.transfer_type != "Uncollected FX to Vault":
			if any(fields):
				frappe.throw(_("Uncollected FX envelope details are only valid for Uncollected FX to Vault."))
			return
		if not self.fx_cpr_date or flt(self.fx_expected_amount) <= 0:
			frappe.throw(_("Select an uncollected FX envelope before saving."))
		for label, value in ((_("Expected USD"), self.fx_expected_amount), (_("Actual USD"), self.amount)):
			if flt(value) != int(flt(value)):
				frappe.throw(_("{0} must be a whole-dollar amount.").format(label))
		if flt(self.amount) > flt(self.fx_expected_amount):
			frappe.throw(_("Actual USD cannot exceed the selected envelope's expected USD."))
		self.fx_difference_amount = flt(self.fx_expected_amount) - flt(self.amount)

	def _validate_uncollected_fx_source(self):
		from pawnshop_management.pawnshop_management.fund_transfer_google import validate_uncollected_fx_envelope

		duplicate = frappe.db.get_value(
			"Fund Transfer",
			{
				"branch": self.branch,
				"fx_cpr_date": self.fx_cpr_date,
				"transfer_type": "Uncollected FX to Vault",
				"docstatus": 1,
				"name": ["!=", self.name],
			},
			"name",
		)
		if duplicate:
			frappe.throw(_("This uncollected FX envelope was already transferred in {0}.").format(duplicate))
		envelope = validate_uncollected_fx_envelope(self.branch, self.fx_cpr_date)
		if flt(envelope.expected_amount) != flt(self.fx_expected_amount):
			frappe.throw(_("The selected envelope amount changed. Reload and select it again."))
		self.fx_source_row = envelope.source_row
		self.fx_source_rate = envelope.rate

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
		if self.transfer_type == "Uncollected FX to Vault":
			self.comments = "{0}-Uncollected FX transfer".format(self.received_by)

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
			"customer_name",
			"fx_selling",
			"fx_cpr_date",
			"fx_expected_amount",
			"fx_difference_amount",
			"fx_source_row",
			"fx_source_rate",
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


PARTICIPANT_LABELS = {
	"vault_custodian": _("Vault Custodian"),
	"pawnshop_cashier": _("Pawnshop Cashier"),
	"remittance_cashier": _("Remittance Cashier"),
	"fx_cashier": _("Foreign Exchange Cashier"),
}


def get_initiator_field(rule):
	if rule.get("authorizer_field") and rule["destination"] == "Vault":
		return rule["authorizer_field"]
	return "vault_custodian"


def get_confirmer_field(rule):
	if not rule.get("authorizer_field"):
		return None
	return rule["authorizer_field"] if rule["source"] == "Vault" else "vault_custodian"


def get_expected_authorizer(branch, rule):
	fieldname = get_confirmer_field(rule)
	return frappe.db.get_value("Branch", branch, fieldname) if fieldname else None


def _is_assigned_initiator(branch, transfer_type, user):
	if transfer_type not in TRANSFER_RULES or transfer_type in {"Cash Manager to Vault", "Cash Position Adjustment"}:
		return False
	return bool(branch and frappe.db.get_value("Branch", branch, get_initiator_field(TRANSFER_RULES[transfer_type])) == user)


def require_transfer_initiator(doc):
	user = frappe.session.user
	if is_system_manager(user):
		return
	if not _is_assigned_initiator(doc.branch, doc.transfer_type, user):
		frappe.throw(_("Only the branch's assigned source cashier or Vault Custodian can initiate this transfer type."), frappe.PermissionError)
	if doc.initiated_by != user:
		frappe.throw(_("Only the original initiator can edit this Fund Transfer."), frappe.PermissionError)


def _verify_confirmation_password(user, password, initiator):
	if not frappe.db.get_value("User", user, "enabled"):
		frappe.throw(_("The confirming user must be enabled."), frappe.PermissionError)
	if user == initiator or user == frappe.session.user:
		frappe.throw(_("The initiator cannot confirm their own transfer."), frappe.PermissionError)
	if not password:
		frappe.throw(_("The confirming person's password is required."), frappe.AuthenticationError)
	key = _confirmation_rate_limit_key(user)
	if int(frappe.cache().get_value(key, expires=True) or 0) >= 5:
		frappe.throw(_("Confirmation is locked after repeated failed attempts. Try again in five minutes."), frappe.AuthenticationError)
	try:
		check_password(user, password)
	except frappe.AuthenticationError:
		attempts = int(frappe.cache().get_value(key, expires=True) or 0) + 1
		frappe.cache().set_value(key, attempts, expires_in_sec=300)
		raise
	frappe.cache().delete_value(key)


@frappe.whitelist()
def get_entry_context(branch=None, currency=None):
	"""Return only the current user's permitted branches/types and assigned confirmers."""
	user = frappe.session.user
	admin = is_system_manager(user)
	branches = frappe.get_all("Branch", fields=["name"] + list(PARTICIPANT_LABELS))
	permitted = [b for b in branches if admin or user in [b.get(f) for f in PARTICIPANT_LABELS]]
	selected = next((b for b in permitted if b.name == branch), None)
	transfers = []
	if selected:
		for name, rule in TRANSFER_RULES.items():
			if name in {"Cash Manager to Vault", "Cash Position Adjustment"}:
				continue
			if currency not in rule["currencies"]:
				continue
			if not admin and selected.get(get_initiator_field(rule)) != user:
				continue
			field = get_confirmer_field(rule)
			transfers.append({"transfer_type": name, "confirmer": selected.get(field) if field else None,
				"confirmer_label": PARTICIPANT_LABELS.get(field), "authorization": rule.get("authorization", "cashier")})
	closed_position = get_closed_vault_position(branch) if selected else None
	return {"branches": [b.name for b in permitted], "transfers": transfers,
		"closed_position": closed_position,
		"closure_message": fund_transfer_closure_message(branch, today(), closed_position) if closed_position else None}


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


def get_closed_vault_position(branch, posting_date=None, for_update=False):
	if not branch:
		return None
	# FOR UPDATE is a current read in MariaDB, even if this transaction already
	# established an older repeatable-read snapshot before waiting for the branch.
	rows = frappe.db.sql("""
		select name from `tabVault Cash Position`
		where branch=%s and business_date=%s and docstatus=1
		order by name limit 1
		""" + (" for update" if for_update else ""), (branch, posting_date or today()))
	return rows[0][0] if rows else None


def fund_transfer_closure_message(branch, posting_date, position):
	return _("Fund transfers are closed for {0} on {1} because Vault Cash Position {2} has already been submitted.").format(
		frappe.utils.escape_html(branch), frappe.utils.formatdate(posting_date),
		frappe.utils.get_link_to_form("Vault Cash Position", position))


def validate_fund_transfer_day_open(branch, posting_date=None):
	_lock_branch(branch)
	posting_date = posting_date or today()
	position = get_closed_vault_position(branch, posting_date, for_update=True)
	if position:
		frappe.throw(fund_transfer_closure_message(branch, posting_date, position))


def get_latest_civ_balance(branch, currency, lock=True):
	if lock:
		_lock_branch(branch)
	result = frappe.db.sql(
		"""
		select civ_balance
		from `tabFund Transfer`
		where branch=%s and currency=%s and docstatus=1 and status='Submitted'
		order by date_of_transfer desc, creation desc
		limit 1 for update
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
	"""Compatibility for transfers that never required a second person's password."""
	doc = frappe.get_doc("Fund Transfer", name)
	doc.check_permission("write")
	if get_transfer_rule(doc.transfer_type).get("authorization") != "none":
		frappe.throw(_("Use Submit and confirm with the receiving person's password. Pending approvals are retired."))
	doc.submit()
	return doc.as_dict()


@frappe.whitelist()
def approve_cashier_transfer(name):
	frappe.throw(_("Pending approvals are retired. Use Submit with password confirmation."))


@frappe.whitelist()
def reject_cashier_transfer(name, reason=None):
	frappe.throw(_("Pending approvals are retired."))


@frappe.whitelist()
def confirm_rover_transfer(name, rover, password):
	frappe.throw(_("Use Submit with Rover password confirmation. Pending approvals are retired."))


@frappe.whitelist()
def cancel_pending_transfer(name):
	doc = frappe.get_doc("Fund Transfer", name)
	doc.check_permission("write")
	require_transfer_initiator(doc)
	if doc.docstatus != 0 or doc.status != "Draft":
		frappe.throw(_("Only a Draft Fund Transfer can be cancelled."))
	doc.status = "Cancelled"
	doc.save()
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
	if is_system_manager(user) or _has_read_all_role(user):
		return None
	branch = get_branch_from_request_ip()
	if not branch:
		return "1=0"
	return "`tabFund Transfer`.`branch`={0}".format(frappe.db.escape(branch))


@frappe.whitelist()
def get_current_branch_context():
	"""Return the request-IP branch so Desk can explain a fail-closed empty list."""
	user = frappe.session.user
	if is_system_manager(user) or _has_read_all_role(user):
		return {"unrestricted": True}
	return {"branch": get_branch_from_request_ip()}


def has_permission(doc, ptype=None, user=None):
	user = user or frappe.session.user
	permission_type = ptype or "read"
	if permission_type in {"cancel", "delete"}:
		return user == "Administrator"
	if is_system_manager(user):
		return True
	if permission_type == "create":
		if doc and doc.get("branch") and doc.get("transfer_type"):
			return _is_assigned_initiator(doc.branch, doc.transfer_type, user)
		return any(frappe.db.exists("Branch", {field: user}) for field in PARTICIPANT_LABELS)
	if permission_type in READ_PERMISSION_TYPES:
		return _can_read_from_current_branch(doc, user)
	if permission_type in {"submit", "write"}:
		return _can_write_draft(doc, user)
	return None


def _can_read_from_current_branch(doc, user):
	if _has_read_all_role(user):
		return True
	branch = get_branch_from_request_ip()
	return bool(branch and branch == doc.branch)


def _has_read_all_role(user):
	return bool(set(frappe.get_roles(user)).intersection(READ_ALL_ROLES))


def _can_write_draft(doc, user):
	if not doc.get("name"):
		return False
	stored = frappe.db.get_value("Fund Transfer", doc.name, ["docstatus", "status", "initiated_by", "branch", "transfer_type"], as_dict=True)
	return bool(stored and stored.docstatus == 0 and stored.status == "Draft"
		and stored.initiated_by == user and doc.initiated_by == user
		and _is_assigned_initiator(stored.branch, stored.transfer_type, user)
		and _is_assigned_initiator(doc.branch, doc.transfer_type, user))


def _safe_series_prefix(value):
	import re

	value = str(value or "FT").strip().upper()
	return re.sub(r"[^A-Z0-9]+", "-", value).strip("-") or "FT"


def _given_by(doc):
	if get_transfer_rule(doc.transfer_type).get("authorizer_field"):
		return doc.initiated_by
	if doc.source == "Vault":
		return doc.initiated_by
	if doc.source == "Armored Van":
		return doc.external_party or "Armored Van"
	if doc.source == "Uncollected FX":
		return "Uncollected FX"
	return doc.authorized_by or doc.source


def _received_by(doc):
	if get_transfer_rule(doc.transfer_type).get("authorizer_field"):
		return doc.authorized_by
	if doc.fx_selling and doc.customer_name:
		return doc.customer_name
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


def _confirmation_rate_limit_key(user):
	request_ip = getattr(frappe.local, "request_ip", None) or "unknown"
	return "fund-transfer-confirmation:{0}:{1}".format(user, request_ip)
