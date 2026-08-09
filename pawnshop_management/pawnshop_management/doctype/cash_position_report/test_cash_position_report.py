# Copyright (c) 2022, Rabie Moses Santillan and Contributors
# See license.txt

import unittest
from unittest.mock import patch

import frappe

from pawnshop_management.pawnshop_management.doctype.cash_position_report.cash_position_report import (
	CashPositionReport,
	_get_pawnshop_fund_transfer_totals,
)


class TestCashPositionReport(unittest.TestCase):
	@patch("frappe.db.sql")
	def test_fund_transfer_totals_are_returned_in_report_direction(self, sql):
		sql.return_value = [{"cash_from_vault": 125, "cash_to_vault": 75}]

		totals = _get_pawnshop_fund_transfer_totals("TEST", "2026-08-05")

		self.assertEqual(totals.cash_from_vault, 125)
		self.assertEqual(totals.cash_to_vault, 75)
		query, values = sql.call_args.args[:2]
		self.assertIn("business_date = %(report_date)s", query)
		self.assertIn("docstatus = 1", query)
		self.assertIn("status = 'Submitted'", query)
		self.assertEqual(values, {"branch": "TEST", "report_date": "2026-08-05"})

	@patch(
		"pawnshop_management.pawnshop_management.doctype.cash_position_report.cash_position_report._get_pawnshop_fund_transfer_totals"
	)
	def test_stale_fund_transfer_totals_block_report_save(self, get_totals):
		get_totals.return_value = frappe._dict(cash_from_vault=125, cash_to_vault=75)
		doc = CashPositionReport(
			{
				"doctype": "Cash Position Report",
				"branch": "TEST",
				"date": "2026-08-05",
				"cash_from_vault": 100,
				"cash_to_vault": 75,
			}
		)

		with self.assertRaisesRegex(frappe.ValidationError, "Fund Transfers changed"):
			doc.validate_pawnshop_fund_transfer_totals()
