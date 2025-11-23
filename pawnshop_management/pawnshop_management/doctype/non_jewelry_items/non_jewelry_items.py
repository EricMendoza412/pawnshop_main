# Copyright (c) 2021, Rabie Moses Santillan and contributors
# For license information, please see license.txt

# from pydoc import doc
import frappe
from frappe.model.document import Document

class NonJewelryItems(Document):
	def before_save(self):
		if frappe.db.exists('Pawn Ticket Non Jewelry', self.name) == None:
			if frappe.db.exists('Pawnshop Naming Series', self.branch):
				settings = frappe.get_doc('Pawnshop Naming Series', self.branch)
				# if branch is Subastado NJ, increment the inventory count and not the item count
				if self.branch == 'Subastado NJ':
					settings.inventory_count += 1
				else:			
					settings.item_count += 1
				settings.save(ignore_permissions=True)
		
