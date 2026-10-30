# Copyright (c) 2021, Rabie Moses Santillan and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt
from pawnshop_management.pawnshop_management.loan_dates import validate_loan_periods

class PawnshopManagementSettings(Document):
	def validate(self):
		validate_loan_periods(self)
		if flt(self.jewelry_a_series_limit) <= 0:
			frappe.throw("Jewelry A Series Maximum Principal must be greater than zero.")

	@frappe.whitelist()
	def reset_jewelry_count(self):
		self.jewelry_count = 0

	@frappe.whitelist()
	def reset_non_jewelry_count(self):
		self.non_jewelry_count = 0
