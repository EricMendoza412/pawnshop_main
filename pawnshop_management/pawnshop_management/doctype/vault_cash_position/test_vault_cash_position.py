# Copyright (c) 2026, Rabie Santillan and Eric Mendoza and Contributors
# See license.txt

import unittest

from unittest.mock import patch

import frappe

from pawnshop_management.pawnshop_management.doctype.fund_transfer.fund_transfer import request_approval
from pawnshop_management.pawnshop_management.doctype.vault_cash_position.vault_cash_position import (
	PHP_DENOMINATIONS,
	USD_DENOMINATIONS,
	approve_reconciliation,
	get_permission_query_conditions,
	has_permission,
)


TEST_BRANCH = "TEST"


class TestVaultCashPosition(unittest.TestCase):
	@patch(
		"pawnshop_management.pawnshop_management.doctype.vault_cash_position.vault_cash_position.is_system_manager",
		return_value=False,
	)
	def test_read_all_roles_can_read_all_branches_without_list_filter(self, _is_system_manager):
		doc = frappe._dict(branch="OTHER BRANCH")
		for role in ("Accounting Analyst", "Auditor", "Operations Manager", "Settlement Member"):
			user = "{0}@example.com".format(role.lower().replace(" ", "."))
			with self.subTest(role=role), patch(
				"pawnshop_management.pawnshop_management.doctype.vault_cash_position.vault_cash_position.frappe.get_roles",
				return_value=[role],
			):
				self.assertIsNone(get_permission_query_conditions(user))
				self.assertTrue(has_permission(doc, "read", user))
				self.assertTrue(has_permission(doc, "report", user))
				self.assertFalse(has_permission(doc, "write", user))

	def setUp(self):
		frappe.set_user("Administrator")
		frappe.db.set_value("Branch", TEST_BRANCH, "vault_custodian", "Administrator", update_modified=False)
		frappe.db.set_value(
			"Fund Transfer Settings",
			"Fund Transfer Settings",
			{"enable_usd_validation": 0, "enable_google_uat_sync": 0},
			update_modified=False,
		)

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def test_first_position_establishes_both_opening_balances(self):
		doc = self._new_position(php_counts={1000: 2}, usd_counts={100: 3})
		doc.submit()
		doc.reload()

		self.assertEqual(doc.is_opening_position, 1)
		self.assertEqual(doc.php_actual_cash, 2000)
		self.assertEqual(doc.usd_actual_cash, 300)
		self.assertEqual(doc.php_system_civ_balance, 2000)
		self.assertEqual(doc.usd_system_civ_balance, 300)
		self.assertEqual(doc.reconciliation_status, "Balanced")

	@patch(
		"pawnshop_management.pawnshop_management.doctype.vault_cash_position.vault_cash_position.is_system_manager",
		return_value=False,
	)
	def test_registered_custodian_can_submit_draft(self, _is_system_manager):
		custodian = "custodian@example.com"
		doc = frappe._dict(doctype="Vault Cash Position", name="VCP-TEST", branch=TEST_BRANCH, docstatus=1)
		stored_docstatus = {"value": 0}

		def get_value(doctype, name, fieldname):
			if doctype == "Branch":
				return custodian
			if doctype == "Vault Cash Position":
				return stored_docstatus["value"]

		with patch.object(frappe.db, "get_value", side_effect=get_value):
			self.assertTrue(has_permission(doc, "write", custodian))
			self.assertTrue(has_permission(doc, "submit", custodian))

			stored_docstatus["value"] = 1
			self.assertFalse(has_permission(doc, "write", custodian))
			self.assertFalse(has_permission(doc, "submit", custodian))

	def test_variance_does_not_block_transfer_and_reconciliation_adjusts_current_civ(self):
		incoming = frappe.new_doc("Fund Transfer")
		incoming.update(
			{
				"branch": TEST_BRANCH,
				"currency": "PHP",
				"transfer_type": "Armored Van to Vault",
				"amount": 1000,
			}
		)
		incoming.insert()
		request_approval(incoming.name)

		position = self._new_position(php_counts={1000: 1, 100: -0}, usd_counts={})
		# Declare a PHP 100 shortage while preserving a complete denomination table.
		for row in position.php_denominations:
			row.amount = 0
			if row.denomination == 500:
				row.amount = 500
			if row.denomination == 200:
				row.amount = 400
		position.save()
		position.submit()
		position.reload()
		self.assertEqual(position.php_system_civ_balance, 1000)
		self.assertEqual(position.php_actual_cash, 900)
		self.assertEqual(position.php_variance, -100)
		self.assertEqual(position.reconciliation_status, "Pending Accounting Review")

		# A real transfer can continue before Accounting approval.
		second = frappe.new_doc("Fund Transfer")
		second.update(
			{
				"branch": TEST_BRANCH,
				"currency": "PHP",
				"transfer_type": "Armored Van to Vault",
				"amount": 200,
			}
		)
		second.insert()
		request_approval(second.name)
		second.reload()
		self.assertEqual(second.civ_balance, 1200)

		approve_reconciliation(position.name, "Approved test shortage")
		position.reload()
		self.assertEqual(position.reconciliation_status, "Reconciled")
		self.assertTrue(position.php_adjustment_fund_transfer)
		adjustment = frappe.get_doc("Fund Transfer", position.php_adjustment_fund_transfer)
		self.assertEqual(adjustment.vault_balance_change, -100)
		self.assertEqual(adjustment.opening_civ_balance, 1200)
		self.assertEqual(adjustment.civ_balance, 1100)

	def _new_position(self, php_counts, usd_counts):
		doc = frappe.new_doc("Vault Cash Position")
		doc.branch = TEST_BRANCH
		for denomination in PHP_DENOMINATIONS:
			doc.append(
				"php_denominations",
				{"denomination": denomination, "amount": denomination * php_counts.get(denomination, 0)},
			)
		for denomination in USD_DENOMINATIONS:
			doc.append(
				"usd_denominations",
				{"denomination": denomination, "amount": denomination * usd_counts.get(denomination, 0)},
			)
		doc.insert()
		return doc
