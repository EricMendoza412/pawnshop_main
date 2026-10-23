# Copyright (c) 2026, Rabie Santillan and Eric Mendoza and Contributors
# See license.txt

import unittest
from unittest.mock import patch

import frappe
from frappe.model.workflow import apply_workflow
from frappe.utils import today
from frappe.utils.password import update_password

from pawnshop_management.pawnshop_management.doctype.fund_transfer.fund_transfer import (
	TRANSFER_RULES,
	_confirmation_rate_limit_key,
	approve_cashier_transfer,
	confirm_rover_transfer,
	get_entry_context,
	get_permission_query_conditions,
	has_permission,
	request_approval,
)
from pawnshop_management.pawnshop_management.fund_transfer_google import _build_uat_row
from pawnshop_management.pawnshop_management.doctype.cash_position_report.cash_position_report import (
	_get_pawnshop_fund_transfer_totals,
)


TEST_BRANCH = "FT-DIRECT-TEST"
PASSWORD = "Direct-Transfer-Test-Password-2026"
MODULE = "pawnshop_management.pawnshop_management.doctype.fund_transfer.fund_transfer"


class TestFundTransfer(unittest.TestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		from pawnshop_management.pawnshop_management.patches.v1_0.create_fund_transfer_workflow import ensure_workflow
		ensure_workflow()
		self.vc = self._create_user("ft.direct.vc@example.com")
		self.cashier = self._create_user("ft.direct.cashier@example.com")
		self.other = self._create_user("ft.direct.other@example.com")
		self.rover = self._create_user("ft.direct.rover@example.com", ["Rover"])
		frappe.get_doc({"doctype": "Branch", "branch": TEST_BRANCH,
			"vault_custodian": self.vc, "pawnshop_cashier": self.cashier,
			"remittance_cashier": self.cashier, "fx_cashier": self.cashier}).insert(ignore_permissions=True)
		self.branch_patch = patch(MODULE + ".get_branch_from_request_ip", return_value=TEST_BRANCH)
		self.branch_patch.start()
		frappe.db.set_value("Fund Transfer Settings", "Fund Transfer Settings",
			{"enable_usd_validation": 0, "enable_google_uat_sync": 0}, update_modified=False)
		for user in (self.vc, self.cashier, self.rover, self.other):
			frappe.cache().delete_value(_confirmation_rate_limit_key(user))
		frappe.set_user(self.vc)

	def tearDown(self):
		self.branch_patch.stop()
		frappe.set_user("Administrator")
		for user in (self.vc, self.cashier, self.rover, self.other):
			frappe.cache().delete_value(_confirmation_rate_limit_key(user))
		frappe.db.rollback()

	def _create_user(self, email, roles=None):
		user = frappe.get_doc({"doctype": "User", "email": email, "first_name": "FT Test",
			"send_welcome_email": 0, "user_type": "System User",
			"roles": [{"role": r} for r in (roles or ["Employee"])]})
		user.insert(ignore_permissions=True)
		update_password(user.name, PASSWORD)
		return user.name

	def _new_transfer(self, transfer_type, amount=100, currency="PHP", **values):
		doc = frappe.get_doc({"doctype": "Fund Transfer", "branch": TEST_BRANCH,
			"currency": currency, "transfer_type": transfer_type, "amount": amount, **values})
		doc.insert()
		return doc

	def _submit(self, doc, password=PASSWORD):
		doc.confirmation_password = password
		apply_workflow(doc, "Submit")
		doc.reload()
		return doc

	def _fund_vault(self, currency="PHP"):
		frappe.set_user(self.vc)
		doc = self._new_transfer("Armored Van to Vault", 1000, currency)
		request_approval(doc.name)
		return doc

	@patch("pawnshop_management.pawnshop_management.fund_transfer_google.get_usd_availability")
	def test_all_cashier_directions_submit_directly_with_correct_participants_and_exports(self, availability):
		availability.return_value = frappe._dict(purchased_usd=10000, transferred_usd=0, available_usd=10000)
		for transfer_type, rule in TRANSFER_RULES.items():
			if not rule.get("authorizer_field"):
				continue
			for currency in sorted(rule["currencies"]):
				with self.subTest(transfer_type=transfer_type, currency=currency):
					self._fund_vault(currency)
					inbound = rule["destination"] == "Vault"
					initiator, confirmer = (self.cashier, self.vc) if inbound else (self.vc, self.cashier)
					frappe.set_user(initiator)
					doc = self._new_transfer(transfer_type, 100, currency)
					self.assertEqual(doc.expected_authorizer, confirmer)
					self.assertTrue(doc.has_permission("submit"))
					self._submit(doc)
					self.assertEqual((doc.status, doc.docstatus), ("Submitted", 1))
					self.assertEqual((doc.initiated_by, doc.authorized_by), (initiator, confirmer))
					self.assertEqual((doc.given_by, doc.received_by), (initiator, confirmer))
					self.assertEqual(doc.vault_balance_change, 100 * rule["impact"])
					self.assertEqual(doc.civ_balance, doc.opening_civ_balance + doc.vault_balance_change)
					self.assertEqual(doc.get(rule["legacy_field"]), 100)
					row = _build_uat_row(doc)
					given, received = (16, 17) if currency == "PHP" else (11, 12)
					self.assertEqual((row[given], row[received]), (initiator, confirmer))
					self.assertFalse(doc.confirmation_password)
					self.assertFalse(frappe.db.sql("select name from __Auth where doctype='Fund Transfer' and name=%s", doc.name))

	def test_pawnshop_report_counts_only_submitted_amounts_once(self):
		self._fund_vault()
		outgoing = self._new_transfer("Vault to Pawnshop (-NCB)", 250)
		self._submit(outgoing)
		frappe.set_user(self.cashier)
		incoming = self._new_transfer("Pawnshop (-NCB) to Vault", 100)
		before = _get_pawnshop_fund_transfer_totals(TEST_BRANCH, today())
		self.assertEqual((before.cash_from_vault, before.cash_to_vault), (250, 0))
		self._submit(incoming)
		after = _get_pawnshop_fund_transfer_totals(TEST_BRANCH, today())
		self.assertEqual((after.cash_from_vault, after.cash_to_vault), (250, 100))
		self.assertEqual(incoming.civ_balance, 850)

	def test_cashier_can_only_create_assigned_outgoing_types(self):
		frappe.set_user("Administrator")
		frappe.db.set_value("Branch", TEST_BRANCH, {"remittance_cashier": self.other, "fx_cashier": self.other})
		frappe.set_user(self.cashier)
		self.assertTrue(has_permission(frappe._dict(), "create", self.cashier))
		context = get_entry_context(TEST_BRANCH, "PHP")
		self.assertEqual([t["transfer_type"] for t in context["transfers"]], ["Pawnshop (-NCB) to Vault"])
		self._new_transfer("Pawnshop (-NCB) to Vault")
		for transfer_type in ("Vault to Pawnshop (-NCB)", "Remittance to Vault", "ForEx to Vault", "Rover to Vault", "Armored Van to Vault"):
			with self.subTest(transfer_type=transfer_type), self.assertRaises(frappe.PermissionError):
				self._new_transfer(transfer_type)

	def test_cross_branch_and_unassigned_creation_are_denied(self):
		frappe.set_user(self.cashier)
		with self.assertRaises(frappe.PermissionError):
			self._new_transfer("Pawnshop (-NCB) to Vault", branch="TEST")
		frappe.set_user(self.other)
		self.assertFalse(has_permission(frappe._dict(), "create", self.other))
		with self.assertRaises(frappe.PermissionError):
			self._new_transfer("Pawnshop (-NCB) to Vault")

	def test_wrong_missing_disabled_and_self_confirmation_are_denied(self):
		frappe.set_user(self.cashier)
		doc = self._new_transfer("Pawnshop (-NCB) to Vault")
		for password in (None, "incorrect"):
			with self.assertRaises(frappe.AuthenticationError):
				self._submit(doc, password)
			doc.reload()
			self.assertEqual((doc.status, doc.docstatus), ("Draft", 0))
		frappe.db.set_value("User", self.vc, "enabled", 0)
		with self.assertRaises(frappe.PermissionError):
			self._submit(doc)
		doc.reload()
		frappe.db.set_value("User", self.vc, "enabled", 1)
		frappe.db.set_value("Branch", TEST_BRANCH, "vault_custodian", self.cashier)
		with self.assertRaisesRegex(frappe.PermissionError, "cannot confirm their own"):
			self._submit(doc)

	def test_confirmation_is_rate_limited(self):
		frappe.set_user(self.cashier)
		doc = self._new_transfer("Pawnshop (-NCB) to Vault")
		for _ in range(5):
			with self.assertRaises(frappe.AuthenticationError):
				self._submit(doc, "incorrect")
			doc.reload()
		with self.assertRaisesRegex(frappe.AuthenticationError, "locked"):
			self._submit(doc)

	def test_missing_confirmer_stays_draft(self):
		frappe.db.set_value("Branch", TEST_BRANCH, "pawnshop_cashier", None)
		doc = self._new_transfer("Vault to Pawnshop (-NCB)")
		with self.assertRaisesRegex(frappe.ValidationError, "No Pawnshop Cashier is assigned"):
			self._submit(doc)
		doc.reload()
		self.assertEqual(doc.status, "Draft")

	def test_assignment_changes_recheck_both_participants(self):
		frappe.set_user(self.cashier)
		doc = self._new_transfer("Pawnshop (-NCB) to Vault")
		frappe.db.set_value("Branch", TEST_BRANCH, "vault_custodian", self.other)
		# A distinct password proves we verify the new assignment, not the stale field.
		update_password(self.other, "Replacement-VC-Password")
		with self.assertRaises(frappe.AuthenticationError):
			self._submit(doc)
		doc.reload()
		frappe.db.set_value("Branch", TEST_BRANCH, "pawnshop_cashier", self.other)
		with self.assertRaises(frappe.PermissionError):
			self._submit(doc, "Replacement-VC-Password")
		frappe.set_user(self.other)
		doc.reload()
		with self.assertRaises(frappe.PermissionError):
			doc.save()

	def test_initiator_cannot_be_forged_or_changed(self):
		frappe.set_user(self.cashier)
		doc = self._new_transfer("Pawnshop (-NCB) to Vault", initiated_by=self.vc)
		self.assertEqual(doc.initiated_by, self.cashier)
		doc.initiated_by = self.vc
		with self.assertRaises(frappe.PermissionError):
			doc.save()

	def test_password_is_not_saved_on_draft_and_authorization_cannot_be_forged(self):
		frappe.set_user(self.cashier)
		doc = self._new_transfer("Pawnshop (-NCB) to Vault", confirmation_password=PASSWORD, rover_password=PASSWORD)
		self.assertFalse(doc.confirmation_password)
		self.assertFalse(doc.rover_password)
		doc.authorized_by = self.vc
		with self.assertRaises(frappe.AuthenticationError):
			doc.submit()
		doc.reload()
		self.assertEqual(doc.docstatus, 0)

	def test_insufficient_balance_does_not_submit(self):
		doc = self._new_transfer("Vault to Pawnshop (-NCB)", 500)
		with self.assertRaisesRegex(frappe.ValidationError, "Insufficient"):
			self._submit(doc)
		doc.reload()
		self.assertEqual(doc.docstatus, 0)

	def test_rover_direct_submission_in_both_directions(self):
		self._fund_vault()
		for transfer_type in ("Rover to Vault", "Vault to Cash Manager"):
			doc = self._new_transfer(transfer_type, 125)
			doc.rover = self.rover
			doc.rover_password = PASSWORD
			apply_workflow(doc, "Submit")
			doc.reload()
			self.assertEqual(doc.authorized_by, self.rover)
			self.assertFalse(doc.rover_password)
			if transfer_type == "Rover to Vault":
				self.assertEqual((doc.given_by, doc.received_by), (self.rover, self.vc))
			else:
				self.assertEqual((doc.given_by, doc.received_by), (self.vc, self.rover))

	def test_legacy_approval_methods_cannot_bypass_confirmation(self):
		doc = self._new_transfer("Vault to Pawnshop (-NCB)")
		for action in (lambda: request_approval(doc.name), lambda: approve_cashier_transfer(doc.name),
			lambda: confirm_rover_transfer(doc.name, self.rover, PASSWORD)):
			with self.assertRaises(frappe.ValidationError):
				action()
		doc.reload()
		self.assertEqual(doc.status, "Draft")

	def test_retired_type_cannot_be_created_even_by_administrator(self):
		frappe.set_user("Administrator")
		with self.assertRaisesRegex(frappe.ValidationError, "retired"):
			self._new_transfer("Cash Manager to Vault")

	def test_currency_matrix_is_enforced(self):
		with self.assertRaises(frappe.ValidationError):
			self._new_transfer("Vault to Pawnshop (-NCB)", currency="USD")

	@patch("pawnshop_management.pawnshop_management.fund_transfer_google.validate_uncollected_fx_envelope")
	def test_uncollected_fx_preserves_validation_and_identity(self, validate_envelope):
		validate_envelope.return_value = frappe._dict(source_row=1450, rate=60, expected_amount=100)
		for amount in (100.5, 101):
			with self.assertRaises(frappe.ValidationError):
				self._new_transfer("Uncollected FX to Vault", amount, "USD", fx_cpr_date=today(), fx_expected_amount=100)
		doc = self._new_transfer("Uncollected FX to Vault", 75, "USD", fx_cpr_date=today(), fx_expected_amount=100)
		apply_workflow(doc, "Submit")
		doc.reload()
		self.assertEqual((doc.given_by, doc.received_by), ("Uncollected FX", self.vc))
		self.assertEqual((doc.vault_balance_change, doc.fx_difference_amount), (75, 25))

	def test_submitted_transfer_is_immutable_and_cannot_be_resubmitted(self):
		frappe.set_user(self.cashier)
		doc = self._new_transfer("Pawnshop (-NCB) to Vault")
		self._submit(doc)
		self.assertFalse(has_permission(doc, "write", self.cashier))
		self.assertFalse(has_permission(doc, "submit", self.cashier))
		doc.amount = 999
		with self.assertRaises(frappe.PermissionError):
			doc.save()


	def test_system_adjustment_preserves_internal_authorization(self):
		from pawnshop_management.pawnshop_management.doctype.fund_transfer.fund_transfer import create_cash_position_adjustment
		self._fund_vault()
		frappe.set_user("Administrator")
		# Use an actual linked document so link validation is exercised.
		position = frappe.get_doc({"doctype": "Vault Cash Position", "branch": TEST_BRANCH})
		position.insert(ignore_permissions=True)
		for row in position.php_denominations:
			row.amount = 900 if row.denomination == 100 else 0
		position.save()
		position.submit()
		name = create_cash_position_adjustment(position, "PHP", -100)
		doc = frappe.get_doc("Fund Transfer", name)
		self.assertEqual((doc.docstatus, doc.status, doc.civ_balance), (1, "Submitted", 900))

	def test_api_flags_cannot_forge_internal_authorization(self):
		frappe.set_user(self.cashier)
		doc = self._new_transfer("Pawnshop (-NCB) to Vault")
		payload = doc.as_dict()
		payload["flags"] = {"authorized_submission": True, "fx_selling_submission": True, "system_adjustment": True}
		payload["authorized_by"] = self.vc
		with self.assertRaises(frappe.AuthenticationError):
			apply_workflow(payload, "Submit")

	def test_usd_availability_still_blocks_unfunded_forex_receipts(self):
		frappe.set_user(self.cashier)
		doc = self._new_transfer("ForEx to Vault", 100, "USD")
		with patch("pawnshop_management.pawnshop_management.fund_transfer_google.get_usd_availability",
			return_value=frappe._dict(purchased_usd=50, transferred_usd=0, available_usd=50)):
			with self.assertRaisesRegex(frappe.ValidationError, "Insufficient purchased USD"):
				self._submit(doc)
		doc.reload()
		self.assertEqual(doc.docstatus, 0)

	def test_draft_can_be_cancelled_and_submitted_transfer_cancel_requires_administrator(self):
		from pawnshop_management.pawnshop_management.doctype.fund_transfer.fund_transfer import cancel_pending_transfer
		frappe.set_user(self.cashier)
		draft = self._new_transfer("Pawnshop (-NCB) to Vault")
		cancel_pending_transfer(draft.name)
		draft.reload()
		self.assertEqual(draft.status, "Cancelled")
		doc = self._new_transfer("Pawnshop (-NCB) to Vault")
		self._submit(doc)
		with self.assertRaises(frappe.PermissionError):
			doc.cancel()
		frappe.set_user("Administrator")
		doc.reload()
		doc.cancel()
		self.assertEqual(doc.docstatus, 2)

	def _close_vault(self, amount=0):
		frappe.set_user(self.vc)
		position = frappe.get_doc({"doctype": "Vault Cash Position", "branch": TEST_BRANCH})
		position.insert()
		for row in position.php_denominations:
			row.amount = amount if row.denomination == 100 else 0
		position.save()
		position.submit()
		return position

	def test_vcp_closes_all_currencies_and_blocks_admin_and_old_drafts(self):
		self._fund_vault()
		cashier_draft = None
		frappe.set_user(self.cashier)
		cashier_draft = self._new_transfer("Pawnshop (-NCB) to Vault")
		frappe.set_user(self.vc)
		rover_draft = self._new_transfer("Rover to Vault")
		position = self._close_vault(900)
		self.assertEqual(position.reconciliation_status, "Pending Accounting Review")
		for user, transfer_type in ((self.cashier, "Remittance to Vault"), (self.vc, "Armored Van to Vault"), ("Administrator", "Armored Van to Vault")):
			frappe.set_user(user)
			for currency in ("PHP", "USD"):
				with self.subTest(user=user, currency=currency), self.assertRaisesRegex(frappe.ValidationError, "Fund transfers are closed"):
					self._new_transfer(transfer_type, currency=currency)
		frappe.set_user(self.cashier)
		with patch(MODULE + ".check_password") as check_password:
			with self.assertRaisesRegex(frappe.ValidationError, "Fund transfers are closed"):
				self._submit(cashier_draft)
			check_password.assert_not_called()
		cashier_draft.reload()
		self.assertEqual(cashier_draft.docstatus, 0)
		frappe.set_user(self.vc)
		with self.assertRaisesRegex(frappe.ValidationError, "Fund transfers are closed"):
			rover_draft.submit()
		self.assertEqual(get_entry_context(TEST_BRANCH, "PHP")["closed_position"], position.name)

	def test_cancelled_vcp_reopens_day_and_other_dates_or_branches_do_not_close_it(self):
		from frappe.utils import add_days
		from pawnshop_management.pawnshop_management.doctype.fund_transfer.fund_transfer import get_closed_vault_position
		position = self._close_vault()
		self.assertTrue(position.is_opening_position)
		self.assertIsNone(get_closed_vault_position("OTHER"))
		self.assertIsNone(get_closed_vault_position(TEST_BRANCH, add_days(today(), 1)))
		self.assertIsNone(get_closed_vault_position(TEST_BRANCH, add_days(today(), -1)))
		frappe.set_user("Administrator")
		position.cancel()
		self.assertIsNone(get_closed_vault_position(TEST_BRANCH, for_update=True))
		frappe.set_user(self.vc)
		doc = self._new_transfer("Armored Van to Vault")
		apply_workflow(doc, "Submit")
		doc.reload()
		self.assertEqual(doc.docstatus, 1)

	def test_previous_days_submitted_vcp_does_not_block_next_day(self):
		from frappe.utils import add_days, get_datetime
		self._close_vault()
		next_day = add_days(today(), 1)
		with patch(MODULE + ".today", return_value=next_day), patch(MODULE + ".now_datetime", return_value=get_datetime(next_day + " 09:00:00")):
			doc = self._new_transfer("Armored Van to Vault", business_date=next_day)
			apply_workflow(doc, "Submit")
			doc.reload()
			self.assertEqual(str(doc.business_date), next_day)
			self.assertEqual(doc.docstatus, 1)

	def test_backdated_input_cannot_bypass_todays_close(self):
		from frappe.utils import add_days
		self._close_vault()
		frappe.set_user("Administrator")
		with self.assertRaisesRegex(frappe.ValidationError, "Fund transfers are closed"):
			self._new_transfer("Armored Van to Vault", business_date=add_days(today(), -1))

	def test_draft_vcp_does_not_close_day(self):
		position = frappe.get_doc({"doctype": "Vault Cash Position", "branch": TEST_BRANCH})
		position.insert()
		self._fund_vault()
		self.assertIsNone(get_entry_context(TEST_BRANCH, "PHP")["closed_position"])

	def test_reconciliation_after_close_is_allowed_only_for_matching_system_adjustment(self):
		from pawnshop_management.pawnshop_management.doctype.vault_cash_position.vault_cash_position import approve_reconciliation
		from pawnshop_management.pawnshop_management.doctype.fund_transfer.fund_transfer import create_cash_position_adjustment
		self._fund_vault()
		position = self._close_vault(900)
		frappe.set_user("Administrator")
		with self.assertRaises(frappe.PermissionError):
			create_cash_position_adjustment(position, "PHP", -99)
		approve_reconciliation(position.name)
		position.reload()
		adjustment = frappe.get_doc("Fund Transfer", position.php_adjustment_fund_transfer)
		self.assertEqual((adjustment.docstatus, adjustment.civ_balance), (1, 900))
		with self.assertRaises(frappe.ValidationError):
			approve_reconciliation(position.name)
		with self.assertRaisesRegex(frappe.ValidationError, "Fund transfers are closed"):
			self._new_transfer("Armored Van to Vault")

	def test_cutoff_uses_current_read_after_another_transaction_commits(self):
		# No operational records are touched: the second connection inserts only a
		# uniquely named synthetic VCP and deletes it in finally.
		from uuid import uuid4
		from pawnshop_management.pawnshop_management.doctype.fund_transfer.fund_transfer import get_closed_vault_position
		name = "FT-CUTOFF-" + uuid4().hex
		branch = name
		other = frappe.db.get_connection()
		try:
			self.assertIsNone(get_closed_vault_position(branch))  # establish old snapshot
			with other.cursor() as cursor:
				cursor.execute("insert into `tabVault Cash Position` (name, branch, business_date, docstatus) values (%s,%s,%s,1)", (name, branch, today()))
			other.commit()
			self.assertEqual(get_closed_vault_position(branch, for_update=True), name)
		finally:
			# Release the current-read row lock before the second connection cleans up.
			frappe.db.rollback()
			with other.cursor() as cursor:
				cursor.execute("delete from `tabVault Cash Position` where name=%s", name)
			other.commit()
			other.close()

	def test_read_controls_are_preserved(self):
		doc = frappe._dict(branch="OTHER")
		self.assertFalse(has_permission(doc, "read", self.cashier))
		self.assertIn(TEST_BRANCH, get_permission_query_conditions(self.cashier))
		for role in ("Auditor", "Accounting Analyst", "Operations Manager", "Settlement Member"):
			with patch(MODULE + ".frappe.get_roles", return_value=[role]):
				self.assertIsNone(get_permission_query_conditions(self.cashier))
				self.assertTrue(has_permission(doc, "read", self.cashier))
