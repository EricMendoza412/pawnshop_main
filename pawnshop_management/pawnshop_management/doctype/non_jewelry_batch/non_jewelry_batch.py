# Copyright (c) 2022, Rabie Moses Santillan and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class NonJewelryBatch(Document):
	def before_save(self):
		if frappe.db.exists('Pawn Ticket Jewelry', self.name) == None:
			settings = frappe.get_doc('Pawnshop Naming Series', self.branch)
			settings.inventory_count += 1
			settings.item_count = 1
			settings.save(ignore_permissions=True)
		else:
			print(self.branch)
