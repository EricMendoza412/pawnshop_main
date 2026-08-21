# Copyright (c) 2026, Rabie Santillan and Eric Mendoza and Contributors
# See license.txt

import unittest
from unittest.mock import patch

import frappe

from pawnshop_management.pawnshop_management.doctype.fund_transfer.fund_transfer import (
	approve_cashier_transfer,
	cancel_pending_transfer,
	confirm_rover_transfer,
	get_permission_query_conditions,
	has_permission,
	request_approval,
)


TEST_BRANCH = "TEST"


class TestFundTransfer(unittest.TestCase):
	@patch(
		"pawnshop_management.pawnshop_management.doctype.fund_transfer.fund_transfer.frappe.get_roles",
		return_value=["Auditor"],
	)
	@patch(
		"pawnshop_management.pawnshop_management.doctype.fund_transfer.fund_transfer.is_system_manager",
		return_value=False,
	)
	def test_auditor_can_read_all_branches_without_list_filter(self, _is_system_manager, _get_roles):
		doc = frappe._dict(branch="OTHER BRANCH")
		self.assertIsNone(get_permission_query_conditions("auditor@example.com"))
		self.assertTrue(has_permission(doc, "read", "auditor@example.com"))
		self.assertTrue(has_permission(doc, "report", "auditor@example.com"))

	@patch(
		"pawnshop_management.pawnshop_management.doctype.fund_transfer.fund_transfer.frappe.get_roles",
		return_value=["Operations Manager"],
	)
	@patch(
		"pawnshop_management.pawnshop_management.doctype.fund_transfer.fund_transfer.is_system_manager",
		return_value=False,
	)
	def test_operations_manager_can_read_all_branches_without_list_filter(self, _is_system_manager, _get_roles):
		doc = frappe._dict(branch="OTHER BRANCH")
		self.assertIsNone(get_permission_query_conditions("operations.manager@example.com"))
		self.assertTrue(has_permission(doc, "read", "operations.manager@example.com"))
		self.assertTrue(has_permission(doc, "report", "operations.manager@example.com"))

	def setUp(self):
		frappe.set_user("Administrator")
		self.original_request_ip = getattr(frappe.local, "request_ip", None)
		frappe.local.request_ip = frappe.db.get_value("Branch IP Addressing", TEST_BRANCH, "ip_address")
		self.original_branch = frappe.db.get_value(
			"Branch",
			TEST_BRANCH,
			["vault_custodian", "pawnshop_cashier", "fx_cashier", "remittance_cashier"],
			as_dict=True,
		)
		frappe.db.set_value(
			"Branch",
			TEST_BRANCH,
			{
				"vault_custodian": "Administrator",
				"pawnshop_cashier": "Administrator",
				"fx_cashier": "Administrator",
				"remittance_cashier": "Administrator",
			},
			update_modified=False,
		)
		frappe.db.set_value(
			"Fund Transfer Settings",
			"Fund Transfer Settings",
			{"enable_usd_validation": 0, "enable_google_uat_sync": 0},
			update_modified=False,
		)

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.local.request_ip = self.original_request_ip
		frappe.db.rollback()

	def test_armored_van_then_vault_out_updates_running_civ(self):
		incoming = self._new_transfer("Armored Van to Vault", 1000)
		request_approval(incoming.name)
		incoming.reload()
		self.assertEqual(incoming.docstatus, 1)
		self.assertEqual(incoming.opening_civ_balance, 0)
		self.assertEqual(incoming.civ_balance, 1000)
		self.assertEqual(incoming.google_sync_status, "Disabled")

		outgoing = self._new_transfer("Vault to Pawnshop (-NCB)", 250)
		request_approval(outgoing.name)
		outgoing.reload()
		self.assertEqual(outgoing.status, "Pending Cashier Approval")

		approve_cashier_transfer(outgoing.name)
		outgoing.reload()
		self.assertEqual(outgoing.docstatus, 1)
		self.assertEqual(outgoing.opening_civ_balance, 1000)
		self.assertEqual(outgoing.vault_balance_change, -250)
		self.assertEqual(outgoing.civ_balance, 750)
		self.assertEqual(outgoing.vc_to_ps_cashier, 250)

	def test_pending_transfer_and_submitted_transfer_can_be_cancelled_by_administrator(self):
		pending = self._new_transfer("Vault to Pawnshop (-NCB)", 25)
		request_approval(pending.name)
		cancel_pending_transfer(pending.name)
		pending.reload()
		self.assertEqual(pending.status, "Cancelled")
		self.assertEqual(pending.docstatus, 0)

		submitted = self._new_transfer("Armored Van to Vault", 50)
		request_approval(submitted.name)
		submitted.reload()
		submitted.cancel()
		self.assertEqual(submitted.docstatus, 2)

	def test_pending_transfer_definition_is_immutable(self):
		doc = self._new_transfer("Vault to Pawnshop (-NCB)", 100)
		request_approval(doc.name)
		doc.reload()
		doc.amount = 200
		with self.assertRaises(frappe.ValidationError):
			doc.save()

	def test_currency_matrix_is_enforced(self):
		doc = frappe.new_doc("Fund Transfer")
		doc.branch = TEST_BRANCH
		doc.currency = "USD"
		doc.transfer_type = "Vault to Pawnshop (-NCB)"
		doc.amount = 100
		with self.assertRaises(frappe.ValidationError):
			doc.insert()

	def test_uncollected_fx_requires_whole_dollars_within_expected_amount(self):
		for amount in (100.5, 101):
			with self.subTest(amount=amount):
				doc = frappe.new_doc("Fund Transfer")
				doc.branch = TEST_BRANCH
				doc.currency = "USD"
				doc.transfer_type = "Uncollected FX to Vault"
				doc.fx_cpr_date = "2026-08-07"
				doc.fx_expected_amount = 100
				doc.amount = amount
				with self.assertRaises(frappe.ValidationError):
					doc.insert()

	@patch(
		"pawnshop_management.pawnshop_management.fund_transfer_google.validate_uncollected_fx_envelope"
	)
	def test_uncollected_fx_submits_actual_amount_and_system_notes(self, validate_envelope):
		from frappe.model.workflow import apply_workflow

		validate_envelope.return_value = frappe._dict(source_row=1450, rate=60.7213, expected_amount=100)
		doc = frappe.new_doc("Fund Transfer")
		doc.branch = TEST_BRANCH
		doc.currency = "USD"
		doc.transfer_type = "Uncollected FX to Vault"
		doc.fx_cpr_date = "2026-08-07"
		doc.fx_expected_amount = 100
		doc.amount = 75
		doc.insert()
		apply_workflow(doc, "Submit")
		doc.reload()
		self.assertEqual(doc.docstatus, 1)
		self.assertEqual(doc.vault_balance_change, 75)
		self.assertEqual(doc.fx_difference_amount, 25)
		self.assertEqual(doc.given_by, "Uncollected FX")
		self.assertEqual(doc.received_by, "Administrator")
		self.assertEqual(doc.comments, "Administrator-Uncollected FX transfer")

	def test_assigned_cashier_approves_from_own_session(self):
		from frappe.model.workflow import apply_workflow

		cashier = self._create_user("fund.transfer.cashier@example.com")
		frappe.db.set_value("Branch", TEST_BRANCH, "pawnshop_cashier", cashier, update_modified=False)

		frappe.set_user("Administrator")
		incoming = self._new_transfer("Armored Van to Vault", 500)
		request_approval(incoming.name)
		pending = self._new_transfer("Vault to Pawnshop (-NCB)", 100)
		request_approval(pending.name)

		frappe.set_user(cashier)
		pending.reload()
		self.assertEqual(frappe.db.get_value("Branch", TEST_BRANCH, "pawnshop_cashier"), cashier)
		from pawnshop_management.pawnshop_management.doctype.fund_transfer.fund_transfer import (
			has_permission as controller_has_permission,
		)
		self.assertTrue(controller_has_permission(pending, "read", cashier))
		self.assertTrue(pending.has_permission("read"))
		self.assertIn(pending.name, frappe.get_list("Fund Transfer", pluck="name"))
		# Desk sends some values back in browser-equivalent representations.
		pending.amount = str(pending.amount)
		pending.legacy_transfer_id = ""
		pending.external_party = ""
		apply_workflow(pending, "Approve")
		pending.reload()
		self.assertEqual(pending.docstatus, 1)
		self.assertEqual(pending.authorized_by, cashier)
		self.assertEqual(pending.civ_balance, 400)

	def test_expected_authorizer_keeps_read_access_after_branch_assignment_changes(self):
		cashier = self._create_user("fund.transfer.expected.cashier@example.com")
		frappe.db.set_value("Branch", TEST_BRANCH, "pawnshop_cashier", cashier, update_modified=False)

		pending = self._new_transfer("Vault to Pawnshop (-NCB)", 100)
		request_approval(pending.name)
		frappe.db.set_value("Branch", TEST_BRANCH, "pawnshop_cashier", "Administrator", update_modified=False)

		frappe.set_user(cashier)
		pending.reload()
		self.assertTrue(pending.has_permission("read"))
		self.assertIn(pending.name, frappe.get_list("Fund Transfer", pluck="name"))

	def test_native_submit_stays_draft_when_cashier_is_unassigned(self):
		from frappe.model.workflow import apply_workflow

		frappe.db.set_value("Branch", TEST_BRANCH, "pawnshop_cashier", None, update_modified=False)
		doc = self._new_transfer("Vault to Pawnshop (-NCB)", 100)

		with self.assertRaisesRegex(frappe.ValidationError, "No Pawnshop Cashier is assigned"):
			apply_workflow(doc, "Submit")

		doc.reload()
		self.assertEqual(doc.status, "Draft")
		self.assertEqual(doc.docstatus, 0)

	def test_rover_password_confirms_exact_pending_transfer(self):
		from frappe.utils.password import update_password

		rover = self._create_user("fund.transfer.rover@example.com", roles=["Rover"])
		update_password(rover, "Rover-Test-Password-2026")

		frappe.set_user("Administrator")
		doc = self._new_transfer("Rover to Vault", 300)
		request_approval(doc.name)
		doc.reload()
		self.assertEqual(doc.status, "Pending Rover Confirmation")

		confirm_rover_transfer(doc.name, rover, "Rover-Test-Password-2026")
		doc.reload()
		self.assertEqual(doc.docstatus, 1)
		self.assertEqual(doc.authorized_by, rover)
		self.assertEqual(doc.civ_balance, 300)

	def test_rover_password_submits_vault_to_cash_manager_directly_from_draft(self):
		from frappe.model.workflow import apply_workflow
		from frappe.utils.password import update_password

		rover = self._create_user("fund.transfer.direct.rover@example.com", roles=["Rover"])
		update_password(rover, "Rover-Direct-Password-2026")

		incoming = self._new_transfer("Armored Van to Vault", 500)
		request_approval(incoming.name)
		doc = self._new_transfer("Vault to Cash Manager", 125)
		doc.rover = rover
		doc.rover_password = "Rover-Direct-Password-2026"

		apply_workflow(doc, "Submit")
		doc.reload()
		self.assertEqual(doc.docstatus, 1)
		self.assertEqual(doc.status, "Submitted")
		self.assertEqual(doc.authorized_by, rover)
		self.assertEqual(doc.vault_balance_change, -125)
		self.assertEqual(doc.civ_balance, 375)
		self.assertFalse(doc.rover_password)

	def _new_transfer(self, transfer_type, amount, currency="PHP"):
		doc = frappe.new_doc("Fund Transfer")
		doc.branch = TEST_BRANCH
		doc.currency = currency
		doc.transfer_type = transfer_type
		doc.amount = amount
		doc.insert()
		self.assertRegex(doc.name, r"^TEST-\d{6}$")
		return doc

	def _create_user(self, email, roles=None):
		user = frappe.new_doc("User")
		user.email = email
		user.first_name = "Fund Transfer Test"
		user.send_welcome_email = 0
		for role in roles or []:
			user.append("roles", {"role": role})
		user.insert(ignore_permissions=True)
		return user.name
