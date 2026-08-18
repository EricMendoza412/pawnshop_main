import unittest
from unittest.mock import MagicMock, patch

import frappe

from pawnshop_management.pawnshop_management.doctype.fx_selling.fx_selling import (
	FXSelling,
	_latest_rates,
	_round_up_rate,
	cancel_linked_transaction,
	delete_linked_transaction,
	get_available_tracker_requests,
	refresh_and_validate_rates,
	sync_google_rows,
)
from pawnshop_management.pawnshop_management.overrides.naming_series import _get_branch_series


class TestFXSelling(unittest.TestCase):
	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def test_only_privileged_users_can_pass_cancellation_guard(self):
		doc = frappe.new_doc("FX Selling")

		frappe.set_user("Administrator")
		doc.before_cancel()

		frappe.set_user("Guest")
		with self.assertRaises(frappe.ValidationError):
			doc.before_cancel()

	def test_linked_document_requires_coordinated_cancellation(self):
		doc = frappe.new_doc("FX Selling")
		doc.fund_transfer = "TEST-000001"

		frappe.set_user("Administrator")
		with self.assertRaisesRegex(frappe.ValidationError, "Cancel Linked Transaction"):
			doc.before_cancel()

		doc.flags.coordinated_fx_lifecycle = True
		doc.before_cancel()

	def test_linked_lifecycle_service_is_administrator_only(self):
		frappe.set_user("Guest")
		with self.assertRaises(frappe.PermissionError):
			cancel_linked_transaction("FX Selling", "FXS-TEST-2026-00001")

	@patch("pawnshop_management.pawnshop_management.doctype.fx_selling.fx_selling.make_autoname")
	@patch("pawnshop_management.pawnshop_management.doctype.fx_selling.fx_selling.get_fund_transfer_branch_code")
	def test_autoname_records_branch_specific_naming_series(self, get_branch_code, make_autoname):
		get_branch_code.return_value = "Test Branch"
		make_autoname.return_value = "FXS-TEST-BRANCH-2026-00001"
		doc = FXSelling({"doctype": "FX Selling", "branch": "TEST"})

		doc.autoname()

		self.assertEqual(doc.naming_series, "FXS-TEST-BRANCH-.YYYY.-.#####")
		make_autoname.assert_called_once_with(doc.naming_series)
		self.assertEqual(doc.name, "FXS-TEST-BRANCH-2026-00001")

	@patch("pawnshop_management.pawnshop_management.overrides.naming_series.get_fund_transfer_branch_code")
	@patch("pawnshop_management.pawnshop_management.overrides.naming_series.frappe.get_all")
	def test_naming_series_exposes_one_sanitized_option_per_branch(self, get_all, get_branch_code):
		get_all.return_value = ["Branch One", "Branch Two", "Duplicate Branch"]
		get_branch_code.side_effect = ["ONE", "Branch Two", "ONE"]

		self.assertEqual(
			_get_branch_series("FX Selling"),
			["FXS-BRANCH-TWO-.YYYY.-.#####", "FXS-ONE-.YYYY.-.#####"],
		)

	def test_android_rate_rounding_parity(self):
		self.assertEqual(_round_up_rate(61.12 + 0.70, 2), 61.82)
		self.assertEqual(_round_up_rate(0.378 + 0.01, 5), 0.388)
		# This preserves Android's double/ceil behavior for the legacy WON calculation.
		self.assertEqual(_round_up_rate(0.035 + 0.01, 3), 0.046)

	@patch("pawnshop_management.pawnshop_management.doctype.fx_selling.fx_selling._sheet_service")
	def test_latest_rate_is_last_nonblank_per_currency(self, service_factory):
		service = service_factory.return_value
		service.spreadsheets.return_value.values.return_value.get.return_value.execute.return_value = {
			"values": [
				["8:00", 60.0, 0.37, 69.0],
				["10:30", 61.12, "", 69.8],
				["1:30", "", 0.378, ""],
			]
		}
		settings = frappe._dict(rates_spreadsheet_id="rates", rates_sheet="All Rates")
		rates = _latest_rates(settings)
		self.assertEqual(rates["USD"]["base_rate"], 61.12)
		self.assertEqual(rates["USD"]["selling_rate"], 61.82)
		self.assertEqual(rates["USD"]["source_row"], 4)
		self.assertEqual(rates["YEN"]["base_rate"], 0.378)
		self.assertEqual(rates["YEN"]["source_row"], 5)

	@patch("pawnshop_management.pawnshop_management.doctype.fx_selling.fx_selling.frappe.get_single")
	@patch("pawnshop_management.pawnshop_management.doctype.fx_selling.fx_selling._latest_rates")
	@patch("pawnshop_management.pawnshop_management.doctype.fx_selling.fx_selling._tracker_rows")
	def test_non_usd_uses_transfer_tracker_column_e(self, tracker_rows, latest_rates, get_single):
		row = [""] * 27
		row[0], row[2], row[4] = "3-396", "EUR", 71.4
		tracker_rows.return_value = [row]
		get_single.return_value = frappe._dict()
		doc = frappe._dict(currencies=[frappe._dict(
			currency="EUR", request_no="3-396", request_source_row=2,
			amount=280, base_rate=70.4, selling_addition=1, selling_rate=71.4,
		)])

		refresh_and_validate_rates(doc)

		latest_rates.assert_not_called()
		self.assertEqual(doc.currencies[0].base_rate, 71.4)
		self.assertEqual(doc.currencies[0].selling_addition, 0)
		self.assertEqual(doc.currencies[0].selling_rate, 71.4)
		self.assertEqual(doc.total_peso_amount, 19992)

	@patch("pawnshop_management.pawnshop_management.doctype.fx_selling.fx_selling._tracker_rows")
	@patch("pawnshop_management.pawnshop_management.doctype.fx_selling.fx_selling.frappe.get_single")
	@patch("pawnshop_management.pawnshop_management.doctype.fx_selling.fx_selling.get_branch_from_request_ip")
	def test_available_tracker_request_conditions(self, get_branch, get_single, tracker_rows):
		get_branch.return_value = "TEST"
		get_single.return_value = frappe._dict()
		row = [""] * 35
		row[0], row[2], row[4], row[8], row[10], row[14], row[15] = "20-1", "YEN", 0.38, "2026-08-15", 10000, "TEST", "received"
		tracker_rows.return_value = [row]
		result = get_available_tracker_requests("TEST")
		self.assertEqual(result[0]["request_no"], "20-1")
		self.assertEqual(result[0]["source_row"], 2)
		self.assertEqual(result[0]["available_amount"], 10000)

	@patch("pawnshop_management.pawnshop_management.doctype.fx_selling.fx_selling._sheet_service")
	@patch("pawnshop_management.pawnshop_management.doctype.fx_selling.fx_selling.frappe.get_single")
	def test_google_sync_uses_erpnext_name_as_receipt(self, get_single, service_factory):
		settings = frappe._dict(
			write_spreadsheet_id="uat", transaction_sheet="Transaction Monitoring", transfer_tracker_sheet="Transfer Tracker"
		)
		get_single.return_value = settings
		service = service_factory.return_value
		service.spreadsheets.return_value.values.return_value.get.return_value.execute.return_value = {"values": []}
		append = service.spreadsheets.return_value.values.return_value.append.return_value
		append.execute.return_value = {}
		doc = frappe._dict(
			name="FXS-POB-2026-00001", branch="Garcia's Pawnshop - POB", business_date="2026-08-15",
			customer_tracking_no="3.1-123", customer_name="TEST CUSTOMER", source_of_funds="Savings",
			purpose="Allowance", currencies=[frappe._dict(currency="USD", amount=200, selling_rate=61.82, peso_amount=12364)],
		)
		sync_google_rows(doc)
		append_call = service.spreadsheets.return_value.values.return_value.append.call_args.kwargs
		self.assertEqual(append_call["range"], "'Transaction Monitoring'!A:K")
		self.assertEqual(append_call["insertDataOption"], "INSERT_ROWS")
		self.assertEqual(append_call["body"]["values"][0][2], doc.name)
		self.assertEqual(append_call["body"]["values"][0][5], "USD")
		service.spreadsheets.return_value.values.return_value.batchUpdate.assert_not_called()

	@patch("pawnshop_management.pawnshop_management.doctype.fx_selling.fx_selling._latest_rates")
	@patch("pawnshop_management.pawnshop_management.doctype.fx_selling.fx_selling._validate_customer_id")
	def test_draft_uses_erpnext_name_and_customer_snapshot(self, validate_customer_id, latest_rates):
		frappe.set_user("Administrator")
		frappe.db.set_value("FX Selling Settings", "FX Selling Settings", "enabled", 1, update_modified=False)
		latest_rates.return_value = {
			"USD": {"base_rate": 61.12, "selling_addition": 0.70, "selling_rate": 61.82, "source_row": 573}
		}
		customer = frappe.get_all("Customer", filters={"disabled": 0}, pluck="name", limit=1)
		if not customer:
			self.skipTest("No enabled Customer is available on the test site")
		doc = frappe.new_doc("FX Selling")
		doc.branch = "TEST"
		doc.customer = customer[0]
		doc.customer_id_picture = "test-id"
		doc.append("currencies", {"currency": "USD", "amount": 100})
		doc.insert()
		self.assertRegex(doc.name, r"^FXS-TEST-\d{4}-\d{5}$")
		self.assertEqual(doc.naming_series, "FXS-TEST-.YYYY.-.#####")
		self.assertEqual(doc.customer_name, frappe.db.get_value("Customer", customer[0], "customer_name"))
		self.assertEqual(doc.currencies[0].base_rate, 61.12)
		self.assertEqual(doc.currencies[0].selling_rate, 61.82)
		self.assertEqual(doc.total_peso_amount, 6182)

	@patch("pawnshop_management.pawnshop_management.doctype.fx_selling.fx_selling.sync_google_rows")
	@patch("pawnshop_management.pawnshop_management.doctype.fx_selling.fx_selling.validate_tracker_requests")
	@patch("pawnshop_management.pawnshop_management.doctype.fx_selling.fx_selling._latest_rates")
	@patch("pawnshop_management.pawnshop_management.doctype.fx_selling.fx_selling._validate_customer_id")
	def test_usd_submit_creates_linked_fund_transfer(
		self, validate_customer_id, latest_rates, validate_tracker, sync_google
	):
		from pawnshop_management.pawnshop_management.doctype.fund_transfer.fund_transfer import request_approval

		frappe.set_user("Administrator")
		frappe.db.set_value("Branch", "TEST", "vault_custodian", "Administrator", update_modified=False)
		frappe.db.set_value(
			"FX Selling Settings", "FX Selling Settings",
			{"enabled": 1, "enable_google_writes": 1, "write_spreadsheet_id": "uat"}, update_modified=False,
		)
		frappe.db.set_value(
			"Fund Transfer Settings", "Fund Transfer Settings", "enable_google_uat_sync", 0, update_modified=False
		)
		incoming = frappe.new_doc("Fund Transfer")
		incoming.branch = "TEST"
		incoming.currency = "USD"
		incoming.transfer_type = "Armored Van to Vault"
		incoming.amount = 1000
		incoming.insert()
		request_approval(incoming.name)
		customer = frappe.get_all("Customer", filters={"disabled": 0}, pluck="name", limit=1)
		if not customer:
			self.skipTest("No enabled Customer is available on the test site")
		latest_rates.return_value = {
			"USD": {"base_rate": 61.12, "selling_addition": 0.70, "selling_rate": 61.82, "source_row": 573}
		}
		doc = frappe.new_doc("FX Selling")
		doc.branch = "TEST"
		doc.customer = customer[0]
		doc.customer_id_picture = "test-id"
		doc.append("currencies", {"currency": "USD", "amount": 200, "base_rate": 61.12, "selling_addition": 0.70, "selling_rate": 61.82, "peso_amount": 12364})
		doc.insert()
		doc.submit()
		doc.reload()
		transfer = frappe.get_doc("Fund Transfer", doc.fund_transfer)
		self.assertEqual(doc.status, "Completed")
		self.assertEqual(transfer.docstatus, 1)
		self.assertEqual(frappe.get_meta("Fund Transfer").get_field("fx_selling").fieldtype, "Data")
		self.assertEqual(transfer.fx_selling, doc.name)
		self.assertEqual(transfer.vault_balance_change, -200)
		self.assertEqual(transfer.civ_balance, 800)
		self.assertEqual(transfer.given_by, "Administrator")
		self.assertEqual(transfer.received_by, doc.customer_name)
		self.assertEqual(transfer.comments, "FOREX SELLING")

		cancel_linked_transaction("Fund Transfer", transfer.name)
		doc.reload()
		transfer.reload()
		self.assertEqual(doc.docstatus, 2)
		self.assertEqual(transfer.docstatus, 2)

		delete_linked_transaction("FX Selling", doc.name)
		self.assertFalse(frappe.db.exists("FX Selling", doc.name))
		self.assertFalse(frappe.db.exists("Fund Transfer", transfer.name))
