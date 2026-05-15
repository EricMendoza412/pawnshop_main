# Copyright (c) 2022, Rabie Moses Santillan and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import today

class AgreementtoSell(Document):
	def before_validate(self):
		if not self.main_appraiser_acct or not self.assistant_appraiser_acct:
			for item in self.jewelry_items or []:
				if not item.item_no:
					continue
				first_jewelry_item = frappe.get_doc("Jewelry Items", item.item_no)
				self.main_appraiser_acct = self.main_appraiser_acct or first_jewelry_item.main_appraiser_acct
				self.main_appraiser = self.main_appraiser or first_jewelry_item.main_appraiser
				self.assistant_appraiser_acct = self.assistant_appraiser_acct or first_jewelry_item.assistant_appraiser_acct
				self.assistant_appraiser = self.assistant_appraiser or first_jewelry_item.assistant_appraiser
				break

		if self.main_appraiser_acct:
			self.main_appraiser = frappe.db.get_value("User", self.main_appraiser_acct, "first_name")

		if self.assistant_appraiser_acct:
			self.assistant_appraiser = frappe.db.get_value("User", self.assistant_appraiser_acct, "first_name")

	def validate(self):
		if self.main_appraiser_acct and self.main_appraiser_acct == self.assistant_appraiser_acct:
			frappe.throw("Assistant Appraiser cannot be the same as Main Appraiser.")

	def validate_appraisers_for_submit(self):
		self.before_validate()
		self.validate()

		if not self.main_appraiser_acct:
			frappe.throw("Main appraiser account is required.")

		if not self.assistant_appraiser_acct:
			frappe.throw("Assistant appraiser account is required.")

	def update_jewelry_item_appraisers(self):
		for item in self.jewelry_items:
			if not item.item_no:
				continue
			frappe.db.set_value(
				'Jewelry Items',
				item.item_no,
				{
					'main_appraiser_acct': self.main_appraiser_acct,
					'main_appraiser': self.main_appraiser,
					'assistant_appraiser_acct': self.assistant_appraiser_acct,
					'assistant_appraiser': self.assistant_appraiser
				}
			)

	def before_save(self):
		if frappe.db.exists('Agreement to Sell', self.name) == None:
			if self.amended_from == None:
				settings = frappe.get_doc('Pawnshop Naming Series', self.branch)
				settings.ats_jewelry_count  += 1
				settings.save(ignore_permissions=True)
				settings.save(ignore_permissions=True)

	def before_submit(self):
		self.validate_appraisers_for_submit()

	def on_submit(self):
		self.update_jewelry_item_appraisers()

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
			
