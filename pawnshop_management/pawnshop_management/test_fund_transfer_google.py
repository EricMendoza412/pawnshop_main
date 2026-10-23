import unittest
from unittest.mock import MagicMock, patch

import frappe

from pawnshop_management.pawnshop_management.fund_transfer_google import (
	_build_uat_row,
	get_usd_availability,
	_normalize_text,
	_parse_uncollected_fx_row,
	_parse_number,
)


class TestFundTransferGoogle(unittest.TestCase):
	def test_number_and_text_normalization(self):
		self.assertEqual(_parse_number("1,250.50"), 1250.5)
		self.assertEqual(_normalize_text(" USD   "), "USD")

	def test_uncollected_fx_parser_uses_ch_and_requires_blank_a_and_c(self):
		row = [""] * 86
		row[3] = "8/7/2026 16:56:30"
		row[4] = "GTC"
		row[26] = "60.6893"
		row[85] = "3,375"
		envelope = _parse_uncollected_fx_row(row, 1443)
		self.assertEqual(envelope.cpr_date.isoformat(), "2026-08-07")
		self.assertEqual(envelope.expected_amount, 3375)
		self.assertEqual(envelope.source_row, 1443)
		row[2] = "USD-user@example.com"
		self.assertIsNone(_parse_uncollected_fx_row(row, 1443))

	def test_uncollected_fx_uses_usd_from_uncollected_column(self):
		doc = frappe._dict(
			currency="USD",
			branch="TEST",
			date_of_transfer="2026-08-07 10:06:49",
			name="4.1-8368",
			transfer_type="Uncollected FX to Vault",
			amount=3375,
			civ_balance=4081,
			given_by="Uncollected FX",
			received_by="user@example.com",
			comments="user@example.com-Uncollected FX transfer",
			business_date="2026-08-07",
		)
		row = _build_uat_row(doc)
		self.assertEqual(row[4], 3375)
		self.assertEqual(row[11], "Uncollected FX")
		self.assertEqual(row[13], "user@example.com-Uncollected FX transfer")

	def test_php_uat_row_uses_ncb_columns(self):
		doc = frappe._dict(
			currency="PHP",
			branch="TEST",
			date_of_transfer="2026-07-30 10:00:00",
			name="20-000001",
			transfer_type="Vault to Pawnshop (-NCB)",
			amount=500,
			civ_balance=1500,
			given_by="vc@example.com",
			received_by="cashier@example.com",
			comments="Test",
			business_date="2026-07-30",
		)
		row = _build_uat_row(doc)
		self.assertEqual(row[11], 500)
		self.assertEqual(row[5], "")
		self.assertEqual(row[15], 1500)

	def test_cash_manager_rows_include_vault_custodian_rover_note(self):
		for currency in ("PHP", "USD"):
			for transfer_type in ("Vault to Cash Manager", "Cash Manager to Vault"):
				with self.subTest(currency=currency, transfer_type=transfer_type):
					doc = frappe._dict(
						currency=currency,
						branch="TEST",
						date_of_transfer="2026-08-07 10:25:54",
						name="3.1-5707",
						transfer_type=transfer_type,
						amount=5000,
						civ_balance=5000,
						given_by="giver@example.com",
						received_by="receiver@example.com",
						initiated_by="gpemmacostibolo@gmail.com",
						comments="",
						business_date="2026-08-07",
					)

					row = _build_uat_row(doc)
					comments_column = 18 if currency == "PHP" else 13

					self.assertEqual(
						row[comments_column], "By gpemmacostibolo@gmail.com-Rover transfer"
					)

	def test_armored_van_rows_include_vault_custodian_note(self):
		for currency in ("PHP", "USD"):
			with self.subTest(currency=currency):
				doc = frappe._dict(
					currency=currency,
					branch="TEST",
					date_of_transfer="2026-08-07 10:25:54",
					name="3.1-5707",
					transfer_type="Armored Van to Vault",
					amount=5000,
					civ_balance=5000,
					given_by="Armored Van",
					received_by="gpjacklyndiaz@gmail.com",
					initiated_by="gpjacklyndiaz@gmail.com",
					comments="",
					business_date="2026-08-07",
				)

				row = _build_uat_row(doc)
				comments_column = 18 if currency == "PHP" else 13

				self.assertEqual(
					row[comments_column], "By gpjacklyndiaz@gmail.com-Armored Van transfer"
				)

	def test_usd_cash_manager_rover_note_preserves_existing_comments(self):
		doc = frappe._dict(
			currency="USD",
			branch="TEST",
			date_of_transfer="2026-08-07 10:25:54",
			name="3.1-5707",
			transfer_type="Vault to Cash Manager",
			amount=5000,
			civ_balance=5000,
			given_by="giver@example.com",
			received_by="receiver@example.com",
			initiated_by="vc@example.com",
			comments="Existing comment",
			business_date="2026-08-07",
		)

		row = _build_uat_row(doc)

		self.assertEqual(row[13], "Existing comment\nBy vc@example.com-Rover transfer")

	def test_fx_selling_comment_does_not_include_rover_note(self):
		doc = frappe._dict(
			currency="USD",
			branch="TEST",
			date_of_transfer="2026-08-17 23:59:21",
			name="POB-000023",
			transfer_type="Vault to Cash Manager",
			amount=400,
			civ_balance=8300,
			given_by="Administrator",
			received_by="TEST CUSTOMER",
			initiated_by="Administrator",
			comments="FOREX SELLING - FXS-POB-2026-00002",
			fx_selling="FXS-POB-2026-00002",
			business_date="2026-08-17",
		)

		row = _build_uat_row(doc)

		self.assertEqual(row[13], "FOREX SELLING")

	@patch("pawnshop_management.pawnshop_management.fund_transfer_google.frappe.get_all")
	@patch("pawnshop_management.pawnshop_management.fund_transfer_google._get_sheets_service")
	@patch("pawnshop_management.pawnshop_management.fund_transfer_google.frappe.get_single")
	def test_usd_availability_excludes_voids_and_previous_days(self, get_single, get_service, get_all):
		get_single.return_value = frappe._dict(
			enable_usd_validation=1,
			fx_transaction_sheet="Transaction Monitoring",
			fx_spreadsheet_id="spreadsheet-id",
		)
		execute = MagicMock(
			return_value={
				"values": [
					["CC", "2026-07-30 09:00:00", "1", "", " USD   ", "1,000", "", "", "", "", "", "", "", ""],
					["CC", "2026-07-30 10:00:00", "2", "", "USD", 500, "", "", "", "", "", "", "", "void user"],
					["CC", "2026-07-29 11:00:00", "3", "", "USD", 700],
					["GTC", "2026-07-30 12:00:00", "4", "", "USD", 900],
				]
			}
		)
		get_service.return_value.spreadsheets.return_value.values.return_value.get.return_value.execute = execute
		get_all.return_value = [frappe._dict(amount=250)]

		result = get_usd_availability("Garcia's Pawnshop - CC", "2026-07-30")
		self.assertEqual(result.purchased_usd, 1000)
		self.assertEqual(result.transferred_usd, 250)
		self.assertEqual(result.available_usd, 750)


class TestReconciliationGoogleExport(unittest.TestCase):
	def adjustment(self, variance=89, currency="PHP"):
		return frappe._dict(
			name="TEST-ADJUSTMENT", branch="TEST", currency=currency,
			transfer_type="Cash Position Adjustment", amount=abs(variance),
			vault_balance_change=variance, civ_balance=3552300 + variance,
			date_of_transfer="2026-10-24 10:00:00", business_date="2026-10-24",
			given_by="analyst@example.com", received_by="analyst@example.com",
			cash_position="VCP-TEST", comments="Original adjustment comment", docstatus=1,
		)

	@patch("pawnshop_management.pawnshop_management.fund_transfer_google._branch_code", return_value="TEST")
	def test_php_variance_columns_and_audit_fields(self, branch_code):
		for variance, shortage, overage in ((89, "", 89), (-89, 89, ""), (-0.25, 0.25, ""), (0, "", "")):
			with self.subTest(variance=variance):
				doc = self.adjustment(variance)
				row = _build_uat_row(doc)
				self.assertEqual(row[13:16], [shortage, overage, doc.civ_balance])
				self.assertEqual(row[3:13], [""] * 10)
				self.assertEqual(row[2], doc.name)
				self.assertEqual(row[16:18], [doc.given_by, doc.received_by])
				self.assertIn("VCP VCP-TEST", row[18])
				self.assertEqual(row[19], "October 2026")
				self.assertEqual(doc.comments, "Original adjustment comment")

	@patch("pawnshop_management.pawnshop_management.fund_transfer_google._branch_code", return_value="TEST")
	def test_usd_layout_is_preserved(self, branch_code):
		row = _build_uat_row(self.adjustment(-89, "USD"))
		self.assertEqual(len(row), 15)
		self.assertEqual(row[3:10], [""] * 7)
		self.assertEqual(row[10], 3552211)
		self.assertIn("USD CIV adjustment -89", row[13])
		self.assertEqual(row[14], "October 2026")

	def test_retry_keeps_existing_sheet_row_and_manual_values(self):
		from pawnshop_management.pawnshop_management import fund_transfer_google as google
		doc = self.adjustment()
		service = MagicMock()
		values = service.spreadsheets.return_value.values.return_value
		# First export is absent; retry finds its existing transfer ID in column C.
		values.get.return_value.execute.side_effect = [{"values": []}, {"values": [[doc.name]]}]
		settings = frappe._dict(enable_google_uat_sync=1, php_uat_sheet="PHP", uat_spreadsheet_id="test")
		with patch.object(google.frappe, "get_doc", return_value=doc), \
			patch.object(google.frappe, "get_single", return_value=settings), \
			patch.object(google, "_get_sheets_service", return_value=service), \
			patch.object(google, "_branch_code", return_value="TEST"), \
			patch.object(google, "_mark_synced") as mark_synced:
			doc.db_set = MagicMock()
			google.sync_google_uat_row(doc.name)
			google.sync_google_uat_row(doc.name)
		values.append.assert_called_once()
		row = values.append.call_args.kwargs["body"]["values"][0]
		self.assertEqual(row[13:16], ["", 89, 3552389])
		values.update.assert_not_called()
		self.assertEqual(mark_synced.call_count, 2)
