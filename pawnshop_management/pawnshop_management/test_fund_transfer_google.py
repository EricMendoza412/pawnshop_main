import unittest
from unittest.mock import MagicMock, patch

import frappe

from pawnshop_management.pawnshop_management.fund_transfer_google import (
	_build_uat_row,
	get_usd_availability,
	_normalize_text,
	_parse_number,
)


class TestFundTransferGoogle(unittest.TestCase):
	def test_number_and_text_normalization(self):
		self.assertEqual(_parse_number("1,250.50"), 1250.5)
		self.assertEqual(_normalize_text(" USD   "), "USD")

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
