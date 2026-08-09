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
