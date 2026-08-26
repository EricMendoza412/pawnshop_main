# Copyright (c) 2026, Rabie Santillan and Eric Mendoza and Contributors
# See license.txt

import unittest
from unittest.mock import patch

import frappe

from pawnshop_management.pawnshop_management.doctype.vc_turnover_checklist.vc_turnover_checklist import (
	VCTurnoverChecklist,
	get_vault_cash_autofill,
)


MODULE = "pawnshop_management.pawnshop_management.doctype.vc_turnover_checklist.vc_turnover_checklist"


class _ChecklistStub:
	def __init__(self, **values):
		self.values = values
		self.name = values.get("name")
		self.branch = values.get("branch")
		self.date = values.get("date")

	def get(self, fieldname):
		return self.values.get(fieldname)

	def set(self, fieldname, value):
		self.values[fieldname] = value

	def is_new(self):
		return not self.name


class TestVCTurnoverChecklistCashAutofill(unittest.TestCase):
	def test_same_day_transfer_overrides_only_its_currency(self):
		position = frappe._dict(
			name="VCP-0001",
			php_actual_cash=1500.25,
			usd_actual_cash=170,
			php_denominations=[
				frappe._dict(denomination=1000, amount=1000),
				frappe._dict(denomination=500, amount=500),
				frappe._dict(denomination=0.25, amount=0.25),
			],
			usd_denominations=[
				frappe._dict(denomination=100, amount=100),
				frappe._dict(denomination=50, amount=50),
				frappe._dict(denomination=20, amount=20),
			],
		)

		def get_value(doctype, filters, fieldname, **kwargs):
			if doctype == "Vault Cash Position":
				self.assertEqual(filters["docstatus"], 1)
				self.assertEqual(filters["business_date"], ["<=", frappe.utils.getdate("2026-08-26")])
				self.assertEqual(kwargs["order_by"], "business_date desc, count_datetime desc, creation desc")
				return position.name
			if filters["currency"] == "PHP":
				self.assertEqual(filters["business_date"], frappe.utils.getdate("2026-08-26"))
				self.assertEqual(filters["status"], "Submitted")
				self.assertEqual(kwargs["order_by"], "date_of_transfer desc, creation desc")
				return frappe._dict(name="FT-PHP-0002", civ_balance=1800)
			return None

		with patch(f"{MODULE}.frappe.db.get_value", side_effect=get_value), patch(
			f"{MODULE}.frappe.get_doc", return_value=position
		):
			values = get_vault_cash_autofill("TEST", "2026-08-26")

		self.assertEqual(values["forex_reserved_php"], 1800)
		self.assertEqual(values["php_cash_source_type"], "Fund Transfer")
		self.assertIsNone(values["php_breakdown"])
		self.assertEqual(values["forex_reserved_usd"], 170)
		self.assertEqual(values["usd_cash_source_type"], "Vault Cash Position")
		self.assertEqual(values["usd_breakdown"]["usd_100"], 100)
		self.assertEqual(values["usd_breakdown"]["usd_50"], 50)

	def test_vault_cash_position_populates_php_quarter_denomination(self):
		position = frappe._dict(
			name="VCP-0001",
			php_actual_cash=0.25,
			usd_actual_cash=0,
			php_denominations=[frappe._dict(denomination=0.25, amount=0.25)],
			usd_denominations=[],
		)

		def get_value(doctype, filters, fieldname, **kwargs):
			return position.name if doctype == "Vault Cash Position" else None

		with patch(f"{MODULE}.frappe.db.get_value", side_effect=get_value), patch(
			f"{MODULE}.frappe.get_doc", return_value=position
		):
			values = get_vault_cash_autofill("TEST", "2026-08-26")

		self.assertEqual(values["php_breakdown"]["php_025"], 0.25)

	def test_missing_sources_return_zero_locked_breakdown_values(self):
		with patch(f"{MODULE}.frappe.db.get_value", return_value=None):
			values = get_vault_cash_autofill("TEST", "2026-08-26")

		self.assertEqual(values["forex_reserved_php"], 0)
		self.assertEqual(values["forex_reserved_usd"], 0)
		self.assertEqual(values["php_cash_source_type"], "")
		self.assertEqual(values["usd_cash_source_type"], "")
		self.assertEqual(values["php_breakdown"]["php_025"], 0)
		self.assertEqual(values["usd_breakdown"]["usd_100"], 0)

	@patch(f"{MODULE}._get_stored_cash_sources")
	@patch(f"{MODULE}.get_vault_cash_autofill")
	def test_transition_from_position_to_transfer_clears_only_affected_breakdown(self, get_values, get_previous):
		get_previous.return_value = frappe._dict(
			branch="TEST",
			php_cash_source_type="Vault Cash Position",
			usd_cash_source_type="Vault Cash Position",
		)
		get_values.return_value = {
			"forex_reserved_php": 2000,
			"php_cash_source_type": "Fund Transfer",
			"php_cash_source_document": "FT-PHP-0001",
			"php_breakdown": None,
			"forex_reserved_usd": 100,
			"usd_cash_source_type": "Vault Cash Position",
			"usd_cash_source_document": "VCP-0001",
			"usd_breakdown": {"usd_100": 100},
		}
		doc = _ChecklistStub(
			name="VCT-0001",
			branch="TEST",
			date="2026-08-26",
			php_1000=1000,
			php_500=500,
			usd_100=0,
		)

		VCTurnoverChecklist.populate_vault_cash_fields(doc)

		self.assertEqual(doc.get("php_1000"), 0)
		self.assertEqual(doc.get("php_500"), 0)
		self.assertEqual(doc.get("usd_100"), 100)

	def test_php_quarter_is_included_in_breakdown_total(self):
		doc = _ChecklistStub(php_1=1, php_025=0.25)

		VCTurnoverChecklist.calculate_totals(doc)

		self.assertEqual(doc.php_total, 1.25)

	def test_manual_transfer_breakdown_must_equal_in_vault_total(self):
		doc = _ChecklistStub(
			php_cash_source_type="Fund Transfer",
			forex_reserved_php=1000,
			php_total=900,
			usd_cash_source_type="",
		)

		with self.assertRaises(frappe.ValidationError):
			VCTurnoverChecklist.validate_manual_cash_breakdowns(doc)

		doc.set("php_total", 1000)
		VCTurnoverChecklist.validate_manual_cash_breakdowns(doc)


if __name__ == "__main__":
	unittest.main()
