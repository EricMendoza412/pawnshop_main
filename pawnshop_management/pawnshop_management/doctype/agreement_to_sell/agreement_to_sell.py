# Copyright (c) 2022, Rabie Moses Santillan and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import today

class AgreementtoSell(Document):
	def before_save(self):
		if frappe.db.exists('Agreement to Sell', self.name) == None:
			if self.amended_from == None:
				settings = frappe.get_doc('Pawnshop Naming Series', self.branch)
				settings.ats_jewelry_count  += 1
				settings.save(ignore_permissions=True)
				settings.save(ignore_permissions=True)

	def on_submit(self):
		if frappe.db.exists('Jewelry Batch', self.ats_tracking_no) == None:#Copies Items table from pawnt ticket to non jewelry batch doctype
			new_jewelry_batch = frappe.new_doc('Jewelry Batch')
			new_jewelry_batch.inventory_tracking_no = self.ats_tracking_no
			new_jewelry_batch.branch = self.branch
			items = self.jewelry_items
			for i in range(len(items)):
				new_jewelry_batch.append('items', {
					"item_no": items[i].item_no,
					"type": items[i].type,
					"karat_category": items[i].karat_category,
					"karat": items[i].karat,
					"weight": items[i].weight,
					"color": items[i].color,
					"colors_if_multi": items[i].colors_if_multi,
					"additional_for_stone": items[i].additional_for_stone,
					"suggested_appraisal_value": items[i].suggested_appraisal_value,
					"desired_principal": items[i].desired_principal,
					"comments": items[i].comments
				})
			new_jewelry_batch.save(ignore_permissions=True)

	def update_ats_status(self):
		if self.workflow_state == "Pulled Out":
			frappe.db.set_value("Agreement to Sell", self.form_number, 'change_status_date', today())

	def on_update(self):
		self.update_ats_status()
	def on_update_after_submit(self):
		self.update_ats_status()
			
