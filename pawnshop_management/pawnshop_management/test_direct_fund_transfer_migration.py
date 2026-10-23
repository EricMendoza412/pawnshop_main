import unittest
from unittest.mock import patch

import frappe

from pawnshop_management.pawnshop_management.patches.v1_0.enable_direct_fund_transfer_confirmation import (
	ABANDONED_STATES,
	cleanup_abandoned_transfers,
)


class TestDirectFundTransferCleanup(unittest.TestCase):
	def setUp(self):
		frappe.set_user("Administrator")

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def test_inventory_excludes_submitted_and_historical_records(self):
		with patch.object(frappe, "get_all", return_value=[]) as get_all, patch.object(frappe, "delete_doc") as delete:
			self.assertEqual(cleanup_abandoned_transfers(), [])
			self.assertEqual(get_all.call_args.kwargs["filters"], {"docstatus": 0, "status": ["in", ABANDONED_STATES]})
			self.assertNotIn("Imported Historical", ABANDONED_STATES)
			delete.assert_not_called()

	def test_cleanup_requires_exact_reviewed_inventory(self):
		with patch.object(frappe, "get_all", return_value=[frappe._dict(name="NEW-DRAFT")]), patch.object(frappe, "delete_doc") as delete:
			with self.assertRaises(frappe.ValidationError):
				cleanup_abandoned_transfers(delete=True, expected_names=["OLD-DRAFT"])
			delete.assert_not_called()

	def test_linked_transaction_blocks_cleanup(self):
		doc = frappe._dict(name="LINKED", docstatus=0, status="Draft", fx_selling="FX-1")
		with patch.object(frappe, "get_all", return_value=[doc]), patch.object(frappe, "get_doc", return_value=doc), patch.object(frappe, "delete_doc") as delete:
			with self.assertRaises(frappe.ValidationError):
				cleanup_abandoned_transfers(delete=True, expected_names=["LINKED"])
			delete.assert_not_called()

	def test_cleanup_keeps_normal_link_checks_and_deletion_archive(self):
		doc = frappe._dict(name="DRAFT", docstatus=0, status="Draft")
		with patch.object(frappe, "get_all", return_value=[doc]), patch.object(frappe, "get_doc", return_value=doc), patch.object(frappe, "delete_doc") as delete:
			cleanup_abandoned_transfers(delete=True, expected_names=["DRAFT"])
			delete.assert_called_once_with("Fund Transfer", "DRAFT")
