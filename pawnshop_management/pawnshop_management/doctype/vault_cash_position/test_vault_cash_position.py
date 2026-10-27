# Copyright (c) 2026, Rabie Santillan and Eric Mendoza and Contributors
# See license.txt

import unittest

from unittest.mock import patch

import frappe
from pawnshop_management.pawnshop_management.doctype.vault_cash_position.vault_cash_position import get_balance_preview

from pawnshop_management.pawnshop_management.doctype.fund_transfer.fund_transfer import request_approval
from pawnshop_management.pawnshop_management.doctype.vault_cash_position.vault_cash_position import (
	PHP_DENOMINATIONS,
	USD_DENOMINATIONS,
	_print_signature_line,
	approve_reconciliation,
	get_permission_query_conditions,
	has_permission,
)


TEST_BRANCH = "VCP-CUTOFF-TEST"


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
		frappe.get_doc({"doctype": "Branch", "branch": TEST_BRANCH}).insert(ignore_permissions=True)
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

	def test_before_print_adds_underlined_custodian_and_blank_manager_lines(self):
		doc = frappe.new_doc("Vault Cash Position")
		doc.vault_custodian = "custodian@example.com"
		doc.usd_currency = None

		with patch.object(frappe.db, "get_value", return_value="Juan Dela Cruz"):
			doc.before_print()

		self.assertIn("Juan Dela Cruz", doc.signature_over_printed_name)
		self.assertIn("border-bottom:1px solid #000", doc.signature_over_printed_name)
		self.assertIn("padding:0 28px", doc.signature_over_printed_name)
		self.assertNotIn("Juan Dela Cruz", doc.managers_spot_check)
		self.assertIn("&nbsp;", doc.managers_spot_check)
		self.assertEqual(doc.usd_currency, "USD")

	def test_before_print_formats_usd_summary_with_dollar_sign(self):
		doc = frappe.new_doc("Vault Cash Position")
		doc.usd_currency = None
		doc.usd_system_civ_balance = 1050
		doc.usd_actual_cash = 1050
		doc.usd_variance = 0

		with patch.object(frappe.db, "get_value", return_value=""):
			doc.before_print()

		for fieldname in ("usd_system_civ_balance", "usd_actual_cash", "usd_variance"):
			formatted_value = doc.get_formatted(fieldname)
			self.assertIn("$", formatted_value)
			self.assertNotIn("₱", formatted_value)

	def test_signature_line_escapes_the_printed_name(self):
		line = _print_signature_line("Custodian <One>")

		self.assertIn("Custodian &lt;One&gt;", line)
		self.assertNotIn("Custodian <One>", line)

	def test_submitted_position_blocks_transfers_but_allows_reconciliation(self):
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

		# Even while Accounting review is pending, the branch is closed.
		second = frappe.new_doc("Fund Transfer")
		second.update(
			{
				"branch": TEST_BRANCH,
				"currency": "PHP",
				"transfer_type": "Armored Van to Vault",
				"amount": 200,
			}
		)
		with self.assertRaisesRegex(frappe.ValidationError, "Fund transfers are closed"):
			second.insert()

		approve_reconciliation(position.name, "Approved test shortage")
		position.reload()
		self.assertEqual(position.reconciliation_status, "Reconciled")
		self.assertTrue(position.php_adjustment_fund_transfer)
		adjustment = frappe.get_doc("Fund Transfer", position.php_adjustment_fund_transfer)
		self.assertEqual(adjustment.vault_balance_change, -100)
		self.assertEqual(adjustment.opening_civ_balance, 1000)
		self.assertEqual(adjustment.civ_balance, 900)

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
		doc._vault_balance_snapshot = get_balance_preview(doc.branch)["token"]
		doc.insert()
		return doc

	def _receive(self, amount=100000):
		doc = frappe.get_doc({"doctype": "Fund Transfer", "branch": TEST_BRANCH,
			"currency": "PHP", "transfer_type": "Armored Van to Vault", "amount": amount})
		doc.insert()
		request_approval(doc.name)
		return doc

	def test_stale_new_report_is_not_inserted(self):
		doc = frappe.get_doc({"doctype": "Vault Cash Position", "branch": TEST_BRANCH})
		doc._vault_balance_snapshot = get_balance_preview(TEST_BRANCH)["token"]
		self._receive()
		with self.assertRaisesRegex(frappe.ValidationError, "Refresh the form"):
			doc.insert()
		self.assertFalse(frappe.db.exists("Vault Cash Position", {"branch": TEST_BRANCH}))

	def test_stale_draft_cannot_save_or_submit_until_refreshed(self):
		self._receive(1000)
		doc = self._new_position({1000: 1}, {})
		self.assertEqual(doc.php_system_civ_balance, 1000)
		self.assertEqual(doc.php_variance, 0)
		self._receive()
		doc.php_denominations[0].amount = 101000
		with self.assertRaisesRegex(frappe.ValidationError, "Refresh the form"):
			doc.save()
		token = doc._vault_balance_snapshot
		doc.reload()
		doc._vault_balance_snapshot = token
		with self.assertRaisesRegex(frappe.ValidationError, "Refresh the form"):
			doc.submit()
		stored = frappe.get_doc("Vault Cash Position", doc.name)
		self.assertEqual(stored.docstatus, 0)
		self.assertEqual(stored.php_actual_cash, 1000)
		stored._vault_balance_snapshot = get_balance_preview(TEST_BRANCH)["token"]
		stored.save()
		self.assertEqual(stored.php_variance, -100000)
		stored.submit()
		stored.reload()
		self.assertEqual(stored.reconciliation_status, "Pending Accounting Review")

	def test_missing_snapshot_rejected_even_for_administrator(self):
		doc = frappe.get_doc({"doctype": "Vault Cash Position", "branch": TEST_BRANCH})
		with self.assertRaisesRegex(frappe.ValidationError, "Refresh the form"):
			doc.insert()

	def test_draft_transfer_does_not_invalidate_preview(self):
		token = get_balance_preview(TEST_BRANCH)["token"]
		frappe.get_doc({"doctype": "Fund Transfer", "branch": TEST_BRANCH,
			"currency": "PHP", "transfer_type": "Armored Van to Vault", "amount": 1000}).insert()
		self.assertEqual(get_balance_preview(TEST_BRANCH)["token"], token)

	def test_same_balance_new_transfer_invalidates_preview(self):
		incoming = self._receive(1000)
		token = get_balance_preview(TEST_BRANCH)["token"]
		# A distinct committed ledger entry must be noticed even if its closing balance matches.
		copy = frappe.copy_doc(incoming)
		copy.name = "VCP-SAME-BALANCE-TEST"
		copy.fund_transfer_series = copy.name
		copy.docstatus = 1
		copy.status = "Submitted"
		copy.db_insert()
		self.assertNotEqual(get_balance_preview(TEST_BRANCH)["token"], token)

	def test_preview_token_survives_api_payload_and_is_not_persisted(self):
		doc = frappe.get_doc({"doctype": "Vault Cash Position", "branch": TEST_BRANCH,
			"_vault_balance_snapshot": get_balance_preview(TEST_BRANCH)["token"]})
		doc.insert()
		self.assertIsNone(frappe.get_doc("Vault Cash Position", doc.name).get("_vault_balance_snapshot"))

	def test_submission_rechecks_snapshot_after_validation(self):
		doc = self._new_position({}, {})
		doc.validate()
		self._receive()
		with self.assertRaisesRegex(frappe.ValidationError, "Refresh the form"):
			doc.before_submit()

	def test_preview_requires_current_vault_custodian(self):
		frappe.set_user("Guest")
		with patch("pawnshop_management.pawnshop_management.doctype.fund_transfer.fund_transfer.is_system_manager", return_value=False):
			frappe.db.set_value("Branch", TEST_BRANCH, "vault_custodian", "another@example.com")
			with self.assertRaises(frappe.PermissionError):
				get_balance_preview(TEST_BRANCH)

	def test_cancelled_workflow_state_and_amendment(self):
		from pawnshop_management.pawnshop_management.patches.v1_0.fix_vault_cash_position_cancelled_state import execute
		from frappe.model.workflow import apply_workflow
		execute()
		doc = self._new_position({1000: 1}, {})
		doc.submit()
		doc.reload()
		doc.cancel()
		doc.reload()
		self.assertEqual(doc.docstatus, 2)
		self.assertEqual(doc.workflow_state, "Cancelled")
		self.assertEqual(doc.reconciliation_status, "Balanced")
		amended = frappe.copy_doc(doc)
		amended.docstatus = 0
		amended._vault_balance_snapshot = get_balance_preview(TEST_BRANCH)["token"]
		amended.insert()
		self.assertEqual(amended.workflow_state, "Draft")
		amended.submit()
		amended.reload()
		apply_workflow(amended, "Cancel")
		amended.reload()
		self.assertEqual(amended.workflow_state, "Cancelled")
		self.assertEqual(amended.docstatus, 2)

	def test_cancelled_state_migration_is_scoped_and_repeatable(self):
		from pawnshop_management.pawnshop_management.patches.v1_0.fix_vault_cash_position_cancelled_state import execute
		execute()
		doc = self._new_position({1000: 1}, {})
		doc.submit()
		doc.reload()
		doc.cancel()
		frappe.db.set_value("Vault Cash Position", doc.name, "workflow_state", "Submitted", update_modified=False)
		before = frappe.get_doc("Vault Cash Position", doc.name).as_dict()
		execute()
		execute()
		after = frappe.get_doc("Vault Cash Position", doc.name).as_dict()
		self.assertEqual(after.pop("workflow_state"), "Cancelled")
		before.pop("workflow_state")
		self.assertEqual(before, after)
		workflow = frappe.get_doc("Workflow", "Vault Cash Position status")
		self.assertEqual(sum(row.state == "Cancelled" for row in workflow.states), 1)
		self.assertEqual(sum(row.action == "Cancel" and row.next_state == "Cancelled" for row in workflow.transitions), 1)

	def test_branch_assignment_context_and_admin_bypass(self):
		from pawnshop_management.pawnshop_management.doctype.vault_cash_position.vault_cash_position import get_creation_context, require_vcp_branch
		self.assertTrue(get_creation_context()["administrator"])
		self.assertEqual(require_vcp_branch("OTHER"), "OTHER")
		frappe.set_user("Guest")
		self.assertFalse(get_creation_context()["allowed"])
		with self.assertRaises(frappe.PermissionError):
			require_vcp_branch(TEST_BRANCH)
		frappe.db.set_value("Branch", TEST_BRANCH, "vault_custodian", "Guest")
		self.assertEqual(get_creation_context()["branch"], TEST_BRANCH)
		self.assertEqual(require_vcp_branch(None), TEST_BRANCH)
		with self.assertRaises(frappe.PermissionError):
			require_vcp_branch("OTHER")
		frappe.set_user("Administrator")
		frappe.get_doc({"doctype": "Branch", "branch": "VCP-SECOND-TEST"}).insert(ignore_permissions=True)
		frappe.db.set_value("Branch", "VCP-SECOND-TEST", "vault_custodian", "Guest")
		frappe.set_user("Guest")
		self.assertIn("multiple branches", get_creation_context()["message"])
		with self.assertRaisesRegex(frappe.PermissionError, "multiple branches"):
			require_vcp_branch(TEST_BRANCH)

	def test_assignment_is_enforced_even_with_system_manager_role(self):
		from pawnshop_management.pawnshop_management.doctype.vault_cash_position.vault_cash_position import require_vcp_branch
		frappe.set_user("Guest")
		with patch("pawnshop_management.pawnshop_management.doctype.vault_cash_position.vault_cash_position.is_system_manager", return_value=True):
			with self.assertRaises(frappe.PermissionError):
				require_vcp_branch(TEST_BRANCH)

	def test_assignment_change_blocks_existing_draft_and_preserves_branch(self):
		doc = self._new_position({}, {})
		frappe.db.set_value("Branch", TEST_BRANCH, "vault_custodian", "Guest")
		frappe.set_user("Guest")
		doc.validate()
		frappe.db.set_value("Branch", TEST_BRANCH, "vault_custodian", "Administrator")
		with self.assertRaises(frappe.PermissionError):
			doc.validate()
		with self.assertRaises(frappe.PermissionError):
			doc.before_submit()
		self.assertEqual(doc.branch, TEST_BRANCH)

	def test_amendment_cannot_switch_branch_even_for_administrator(self):
		doc = self._new_position({}, {})
		amended = frappe.get_doc({"doctype": "Vault Cash Position", "branch": "OTHER", "amended_from": doc.name})
		with self.assertRaisesRegex(frappe.ValidationError, "retain the original branch"):
			amended.before_insert()
