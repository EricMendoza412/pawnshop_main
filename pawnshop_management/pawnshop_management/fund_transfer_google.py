from __future__ import unicode_literals

import json

import frappe
from frappe import _
from frappe.utils import cint, flt, get_datetime, getdate, now_datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build


GOOGLE_SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def get_usd_availability(branch, business_date, exclude_transfer=None):
	settings = frappe.get_single("Fund Transfer Settings")
	if not settings.enable_usd_validation:
		frappe.throw(
			_("Purchased USD validation is not configured. Enable it in Fund Transfer Settings before processing USD.")
		)

	service = _get_sheets_service(settings)
	tab = _quote_sheet(settings.fx_transaction_sheet)
	response = (
		service.spreadsheets()
		.values()
		.get(
			spreadsheetId=settings.fx_spreadsheet_id,
			range="{0}!A2:N".format(tab),
			valueRenderOption="FORMATTED_VALUE",
			dateTimeRenderOption="FORMATTED_STRING",
		)
		.execute()
	)

	purchased = 0
	target_date = getdate(business_date)
	target_branch = _normalize_text(_branch_code(branch))
	for row in response.get("values", []):
		if len(row) < 6:
			continue
		row_branch = _normalize_text(row[0])
		currency = _normalize_text(row[4]).upper()
		voided_by = row[13] if len(row) > 13 else None
		if row_branch != target_branch or currency != "USD" or voided_by:
			continue
		try:
			transaction_date = getdate(get_datetime(row[1]))
		except Exception:
			continue
		if transaction_date == target_date:
			purchased += _parse_number(row[5])

	filters = {
		"branch": branch,
		"business_date": target_date,
		"currency": "USD",
		"transfer_type": "ForEx to Vault",
		"docstatus": 1,
		"status": "Submitted",
	}
	if exclude_transfer:
		filters["name"] = ["!=", exclude_transfer]
	transferred = sum(
		flt(row.amount)
		for row in frappe.get_all("Fund Transfer", filters=filters, fields=["amount"], limit_page_length=0)
	)
	return frappe._dict(
		purchased_usd=flt(purchased),
		transferred_usd=flt(transferred),
		available_usd=flt(purchased) - flt(transferred),
	)


def queue_google_uat_sync(fund_transfer):
	settings = frappe.get_single("Fund Transfer Settings")
	if not settings.enable_google_uat_sync:
		frappe.db.set_value(
			"Fund Transfer", fund_transfer, "google_sync_status", "Disabled", update_modified=False
		)
		return

	frappe.db.set_value("Fund Transfer", fund_transfer, "google_sync_status", "Pending", update_modified=False)
	frappe.enqueue(
		"pawnshop_management.pawnshop_management.fund_transfer_google.sync_google_uat_row",
		queue="short",
		enqueue_after_commit=True,
		fund_transfer=fund_transfer,
	)


def sync_google_uat_row(fund_transfer):
	doc = frappe.get_doc("Fund Transfer", fund_transfer)
	if doc.docstatus != 1:
		return

	settings = frappe.get_single("Fund Transfer Settings")
	if not settings.enable_google_uat_sync:
		doc.db_set("google_sync_status", "Disabled", update_modified=False)
		return

	attempts = cint(doc.google_sync_attempts) + 1
	doc.db_set("google_sync_attempts", attempts, update_modified=False)
	try:
		service = _get_sheets_service(settings)
		sheet_name = settings.php_uat_sheet if doc.currency == "PHP" else settings.usd_uat_sheet
		if _uat_row_exists(service, settings.uat_spreadsheet_id, sheet_name, doc.name):
			_mark_synced(doc)
			return

		row = _build_uat_row(doc)
		(
			service.spreadsheets()
			.values()
			.append(
				spreadsheetId=settings.uat_spreadsheet_id,
				range="{0}!A:T".format(_quote_sheet(sheet_name)),
				valueInputOption="USER_ENTERED",
				insertDataOption="INSERT_ROWS",
				body={"values": [row]},
			)
			.execute()
		)
		_mark_synced(doc)
	except Exception:
		message = frappe.get_traceback()
		frappe.db.set_value(
			"Fund Transfer",
			doc.name,
			{"google_sync_status": "Failed", "google_sync_error": message[-2000:]},
			update_modified=False,
		)
		frappe.log_error(message, "Fund Transfer Google UAT Sync: {0}".format(doc.name))


@frappe.whitelist()
def retry_google_uat_sync():
	if "System Manager" not in frappe.get_roles() and frappe.session.user != "Administrator":
		frappe.throw(_("Only System Manager can retry Google UAT synchronization."), frappe.PermissionError)

	names = frappe.get_all(
		"Fund Transfer",
		filters={"docstatus": 1, "google_sync_status": ["in", ["Pending", "Failed"]]},
		pluck="name",
		limit_page_length=0,
	)
	for name in names:
		frappe.enqueue(
			"pawnshop_management.pawnshop_management.fund_transfer_google.sync_google_uat_row",
			queue="short",
			fund_transfer=name,
		)
	return len(names)


def retry_failed_google_uat_sync():
	settings = frappe.get_single("Fund Transfer Settings")
	if settings.enable_google_uat_sync:
		for name in frappe.get_all(
			"Fund Transfer",
			filters={
				"docstatus": 1,
				"google_sync_status": ["in", ["Pending", "Failed"]],
				"google_sync_attempts": ["<", 10],
			},
			pluck="name",
			limit=100,
		):
			frappe.enqueue(
				"pawnshop_management.pawnshop_management.fund_transfer_google.sync_google_uat_row",
				queue="short",
				fund_transfer=name,
			)


def _get_sheets_service(settings):
	raw_credentials = settings.get_password("google_service_account_json")
	if not raw_credentials:
		frappe.throw(_("Google Service Account credentials are not configured."))
	try:
		info = json.loads(raw_credentials)
		credentials = service_account.Credentials.from_service_account_info(info, scopes=GOOGLE_SCOPES)
	except Exception:
		frappe.throw(_("Google Service Account credentials are invalid."))
	return build("sheets", "v4", credentials=credentials, cache_discovery=False)


def _uat_row_exists(service, spreadsheet_id, sheet_name, transfer_id):
	response = (
		service.spreadsheets()
		.values()
		.get(
			spreadsheetId=spreadsheet_id,
			range="{0}!C4:C".format(_quote_sheet(sheet_name)),
			valueRenderOption="FORMATTED_VALUE",
		)
		.execute()
	)
	return any(row and str(row[0]).strip() == transfer_id for row in response.get("values", []))


def _build_uat_row(doc):
	if doc.currency == "PHP":
		row = [""] * 20
		direction_columns = {
			"Vault to Cash Manager": 3,
			"Cash Manager to Vault": 4,
			"Rover to Vault": 4,
			"Armored Van to Vault": 4,
			"Vault to Remittance": 7,
			"Remittance to Vault": 8,
			"Vault to ForEx": 9,
			"ForEx to Vault": 10,
			"Vault to Pawnshop (-NCB)": 11,
			"Pawnshop (-NCB) to Vault": 12,
		}
		balance_column, given_column, received_column, comments_column, month_column = 15, 16, 17, 18, 19
	else:
		row = [""] * 15
		direction_columns = {
			"Vault to Cash Manager": 3,
			"Cash Manager to Vault": 5,
			"Rover to Vault": 5,
			"Armored Van to Vault": 5,
			"Vault to Remittance": 6,
			"Remittance to Vault": 7,
			"Vault to ForEx": 8,
			"ForEx to Vault": 9,
		}
		balance_column, given_column, received_column, comments_column, month_column = 10, 11, 12, 13, 14

	row[0] = _branch_code(doc.branch)
	row[1] = str(doc.date_of_transfer)
	row[2] = doc.name
	direction_column = direction_columns.get(doc.transfer_type)
	if direction_column is not None:
		row[direction_column] = flt(doc.amount)
	elif doc.transfer_type == "Cash Position Adjustment":
		# The shadow report has no adjustment column; preserve the balance and explain the adjustment.
		doc.comments = "{0} CIV adjustment {1}".format(doc.currency, doc.vault_balance_change)
	row[balance_column] = flt(doc.civ_balance)
	row[given_column] = doc.given_by or ""
	row[received_column] = doc.received_by or ""
	comments = doc.comments or ""
	if doc.transfer_type in {
		"Vault to Cash Manager",
		"Cash Manager to Vault",
	}:
		transfer_note = "By {0}-Rover transfer".format(doc.initiated_by)
	elif doc.transfer_type == "Armored Van to Vault":
		transfer_note = "By {0}-Armored Van transfer".format(doc.initiated_by)
	else:
		transfer_note = None
	if transfer_note:
		comments = "{0}\n{1}".format(comments, transfer_note).strip() if comments else transfer_note
	row[comments_column] = comments
	row[month_column] = getdate(doc.business_date).strftime("%B %Y")
	return row


def _mark_synced(doc):
	frappe.db.set_value(
		"Fund Transfer",
		doc.name,
		{
			"google_sync_status": "Synced",
			"google_sync_datetime": now_datetime(),
			"google_sync_error": None,
		},
		update_modified=False,
	)


def _parse_number(value):
	if isinstance(value, (int, float)):
		return flt(value)
	return flt(str(value or "").replace(",", "").strip())


def _normalize_text(value):
	return " ".join(str(value or "").split()).strip()


def _quote_sheet(name):
	return "'{0}'".format(str(name or "").replace("'", "''"))


def _branch_code(branch):
	from pawnshop_management.pawnshop_management.doctype.fund_transfer.fund_transfer import (
		get_fund_transfer_branch_code,
	)

	return get_fund_transfer_branch_code(branch) or branch
