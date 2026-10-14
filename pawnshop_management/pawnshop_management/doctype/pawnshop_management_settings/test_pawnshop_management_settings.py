# Copyright (c) 2021, Rabie Moses Santillan and Contributors
# See license.txt

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from pawnshop_management.pawnshop_management.doctype.pawnshop_management_settings import (
    pawnshop_management_settings as settings,
)
from pawnshop_management.pawnshop_management.patches.v1_0 import set_jewelry_a_series_limit


class TestPawnshopManagementSettings(unittest.TestCase):
    def test_positive_jewelry_limit(self):
        for value in (40000, 50000, 40000.01):
            settings.PawnshopManagementSettings.validate(
                SimpleNamespace(jewelry_a_series_limit=value)
            )

    def test_invalid_jewelry_limit(self):
        for value in (None, 0, -1):
            with self.subTest(value=value), patch.object(settings, "frappe") as frappe:
                frappe.throw.side_effect = ValueError
                with self.assertRaises(ValueError):
                    settings.PawnshopManagementSettings.validate(
                        SimpleNamespace(jewelry_a_series_limit=value)
                    )

    def test_migration_only_initializes_missing_limit(self):
        for value in (None, "", "50000", "0"):
            with self.subTest(value=value), patch.object(set_jewelry_a_series_limit, "frappe") as frappe:
                frappe.db.get_value.return_value = value
                set_jewelry_a_series_limit.execute()
                if value in (None, ""):
                    frappe.db.set_single_value.assert_called_once_with(
                        "Pawnshop Management Settings", "jewelry_a_series_limit", 40000
                    )
                else:
                    frappe.db.set_single_value.assert_not_called()
