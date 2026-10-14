# Copyright (c) 2022, Rabie Moses Santillan and Contributors
# See license.txt

import unittest
from unittest.mock import Mock, patch

import frappe

from pawnshop_management.pawnshop_management.doctype.cash_position_report.cash_position_report import (
	CashPositionReport,
	CPR_BRANCH_NOT_FOUND_MESSAGE,
	CPR_CASHIER_NOT_ASSIGNED_MESSAGE,
	CPR_CREATE_RESTRICTED_MESSAGE,
	_get_cash_position_report_create_access,
	_get_inventory_totals,
	_get_pawnshop_fund_transfer_totals,
)


class TestCashPositionReport(unittest.TestCase):
	@patch("frappe.new_doc")
	@patch("frappe.local.db", new_callable=Mock, create=True)
	def test_inventory_count_and_principal_include_returned_with_matching_scope(self, db, new_doc):
		tickets = []
		for doctype, series, multiplier in (
			("Pawn Ticket Jewelry", "A", 1),
			("Pawn Ticket Jewelry", "B", 10),
			("Pawn Ticket Non Jewelry", "B", 100),
		):
			for status, date, branch, principal in (
				("Active", "2026-08-05", "TEST", 100),
				("Expired", "2026-07-01", "TEST", 200),
				("Returned", "2026-07-01", "TEST", 300),
				("Returned", "2026-08-05", "TEST", 400),
				("Returned", "2026-08-06", "TEST", 500),
				("Active", "2026-08-06", "TEST", 600),
				("Expired", "2026-08-06", "TEST", 700),
				("Returned", "2026-07-01", "OTHER", 800),
				("Redeemed", "2026-07-01", "TEST", 900),
				("Renewed", "2026-07-01", "TEST", 1000),
				("Pulled Out", "2026-07-01", "TEST", 1100),
				("Rejected", "2026-07-01", "TEST", 1200),
			):
				tickets.append({
					"doctype": doctype, "item_series": series, "branch": branch,
					"workflow_state": status, "date_loan_granted": date,
					"change_status_date": date, "desired_principal": principal * multiplier,
				})

		def matches(ticket, filters):
			for field, condition in filters.items():
				value = ticket.get(field)
				if isinstance(condition, list):
					operator, expected = condition
					if operator == "in":
						if value not in expected:
							return False
					elif operator == "<=":
						if value > expected:
							return False
					else:
						self.fail("Unexpected filter operator: " + operator)
				elif value != condition:
					return False
			return True

		def selected(doctype, filters):
			return [row for row in tickets if row["doctype"] == doctype and matches(row, filters)]

		db.count.side_effect = lambda doctype, filters: len(selected(doctype, filters))
		db.get_all.side_effect = lambda doctype, filters, fields, pluck: [
			row[pluck] for row in selected(doctype, filters)
		]
		inventory = Mock()
		new_doc.return_value = inventory
		report = frappe._dict(branch="TEST", date="2026-08-05")

		CashPositionReport.create_inventory_count_document(report)

		for suffix, multiplier in (("a", 1), ("b", 10), ("nj", 100)):
			with self.subTest(category=suffix):
				self.assertEqual(getattr(inventory, "total_" + suffix), 4)
				self.assertEqual(getattr(inventory, "principal_total" + suffix), 1000 * multiplier)
		new_doc.assert_called_once_with("Inventory Count")
		inventory.save.assert_called_once_with(ignore_permissions=True)

	@patch("frappe.local.db", new_callable=Mock, create=True)
	def test_empty_inventory_totals_are_zero(self, db):
		db.get_all.return_value = []
		self.assertEqual(_get_inventory_totals("Pawn Ticket Non Jewelry", "TEST", "2026-08-05"), (0, 0))

	@patch("frappe.db.get_value", return_value="cashier@example.com")
	def test_assigned_pawnshop_cashier_can_create_report(self, get_value):
		access = _get_cash_position_report_create_access(branch="TEST", user="cashier@example.com")

		self.assertTrue(access["allowed"])
		self.assertEqual(access["branch"], "TEST")
		get_value.assert_called_once_with("Branch", "TEST", "pawnshop_cashier")

	@patch("frappe.db.get_value", return_value="cashier@example.com")
	def test_unassigned_user_cannot_create_report(self, get_value):
		access = _get_cash_position_report_create_access(branch="TEST", user="other@example.com")

		self.assertFalse(access["allowed"])
		self.assertEqual(access["message"], CPR_CREATE_RESTRICTED_MESSAGE)

	@patch("frappe.db.get_value", return_value=None)
	def test_missing_pawnshop_cashier_blocks_report_creation(self, get_value):
		access = _get_cash_position_report_create_access(branch="TEST", user="cashier@example.com")

		self.assertFalse(access["allowed"])
		self.assertEqual(access["message"], CPR_CASHIER_NOT_ASSIGNED_MESSAGE.format("TEST"))

	@patch("frappe.db.get_value")
	def test_administrator_bypasses_pawnshop_cashier_assignment(self, get_value):
		access = _get_cash_position_report_create_access(branch="TEST", user="Administrator")

		self.assertTrue(access["allowed"])
		get_value.assert_not_called()

	@patch(
		"pawnshop_management.pawnshop_management.doctype.cash_position_report.cash_position_report.get_branch_from_request_ip",
		return_value=None,
	)
	def test_unresolved_workstation_branch_blocks_report_creation(self, get_branch):
		access = _get_cash_position_report_create_access(user="cashier@example.com")

		self.assertFalse(access["allowed"])
		self.assertEqual(access["message"], CPR_BRANCH_NOT_FOUND_MESSAGE)

	@patch("frappe.db.get_value", side_effect=["cashier@example.com", "replacement@example.com"])
	def test_cashier_reassignment_is_detected_by_a_fresh_access_check(self, get_value):
		initial_access = _get_cash_position_report_create_access(branch="TEST", user="cashier@example.com")
		after_reassignment = _get_cash_position_report_create_access(branch="TEST", user="cashier@example.com")

		self.assertTrue(initial_access["allowed"])
		self.assertFalse(after_reassignment["allowed"])
		self.assertEqual(after_reassignment["message"], CPR_CREATE_RESTRICTED_MESSAGE)

	@patch(
		"pawnshop_management.pawnshop_management.doctype.cash_position_report.cash_position_report._get_cash_position_report_create_access",
		return_value={"allowed": False, "message": CPR_CREATE_RESTRICTED_MESSAGE},
	)
	def test_before_insert_enforces_pawnshop_cashier_assignment(self, get_access):
		doc = CashPositionReport({"doctype": "Cash Position Report", "branch": "TEST"})

		with self.assertRaisesRegex(frappe.PermissionError, CPR_CREATE_RESTRICTED_MESSAGE):
			doc.before_insert()

		get_access.assert_called_once_with(branch="TEST")

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
