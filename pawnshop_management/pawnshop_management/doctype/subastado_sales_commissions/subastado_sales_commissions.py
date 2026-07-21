# Copyright (c) 2023, Rabie Moses Santillan and contributors
# For license information, please see license.txt

from frappe.utils import flt
from frappe.model.document import Document


SPECIAL_BRANCH_CODES = {"5", "7", "8", "9"}
COMMISSION_RATE = 0.03


class SubastadoSalesCommissions(Document):
	def before_save(self):
		"""Calculate the sale commission and split it equally between sellers."""
		seller_count = len(self.get("sellers_list") or [])
		minimum_sellers = 1 if str(self.branch_code or "").strip() in SPECIAL_BRANCH_CODES else 2
		multiplier = COMMISSION_RATE if seller_count > minimum_sellers else 0

		commission_total = 0
		for item in self.get("items_list") or []:
			is_subasta = str(item.is_subasta or "").strip().lower() == "subasta"
			if not is_subasta and flt(item.cost) != 0:
				commission_total += flt(item.amount) * multiplier

		# Keep the existing aggregate field useful for reports and integrations.
		self.commision = commission_total
		commission_per_seller = commission_total / seller_count if seller_count else 0

		for seller in self.get("sellers_list") or []:
			seller.commission_amount = commission_per_seller
