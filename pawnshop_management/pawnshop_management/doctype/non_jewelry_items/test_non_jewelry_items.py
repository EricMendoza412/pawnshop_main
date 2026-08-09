# Copyright (c) 2021, Rabie Moses Santillan and Contributors
# See license.txt

import frappe
import unittest

class TestNonJewelryItems(unittest.TestCase):
	def test_esim_only_changes_maximum_category_to_minimum(self):
		doc = frappe.get_doc({
			"doctype": "Non Jewelry Items",
			"type": "Cellphone",
			"brand": "Apple",
			"category": "Maximum",
			"esim_only": 1,
		})

		doc.validate_esim_only()

		self.assertEqual(doc.category, "Minimum")

	def test_esim_only_rejects_ineligible_items(self):
		doc = frappe.get_doc({
			"doctype": "Non Jewelry Items",
			"type": "Tablet",
			"brand": "Apple",
			"category": "Minimum",
			"esim_only": 1,
		})

		with self.assertRaises(frappe.ValidationError):
			doc.validate_esim_only()
