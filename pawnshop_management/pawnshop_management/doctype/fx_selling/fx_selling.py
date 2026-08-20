from __future__ import unicode_literals

import json
import math

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.naming import make_autoname
from frappe.utils import flt, getdate, now_datetime, today

from pawnshop_management.operations_access_control.access_control import (
	get_branch_from_request_ip,
	has_active_branch_role,
	is_system_manager,
)
from pawnshop_management.pawnshop_management.doctype.fund_transfer.fund_transfer import (
	_safe_series_prefix,
	get_fund_transfer_branch_code,
)


FX_ROLE = "Foreign Exchange Cashier"
READ_ALL_ROLES = {"Accounting Analyst", "Auditor"}
RATE_CONFIG = {
	"USD": (1, 0.70, 2), "YEN": (2, 0.01, 5), "EUR": (3, 1.00, 2),
	"SR": (4, 1.00, 2), "SR <= 20": (5, 1.00, 2), "SR = 1": (6, 1.00, 2),
	"PDS": (7, 1.00, 2), "SGD": (8, 1.00, 2), "UAE": (9, 1.00, 2),
	"AUD": (10, 1.00, 2), "CAD": (11, 1.00, 2), "HKD": (12, 1.00, 2),
	"WON": (13, 0.01, 3), "NT": (14, 1.00, 2), "QR": (15, 1.00, 2),
	"YUAN": (16, 1.00, 2), "BR": (18, 1.00, 2), "MYR": (20, 1.00, 2),
	"SF": (22, 1.00, 2), "THAI BAHT": (23, 1.00, 2), "IDR": (24, 1.00, 4),
	"NZD": (25, 1.00, 4),
}
SHEET_CURRENCY = {"SR <= 20": "SR<=20", "SR = 1": "SR=1", "THAI BAHT": "THAI B"}


class FXSelling(Document):
	def autoname(self):
		self.branch = self.branch or get_branch_from_request_ip()
		if not self.branch:
			frappe.throw(_("Branch is required before naming FX Selling."))
		code = _safe_series_prefix(get_fund_transfer_branch_code(self.branch) or "FXS")
		self.naming_series = "FXS-{0}-.YYYY.-.#####".format(code)
		self.name = make_autoname(self.naming_series)

	def before_insert(self):
		self.branch = self.branch or get_branch_from_request_ip()
		self.business_date = today()
		self.seller = frappe.session.user
		self.status = "Draft"

	def validate(self):
		self._validate_enabled()
		self._validate_actor()
		self._validate_immutable_submitted()
		self._validate_customer()
		refresh_and_validate_rates(self)
		self._validate_currencies()

	def before_submit(self):
		self._validate_actor()
		settings = frappe.get_single("FX Selling Settings")
		if not settings.enable_google_writes or not settings.write_spreadsheet_id:
			frappe.throw(_("Google writes must be enabled with a UAT write spreadsheet before submitting FX Selling."))
		self.status = "Processing"
		self.posting_datetime = now_datetime()
		self.business_date = getdate(self.posting_datetime)
		refresh_and_validate_rates(self)
		validate_tracker_requests(self, settings)

	def on_submit(self):
		try:
			self._create_usd_fund_transfer()
			sync_google_rows(self)
			self.db_set("status", "Completed", update_modified=False)
			self.db_set("google_sync_status", "Synced", update_modified=False)
		except Exception:
			self.db_set("google_sync_status", "Failed", update_modified=False)
			self.db_set("google_sync_error", frappe.get_traceback()[-2000:], update_modified=False)
			raise

	def before_cancel(self):
		if frappe.session.user != "Administrator":
			frappe.throw(_("Submitted FX Selling documents cannot be cancelled. Use an audited reversal process."))
		if self.fund_transfer and not self.flags.coordinated_fx_lifecycle:
			frappe.throw(
				_("Use Cancel Linked Transaction to cancel this FX Selling document and its Fund Transfer together.")
			)

	def on_trash(self):
		if frappe.session.user != "Administrator":
			frappe.throw(_("Only Administrator can delete FX Selling documents."), frappe.PermissionError)
		if self.fund_transfer and not self.flags.coordinated_fx_lifecycle:
			frappe.throw(
				_("Use Delete Linked Transaction to delete this FX Selling document and its Fund Transfer together.")
			)
		if self.docstatus == 1:
			frappe.throw(_("Submitted FX Selling documents cannot be deleted."))

	def _validate_enabled(self):
		if not frappe.get_single("FX Selling Settings").enabled:
			frappe.throw(_("FX Selling is disabled in FX Selling Settings."))

	def _validate_actor(self):
		if is_system_manager(frappe.session.user):
			return
		if not self.branch or get_branch_from_request_ip() != self.branch:
			frappe.throw(_("FX Selling is restricted to the branch mapped to the current request IP."), frappe.PermissionError)
		if not has_active_branch_role(frappe.session.user, self.branch, FX_ROLE):
			frappe.throw(_("Only the branch's active Foreign Exchange Cashier can process FX Selling."), frappe.PermissionError)

	def _validate_customer(self):
		if not self.customer or not frappe.db.exists("Customer", self.customer):
			frappe.throw(_("Select a valid Customer."))
		customer = frappe.db.get_value(
			"Customer", self.customer,
			["customer_name", "customer_tracking_no", "customer_primary_contact", "disabled"], as_dict=True,
		)
		if customer.disabled:
			frappe.throw(_("This customer record is disabled."))
		self.customer_name = customer.customer_name
		self.customer_tracking_no = customer.customer_tracking_no
		self.customer_contact = customer.customer_primary_contact
		_validate_customer_id(self.customer, self.customer_id_picture)

	def _validate_currencies(self):
		if not self.currencies:
			frappe.throw(_("Add at least one currency."))
		seen = set()
		total = 0
		for row in self.currencies:
			if row.currency not in RATE_CONFIG:
				frappe.throw(_("Unsupported currency {0}.").format(row.currency))
			if row.currency in seen:
				frappe.throw(_("Currency {0} can only appear once.").format(row.currency))
			seen.add(row.currency)
			if flt(row.amount) <= 0:
				frappe.throw(_("Amount Out must be greater than zero for {0}.").format(row.currency))
			if row.currency != "USD" and not row.request_no:
				frappe.throw(_("Select a Transfer Tracker request for {0}.").format(row.currency))
			total += flt(row.peso_amount)
		self.total_peso_amount = total
		if total >= 100000 and (not self.source_of_funds or not self.purpose):
			frappe.throw(_("Source of Funds and Purpose are required for transactions of PHP 100,000 or more."))

	def _validate_immutable_submitted(self):
		if self.is_new():
			return
		previous = self.get_doc_before_save()
		if previous and previous.docstatus == 1:
			frappe.throw(_("Submitted FX Selling documents are immutable."))

	def _create_usd_fund_transfer(self):
		usd_amount = sum(flt(row.amount) for row in self.currencies if row.currency == "USD")
		if not usd_amount:
			return
		vault_custodian = frappe.db.get_value("Branch", self.branch, "vault_custodian")
		if not vault_custodian:
			frappe.throw(_("No Vault Custodian is assigned to branch {0}.").format(self.branch))
		doc = frappe.new_doc("Fund Transfer")
		doc.branch = self.branch
		doc.currency = "USD"
		doc.transfer_type = "Vault to Cash Manager"
		doc.amount = usd_amount
		doc.initiated_by = vault_custodian
		doc.authorized_by = frappe.session.user
		doc.authorization_datetime = now_datetime()
		doc.source_system = "ERPNext"
		doc.customer_name = self.customer_name
		doc.fx_selling = self.name
		doc.comments = "FOREX SELLING"
		doc.flags.fx_selling_submission = True
		doc.flags.authorized_submission = True
		doc.insert(ignore_permissions=True)
		doc.flags.fx_selling_submission = True
		doc.flags.authorized_submission = True
		doc.flags.ignore_permissions = True
		doc.submit()
		self.db_set("fund_transfer", doc.name, update_modified=False)


def _validate_customer_id(customer, selected_id):
	from pawnshop_management.pawnshop_management.utils import get_contact_id_pictures_by_customer

	data = get_contact_id_pictures_by_customer(customer)
	options = data.get("options") or []
	if data.get("all_customer_ids_expired"):
		frappe.throw(_("All customer IDs have expired."))
	if not selected_id or selected_id not in {row.get("value") for row in options if not row.get("is_expired")}:
		frappe.throw(_("Select a valid, unexpired customer ID."))


def _round_up_rate(value, precision):
	intermediate = math.ceil(flt(value) * 1000) / 1000.0
	return round(intermediate, precision)


def _sheet_service(settings):
	import json as json_module
	from google.oauth2 import service_account
	from googleapiclient.discovery import build

	raw = settings.get_password("google_service_account_json", raise_exception=False)
	if not raw:
		raw = frappe.get_single("Fund Transfer Settings").get_password(
			"google_service_account_json", raise_exception=False
		)
	if not raw:
		frappe.throw(_("Google Service Account credentials are not configured."))
	credentials = service_account.Credentials.from_service_account_info(
		json_module.loads(raw), scopes=["https://www.googleapis.com/auth/spreadsheets"]
	)
	return build("sheets", "v4", credentials=credentials, cache_discovery=False)


def _quote_sheet(name):
	return "'{0}'".format(str(name or "").replace("'", "''"))


def _latest_rates(settings=None):
	settings = settings or frappe.get_single("FX Selling Settings")
	try:
		service = _sheet_service(settings)
		values = service.spreadsheets().values().get(
			spreadsheetId=settings.rates_spreadsheet_id,
			range="{0}!A3:Z".format(_quote_sheet(settings.rates_sheet)),
			valueRenderOption="UNFORMATTED_VALUE",
		).execute().get("values", [])
	except Exception:
		frappe.log_error(frappe.get_traceback(), "FX Selling Rate Load Failed")
		frappe.throw(
			_("ERPNext could not load rates from the Google All Rates sheet. Verify the spreadsheet ID and service-account access, then try again.")
		)
	result = {}
	for currency, (column, addition, precision) in RATE_CONFIG.items():
		for offset in range(len(values) - 1, -1, -1):
			row = values[offset]
			if len(row) <= column or row[column] in (None, ""):
				continue
			base = flt(row[column])
			result[currency] = {
				"currency": currency, "base_rate": base, "selling_addition": addition,
				"selling_rate": _round_up_rate(base + addition, precision), "source_row": offset + 3,
			}
			break
	return result


@frappe.whitelist()
def get_current_rates():
	settings = frappe.get_single("FX Selling Settings")
	if not settings.enabled:
		frappe.throw(_("FX Selling is disabled."))
	return _latest_rates(settings)


@frappe.whitelist()
def get_fx_selling_context():
	return {"branch": get_branch_from_request_ip(), "seller": frappe.session.user}


@frappe.whitelist()
def cancel_linked_transaction(reference_doctype, reference_name):
	_require_administrator_lifecycle_access()
	fx_selling, fund_transfer = _get_linked_transaction_documents(reference_doctype, reference_name)
	_savepoint = "cancel_fx_selling_transaction"
	frappe.db.savepoint(_savepoint)
	try:
		_cancel_if_submitted(fx_selling)
		_cancel_if_submitted(fund_transfer)
	except Exception:
		frappe.db.rollback(save_point=_savepoint)
		raise
	return _linked_transaction_result(fx_selling, fund_transfer)


@frappe.whitelist()
def delete_linked_transaction(reference_doctype, reference_name):
	_require_administrator_lifecycle_access()
	fx_selling, fund_transfer = _get_linked_transaction_documents(reference_doctype, reference_name)
	_savepoint = "delete_fx_selling_transaction"
	frappe.db.savepoint(_savepoint)
	try:
		_cancel_if_submitted(fx_selling)
		_cancel_if_submitted(fund_transfer)
		# FX Selling owns the only database Link, so remove it before its Fund Transfer.
		_delete_if_present(fx_selling)
		_delete_if_present(fund_transfer)
	except Exception:
		frappe.db.rollback(save_point=_savepoint)
		raise
	return {"deleted": True}


def _require_administrator_lifecycle_access():
	if frappe.session.user != "Administrator":
		frappe.throw(_("Only Administrator can cancel or delete linked FX transactions."), frappe.PermissionError)


def _get_linked_transaction_documents(reference_doctype, reference_name):
	if reference_doctype not in {"FX Selling", "Fund Transfer"}:
		frappe.throw(_("Invalid linked transaction type."))
	if not frappe.db.exists(reference_doctype, reference_name):
		frappe.throw(_("{0} {1} does not exist.").format(reference_doctype, reference_name))

	fx_selling = None
	fund_transfer = None
	if reference_doctype == "FX Selling":
		fx_selling = frappe.get_doc("FX Selling", reference_name)
		if fx_selling.fund_transfer and frappe.db.exists("Fund Transfer", fx_selling.fund_transfer):
			fund_transfer = frappe.get_doc("Fund Transfer", fx_selling.fund_transfer)
	else:
		fund_transfer = frappe.get_doc("Fund Transfer", reference_name)
		fx_selling_name = frappe.db.get_value("FX Selling", {"fund_transfer": reference_name}, "name")
		if fx_selling_name:
			fx_selling = frappe.get_doc("FX Selling", fx_selling_name)

	return fx_selling, fund_transfer


def _cancel_if_submitted(doc):
	if not doc or doc.docstatus != 1:
		return
	doc.flags.coordinated_fx_lifecycle = True
	doc.cancel()


def _delete_if_present(doc):
	if not doc or not frappe.db.exists(doc.doctype, doc.name):
		return
	frappe.delete_doc(
		doc.doctype,
		doc.name,
		flags={"coordinated_fx_lifecycle": True},
	)


def _linked_transaction_result(fx_selling, fund_transfer):
	return {
		"fx_selling": fx_selling.name if fx_selling else None,
		"fund_transfer": fund_transfer.name if fund_transfer else None,
		"cancelled": True,
	}


def refresh_and_validate_rates(doc):
	settings = frappe.get_single("FX Selling Settings")
	rates = _latest_rates(settings) if any(row.currency == "USD" for row in doc.currencies) else {}
	tracker_rows = _tracker_rows(settings) if any(row.currency != "USD" for row in doc.currencies) else []
	for row in doc.currencies:
		if row.currency == "USD":
			rate = rates.get("USD")
			if not rate:
				frappe.throw(_("No current Google rate is available for USD."))
			if row.base_rate and flt(row.base_rate) != flt(rate["base_rate"]):
				frappe.throw(_("The USD rate changed. Reload the rates and review the transaction."))
			row.base_rate = rate["base_rate"]
			row.selling_addition = rate["selling_addition"]
			row.selling_rate = rate["selling_rate"]
			row.rate_source_row = rate["source_row"]
		else:
			tracker_row = _tracker_request_row(tracker_rows, row)
			agreed_rate = flt(tracker_row[4])
			if agreed_rate <= 0:
				frappe.throw(_("Transfer Tracker request {0} has no valid agreed rate in column E.").format(row.request_no))
			row.base_rate = agreed_rate
			row.selling_addition = 0
			row.selling_rate = agreed_rate
			row.rate_source_row = row.request_source_row
		row.peso_amount = flt(row.amount) * flt(row.selling_rate)
	doc.total_peso_amount = sum(flt(row.peso_amount) for row in doc.currencies)


def _tracker_request_row(rows, item):
	index = int(item.request_source_row or 0)
	if index < 2 or index - 2 >= len(rows):
		frappe.throw(_("Transfer Tracker row for request {0} was not found.").format(item.request_no))
	row = list(rows[index - 2]) + [""] * 35
	if str(row[0]).strip() != str(item.request_no).strip() or _normalize_currency(row[2]) != _normalize_currency(item.currency):
		frappe.throw(_("Transfer Tracker request {0} changed.").format(item.request_no))
	return row


def _tracker_rows(settings, spreadsheet_id=None):
	service = _sheet_service(settings)
	sheet = _quote_sheet(settings.transfer_tracker_sheet)
	spreadsheet_id = spreadsheet_id or settings.source_spreadsheet_id
	request_numbers = service.spreadsheets().values().get(
		spreadsheetId=spreadsheet_id,
		range="{0}!A2:A".format(sheet),
		valueRenderOption="UNFORMATTED_VALUE",
	).execute().get("values", [])
	if not request_numbers:
		return []
	last_row = len(request_numbers) + 1
	return service.spreadsheets().values().get(
		spreadsheetId=spreadsheet_id or settings.source_spreadsheet_id,
		range="{0}!A2:AA{1}".format(sheet, last_row),
		valueRenderOption="UNFORMATTED_VALUE",
	).execute().get("values", [])


@frappe.whitelist()
def get_available_tracker_requests(branch=None):
	settings = frappe.get_single("FX Selling Settings")
	branch = branch or get_branch_from_request_ip()
	if not branch:
		frappe.throw(_("No branch is mapped to the current request IP."))
	if not is_system_manager(frappe.session.user) and not has_active_branch_role(frappe.session.user, branch, FX_ROLE):
		frappe.throw(_("Not permitted."), frappe.PermissionError)
	code = get_fund_transfer_branch_code(branch)
	result = []
	for index, row in enumerate(_tracker_rows(settings), start=2):
		row += [""] * (35 - len(row))
		if row[8] not in (None, "") and row[15] not in (None, "") and row[16] in (None, "") and row[26] in (None, "") and str(row[14]).strip().upper() == str(code).upper():
			result.append({"request_no": row[0], "currency": row[2], "available_amount": flt(row[10]), "request_rate": flt(row[4]), "source_row": index, "branch": row[14]})
	return result


def validate_tracker_requests(doc, settings):
	rows = _tracker_rows(settings, settings.write_spreadsheet_id)
	for item in doc.currencies:
		if item.currency == "USD":
			continue
		row = _tracker_request_row(rows, item)
		agreed_rate = flt(row[4])
		if agreed_rate <= 0:
			frappe.throw(_("Transfer Tracker request {0} has no valid agreed rate in column E.").format(item.request_no))
		if flt(item.selling_rate) != agreed_rate:
			frappe.throw(_("The agreed rate for request {0} changed. Reload the transaction and review it.").format(item.request_no))
		idempotent = row[16] not in (None, "") and str(row[17]).strip() == doc.name
		if row[16] not in (None, "") and not idempotent:
			frappe.throw(_("Transfer Tracker request {0} was already sold.").format(item.request_no))
		if not idempotent:
			branch_code = get_fund_transfer_branch_code(doc.branch)
			if row[8] in (None, "") or row[15] in (None, "") or row[26] not in (None, ""):
				frappe.throw(_("Transfer Tracker request {0} is no longer available for selling.").format(item.request_no))
			if str(row[14]).strip().upper() != str(branch_code).strip().upper():
				frappe.throw(_("Transfer Tracker request {0} belongs to another branch.").format(item.request_no))
		available = flt(row[10])
		if flt(item.amount) > available:
			frappe.throw(_("Only {0} is available for request {1}.").format(available, item.request_no))
		item.request_available_amount = available
		item.remaining_amount = available - flt(item.amount)


def sync_google_rows(doc):
	settings = frappe.get_single("FX Selling Settings")
	service = _sheet_service(settings)
	spreadsheet_id = settings.write_spreadsheet_id
	transaction_sheet = _quote_sheet(settings.transaction_sheet)
	tracker_sheet = _quote_sheet(settings.transfer_tracker_sheet)
	existing = service.spreadsheets().values().get(
		spreadsheetId=spreadsheet_id, range="{0}!A2:F".format(transaction_sheet), valueRenderOption="FORMATTED_VALUE"
	).execute().get("values", [])
	existing_keys = {(str(row[2]).strip(), _normalize_currency(row[5])) for row in existing if len(row) > 5}
	new_rows = []
	for item in doc.currencies:
		if (doc.name, _normalize_currency(item.currency)) not in existing_keys:
			new_rows.append([get_fund_transfer_branch_code(doc.branch), str(doc.business_date), doc.name, doc.customer_tracking_no, doc.customer_name, _sheet_currency(item.currency), flt(item.amount), flt(item.selling_rate), flt(item.peso_amount), doc.source_of_funds or "", doc.purpose or ""])
	if new_rows:
		service.spreadsheets().values().append(
			spreadsheetId=spreadsheet_id,
			range="{0}!A:K".format(transaction_sheet),
			valueInputOption="USER_ENTERED",
			insertDataOption="INSERT_ROWS",
			body={"values": new_rows},
		).execute()
	tracker_data = []
	for item in doc.currencies:
		if item.currency == "USD":
			continue
		row_number = int(item.request_source_row)
		values = [str(doc.business_date), doc.name, doc.customer_tracking_no, doc.customer_name, flt(item.amount), flt(item.selling_rate), flt(item.peso_amount), doc.source_of_funds or "", doc.purpose or "", flt(item.remaining_amount)]
		tracker_data.append({"range": "{0}!Q{1}:Z{1}".format(tracker_sheet, row_number), "values": [values]})
		if not flt(item.remaining_amount):
			tracker_data.append({"range": "{0}!AA{1}:AH{1}".format(tracker_sheet, row_number), "values": [["-"] * 8]})
	if tracker_data:
		service.spreadsheets().values().batchUpdate(
			spreadsheetId=spreadsheet_id,
			body={"valueInputOption": "USER_ENTERED", "data": tracker_data},
		).execute()


def _sheet_currency(currency):
	return SHEET_CURRENCY.get(currency, currency)


def _normalize_currency(currency):
	value = "".join(str(currency or "").upper().split())
	return "THAIB" if value == "THAIBAHT" else value


def get_permission_query_conditions(user=None):
	user = user or frappe.session.user
	if is_system_manager(user) or _has_read_all_role(user):
		return None
	branch = get_branch_from_request_ip()
	return "`tabFX Selling`.`branch`={0}".format(frappe.db.escape(branch)) if branch else "1=0"


def has_permission(doc, ptype=None, user=None):
	user = user or frappe.session.user
	permission_type = ptype or "read"
	if permission_type in {"cancel", "delete"}:
		return user == "Administrator"
	if is_system_manager(user):
		return True
	if permission_type in {"read", "report", "print", "email", "export"} and _has_read_all_role(user):
		return True
	branch = get_branch_from_request_ip()
	if not branch or doc.branch != branch:
		return False
	if permission_type in {"read", "report", "print", "email", "export"}:
		return has_active_branch_role(user, branch, FX_ROLE)
	if permission_type == "create":
		return has_active_branch_role(user, branch, FX_ROLE) and doc.docstatus == 0
	if permission_type in {"write", "submit"}:
		return has_active_branch_role(user, branch, FX_ROLE) and (
			doc.docstatus == 0 or _is_draft_submission(doc)
		)
	return None


def _has_read_all_role(user):
	return bool(set(frappe.get_roles(user)).intersection(READ_ALL_ROLES))


def _is_draft_submission(doc):
	"""Return whether the submitted in-memory document is still a draft in the database."""
	if doc.docstatus != 1 or not getattr(doc, "name", None):
		return False
	return frappe.db.get_value("FX Selling", doc.name, "docstatus") == 0
