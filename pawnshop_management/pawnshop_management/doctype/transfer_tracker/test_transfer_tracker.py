# Copyright (c) 2024, Rabie Moses Santillan and Contributors
# See license.txt

import unittest
from unittest.mock import patch

from pawnshop_management.pawnshop_management.doctype.transfer_tracker.transfer_tracker import (
	get_permission_query_conditions,
	has_permission,
)


class TestTransferTracker(unittest.TestCase):
	@patch(
		"pawnshop_management.pawnshop_management.doctype.transfer_tracker.transfer_tracker.frappe.get_roles",
		return_value=["Auditor"],
	)
	@patch(
		"pawnshop_management.pawnshop_management.doctype.transfer_tracker.transfer_tracker.is_system_manager",
		return_value=False,
	)
	def test_auditor_list_is_not_branch_filtered(self, _is_system_manager, _get_roles):
		self.assertIsNone(get_permission_query_conditions("auditor@example.com"))

	@patch(
		"pawnshop_management.pawnshop_management.doctype.transfer_tracker.transfer_tracker.is_transfer_tracker_branch_vault_custodian",
		return_value=False,
	)
	@patch(
		"pawnshop_management.pawnshop_management.doctype.transfer_tracker.transfer_tracker.frappe.get_roles",
		return_value=["Auditor"],
	)
	@patch(
		"pawnshop_management.pawnshop_management.doctype.transfer_tracker.transfer_tracker.is_system_manager",
		return_value=False,
	)
	def test_auditor_bypass_is_read_only(self, _is_system_manager, _get_roles, _is_vault_custodian):
		doc = object()
		self.assertTrue(has_permission(doc, "read", "auditor@example.com"))
		self.assertTrue(has_permission(doc, "report", "auditor@example.com"))
		self.assertFalse(has_permission(doc, "write", "auditor@example.com"))


class TestTransferOrigin(unittest.TestCase):
	def setUp(self):
		from types import SimpleNamespace
		from pawnshop_management.pawnshop_management.doctype.transfer_tracker import transfer_tracker
		self.module = transfer_tracker
		self.row = SimpleNamespace
		self.patcher = patch.object(transfer_tracker, "frappe")
		self.frappe = self.patcher.start()
		self.addCleanup(self.patcher.stop)
		self.frappe.throw.side_effect = ValueError
		self.frappe.session.user = "custodian@example.com"

	def test_single_custody_branch_overrides_role_assumptions(self):
		self.frappe.get_all.return_value = [self.row(name="Bulk NJ")]
		self.assertEqual(self.module.get_transfer_origin(), "Bulk NJ")
		self.assertEqual(self.frappe.get_all.call_args.kwargs["filters"], {"vault_custodian": "custodian@example.com"})

	def test_missing_or_multiple_assignments_stop_transfer(self):
		for branches in ([], [self.row(name="Bulk NJ"), self.row(name="Subastado NJ")]):
			self.frappe.get_all.return_value = branches
			with self.assertRaises(ValueError):
				self.module.get_transfer_origin()

	def test_bulk_number_uses_configured_prefix(self):
		self.frappe.db.get_value.side_effect = ["BN", 123]
		self.assertEqual(self.module.get_transfer_number("Bulk NJ"), "BN-123")

	def test_missing_numbering_is_rejected(self):
		self.frappe.db.get_value.side_effect = [None, 123]
		with self.assertRaises(ValueError):
			self.module.get_transfer_number("Bulk NJ")

	def test_bulk_item_location_and_states(self):
		self.frappe.get_all.return_value = [self.row(name="Bulk NJ")]
		doc = self.row(origin="Bulk NJ", item_type="Non Jewelry Items", transfer_type="Transfer of Display Items",
			is_new=lambda: True, nj_items=[self.row(item_no="NJ-1")])
		for state in ("For Sale", "Reserved"):
			self.frappe.db.get_value.return_value = self.row(current_location="Bulk NJ", workflow_state=state)
			self.module.TransferTracker.validate_origin_and_items(doc)
		for location, state in (("Subastado NJ", "For Sale"), ("Bulk NJ", "Unprocessed"), ("Bulk NJ", "In Transit")):
			self.frappe.db.get_value.return_value = self.row(current_location=location, workflow_state=state)
			with self.assertRaises(ValueError):
				self.module.TransferTracker.validate_origin_and_items(doc)

	def test_forged_origin_is_rejected(self):
		self.frappe.get_all.return_value = [self.row(name="Bulk NJ")]
		with self.assertRaises(ValueError):
			self.module.TransferTracker.validate_origin_and_items(self.row(origin="Subastado NJ"))

	def test_receipt_preserves_reserved_status(self):
		from unittest.mock import Mock
		for previous_state in ("For Sale", "Reserved"):
			item = Mock()
			self.frappe.get_doc.return_value = item
			doc = self.row(workflow_state="Complete", transfer_type="Transfer of Display Items",
				destination="Subastado NJ", nj_items=[self.row(item_no="NJ-1", previous_workflow_state=previous_state)],
				j_items=[], db_set=Mock())
			with patch.object(self.module, "now_datetime", return_value="2026-11-09 12:00:00"):
				self.module.TransferTracker.on_update_after_submit(doc)
			self.assertEqual(item.current_location, "Subastado NJ")
			self.assertEqual(item.workflow_state, previous_state)

	def test_bulk_rejects_other_transfer_types(self):
		self.frappe.get_all.return_value = [self.row(name="Bulk NJ")]
		for transfer_type in ("Pull out of Expired Sangla", "Issue as company used item"):
			doc = self.row(origin="Bulk NJ", item_type="Non Jewelry Items", transfer_type=transfer_type, is_new=lambda: True)
			with self.assertRaises(ValueError):
				self.module.TransferTracker.validate_origin_and_items(doc)
