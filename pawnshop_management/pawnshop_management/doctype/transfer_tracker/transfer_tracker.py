# Copyright (c) 2024, Rabie Moses Santillan and contributors
# For license information, please see license.txt

# import frappe
import frappe
from datetime import datetime
from pydoc import Doc, doc
from frappe.model.document import Document
from frappe.model.document import Document
from frappe.utils import now_datetime

class TransferTracker(Document):
	def before_save(self):
		if frappe.db.exists('Transfer Tracker', self.name) == None:
			if self.amended_from == None:
				settings = frappe.get_doc('Pawnshop Naming Series', self.origin)
				settings.nj_transfer_form += 1
				settings.save(ignore_permissions=True)

	def on_update(self):
		if self.workflow_state == "For Receiving":
			#change workflow state of all items in the child table to In Transit
			for item in self.nj_items:
				item_doc = frappe.get_doc('Non Jewelry Items', item.item_no)
				item_doc.workflow_state = "In Transit"
				item_doc.save(ignore_permissions=True)
				item_pawnticket = frappe.get_doc('Pawn Ticket Non Jewelry', item.last_pawn_ticket)
				item_pawnticket.db_set('workflow_state', 'Pulled Out', update_modified=True)
				item_pawnticket.db_set('change_status_date', now_datetime(), update_modified=True)
			
	#Do something when document changes status from For Receiving to Complete
	def on_update_after_submit(self):
		if self.workflow_state == "Complete":
			#Update the item location in Item table depending on transfer type
			if self.transfer_type == "Pull out of Expired Sangla":
				#change current_location of all items in the child table to Subastado NJ
				for item in self.nj_items:
					item_doc = frappe.get_doc('Non Jewelry Items', item.item_no)
					item_doc.current_location = self.destination
					item_doc.pt_principal = item.pt_principal
					item_doc.workflow_state = "Unprocessed"
					item_doc.date_received = now_datetime()
					item_doc.save(ignore_permissions=True)
					
			elif self.transfer_type == "Transfer of Display Items":
				#change current_location of all items in the child table to destination
				for item in self.nj_items:
					item_doc = frappe.get_doc('Non Jewelry Items', item.item_no)
					item_doc.current_location = self.destination
					item_doc.workflow_state = "For Sale"
					item_doc.save(ignore_permissions=True)
			# # put date today in date_received and put name of current user in the field received_by
			self.db_set('date_received', now_datetime(), update_modified=True)
			self.db_set('received_by', frappe.session.user, update_modified=True)
