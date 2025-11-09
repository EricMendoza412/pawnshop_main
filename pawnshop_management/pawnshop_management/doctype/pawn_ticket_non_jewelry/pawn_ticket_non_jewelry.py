# Copyright (c) 2022, Rabie Moses Santillan and contributors
# For license information, please see license.txt

from pydoc import doc
import frappe
from frappe.model.document import Document
from frappe.utils import flt
from pawnshop_management.pawnshop_management.custom_codes.update_pawn_ticket import (
    update_fields_after_status_change_collect_pawn_ticket,
    update_fields_after_status_change_pull_out_pawn_ticket,
	update_fields_after_status_change_return_pawn_ticket,
	update_fields_after_status_change_renew_pawn_ticket,
	update_fields_after_status_change_redeem_pawn_ticket,
	update_fields_after_status_change_reject_pawn_ticket
)

class PawnTicketNonJewelry(Document):
	def update_pawn_ticket_jewelry_statuses(self):
		if self.workflow_state == "Expired":
			update_fields_after_status_change_collect_pawn_ticket("Pawn Ticket Non Jewelry", self.inventory_tracking_no, self.pawn_ticket)
		elif self.workflow_state == "Pulled Out":
			update_fields_after_status_change_pull_out_pawn_ticket("Pawn Ticket Non Jewelry", self.inventory_tracking_no, self.pawn_ticket)
		elif self.workflow_state == "Returned":
			update_fields_after_status_change_return_pawn_ticket("Pawn Ticket Non Jewelry", self.inventory_tracking_no, self.pawn_ticket)
		elif self.workflow_state == "Renewed":
			update_fields_after_status_change_renew_pawn_ticket("Pawn Ticket Non Jewelry", self.inventory_tracking_no, self.pawn_ticket)	
		elif self.workflow_state == "Redeemed":
			update_fields_after_status_change_redeem_pawn_ticket("Pawn Ticket Non Jewelry", self.inventory_tracking_no, self.pawn_ticket)	
		elif self.workflow_state == "Rejected":
			update_fields_after_status_change_reject_pawn_ticket("Pawn Ticket Non Jewelry", self.inventory_tracking_no, self.pawn_ticket)	


	def on_update(self):
		self.update_pawn_ticket_jewelry_statuses()
	def on_update_after_submit(self):
		self.update_pawn_ticket_jewelry_statuses()
	# def on_trash(self):
	# 	self.update_pawn_ticket_jewelry_statuses()
	def on_cancel(self):
		self.update_pawn_ticket_jewelry_statuses()

	def before_save(self):
		if frappe.db.exists('Pawn Ticket Non Jewelry', self.name) == None and frappe.db.exists('Pawn Ticket Jewelry', self.name) == None:
			if self.amended_from == None:
				settings = frappe.get_doc('Pawnshop Naming Series', self.branch)
				settings.b_series += 1
				settings.save(ignore_permissions=True)

	def on_submit(self):
		if frappe.db.exists('Non Jewelry Batch', self.inventory_tracking_no) == "" or frappe.db.exists('Non Jewelry Batch', self.inventory_tracking_no) == None:	#Copies Items table from pawnt ticket to non jewelry batch doctype
			new_non_jewelry_batch = frappe.new_doc('Non Jewelry Batch')
			new_non_jewelry_batch.inventory_tracking_no = self.inventory_tracking_no
			new_non_jewelry_batch.branch = self.branch
			items = self.non_jewelry_items
			for i in range(len(items)):
				new_non_jewelry_batch.append('items', {
					"item_no": items[i].item_no,
					"type": items[i].type,
					"brand": items[i].brand,
					"model": items[i].model,
					"model_number": items[i].model_number,
					"suggested_appraisal_value": items[i].suggested_appraisal_value
				})
			new_non_jewelry_batch.save(ignore_permissions=True)

		#Journal Entry Creation
		# if self.created_by_pr == "" or self.created_by_pr == None: 		#Creates Journal Entry if it is not created by Provisional Receipt
		# 	doc1 = frappe.new_doc('Journal Entry')
		# 	doc1.voucher_type = 'Journal Entry'
		# 	doc1.company = 'MP Consolidated'
		# 	doc1.posting_date = self.date_loan_granted
		# 	doc1.reference_doctype = "Pawn Ticket Non Jewelry"
		# 	doc1.reference_document = self.name
		# 	doc1.document_status = "New Sangla"
		# 	doc1.finance_book = 'NCB'

		# 	row_values1 = doc1.append('accounts', {})
		# 	if self.branch == "Garcia's Pawnshop - CC":
		# 		row_values1.account = "1615-001 - Pawned Items Inventory - NJ - CC - MPConso"
		# 		row_values1.branch = "Garcia's Pawnshop - CC"
		# 		row_values1.cost_center = "1 - Cavite City - MPConso"
		# 	elif self.branch == "Garcia's Pawnshop - GTC":
		# 		row_values1.account = "1615-002 - Pawned Items Inventory - NJ - GTC - MPConso"
		# 		row_values1.branch = "Garcia's Pawnshop - GTC"
		# 		row_values1.cost_center = "4 - Gen. Trias - MPConso"
		# 	elif self.branch == "Garcia's Pawnshop - MOL":
		# 		row_values1.account = "1615-003 - Pawned Items Inventory - NJ - MOL - MPConso"
		# 		row_values1.branch = "Garcia's Pawnshop - MOL"
		# 		row_values1.cost_center = "6 - Molino - MPConso"
		# 	elif self.branch == "Garcia's Pawnshop - POB":
		# 		row_values1.account = "1615-004 - Pawned Items Inventory - NJ - POB - MPConso"
		# 		row_values1.branch = "Garcia's Pawnshop - POB"
		# 		row_values1.cost_center = "3 - Poblacion - MPConso"
		# 	elif self.branch == "Garcia's Pawnshop - TNZ":
		# 		row_values1.account = "1615-005 - Pawned Items Inventory - NJ - TNZ - MPConso"
		# 		row_values1.branch = "Garcia's Pawnshop - TNZ"
		# 		row_values1.cost_center = "5 - Tanza - MPConso"
		# 	elif self.branch == "Rabie's House":
		# 		row_values1.account = "1615-001 - Pawned Items Inventory - NJ - CC - MPConso"
		# 		row_values1.branch = "Garcia's Pawnshop - CC"
		# 		row_values1.cost_center = "1 - Cavite City - MPConso"

		# 	row_values1.debit_in_account_currency = flt(self.desired_principal)
		# 	row_values1.credit_in_account_currency = flt(0)

		# 	row_values2 = doc1.append('accounts', {})
		# 	if self.branch == "Garcia's Pawnshop - CC":
		# 		row_values2.account = "4111-001 - Interest on Loans and Advances - NJ - CC - MPConso"
		# 		row_values2.branch = "Garcia's Pawnshop - CC"
		# 		row_values2.cost_center = "1 - Cavite City - MPConso"
		# 	elif self.branch == "Garcia's Pawnshop - GTC":
		# 		row_values2.account = "4111-002 - Interest on Loans and Advances - NJ - GTC - MPConso"
		# 		row_values2.branch = "Garcia's Pawnshop - GTC"
		# 		row_values2.cost_center = "4 - Gen. Trias - MPConso"
		# 	elif self.branch == "Garcia's Pawnshop - MOL":
		# 		row_values2.account = "4111-003 - Interest on Loans and Advances - NJ - MOL - MPConso"
		# 		row_values2.branch = "Garcia's Pawnshop - MOL"
		# 		row_values2.cost_center = "6 - Molino - MPConso"
		# 	elif self.branch == "Garcia's Pawnshop - POB":
		# 		row_values2.account = "4111-004 - Interest on Loans and Advances - NJ - POB - MPConso"
		# 		row_values2.branch = "Garcia's Pawnshop - POB"
		# 		row_values2.cost_center = "3 - Poblacion - MPConso"
		# 	elif self.branch == "Garcia's Pawnshop - TNZ":
		# 		row_values2.account = "4111-005 - Interest on Loans and Advances - NJ - TNZ - MPConso"
		# 		row_values2.branch = "Garcia's Pawnshop - TNZ"
		# 		row_values2.cost_center = "5 - Tanza - MPConso"
		# 	elif self.branch == "Rabie's House":
		# 		row_values2.account = "4111-001 - Interest on Loans and Advances - NJ - CC - MPConso"
		# 		row_values2.branch = "Garcia's Pawnshop - CC"
		# 		row_values2.cost_center = "1 - Cavite City - MPConso"
		# 	row_values2.debit_in_account_currency = flt(0)
		# 	row_values2.credit_in_account_currency = flt(self.interest)

		# 	row_values3 = doc1.append('accounts', {})
		# 	if self.branch == "Garcia's Pawnshop - CC":
		# 		row_values3.account = "1110-001 - Cash on Hand - Pawnshop - CC - MPConso"
		# 		row_values3.account = "4113-001 - Interest on Past Due Loans - NJ - CC - MPConso"
		# 		row_values3.branch = "Garcia's Pawnshop - CC"
		# 		row_values3.cost_center = "1 - Cavite City - MPConso"
		# 	elif self.branch == "Garcia's Pawnshop - GTC":
		# 		row_values3.account = "1110-002 - Cash on Hand - Pawnshop - GTC - MPConso"
		# 		row_values3.branch = "Garcia's Pawnshop - GTC"
		# 		row_values3.cost_center = "4 - Gen. Trias - MPConso"
		# 	elif self.branch == "Garcia's Pawnshop - MOL":
		# 		row_values3.account = "1110-003 - Cash on Hand - Pawnshop - MOL - MPConso"
		# 		row_values3.branch = "Garcia's Pawnshop - MOL"
		# 		row_values3.cost_center = "6 - Molino - MPConso"
		# 	elif self.branch == "Garcia's Pawnshop - POB":
		# 		row_values3.account = "1110-004 - Cash on Hand - Pawnshop - POB - MPConso"
		# 		row_values3.branch = "Garcia's Pawnshop - POB"
		# 		row_values3.cost_center = "3 - Poblacion - MPConso"
		# 	elif self.branch == "Garcia's Pawnshop - TNZ":
		# 		row_values3.account = "1110-005 - Cash on Hand - Pawnshop - TNZ - MPConso"
		# 		row_values3.branch = "Garcia's Pawnshop - TNZ"
		# 		row_values3.cost_center = "5 - Tanza - MPConso"
		# 	elif self.branch == "Rabie's House":
		# 		row_values3.account = "1110-001 - Cash on Hand - Pawnshop - CC - MPConso"
		# 		row_values3.branch = "Garcia's Pawnshop - CC"
		# 		row_values3.cost_center = "1 - Cavite City - MPConso"
		# 	row_values3.debit_in_account_currency = flt(0)
		# 	row_values3.credit_in_account_currency = flt(self.net_proceeds)

			

			# row_values4 = doc1.append('accounts', {})
			# row_values4.account = "Cash on Hand - Pawnshop - MPConso"
			# row_values4.debit_in_account_currency = flt(15.00)
			# row_values4.credit_in_account_currency = flt(0)

			# row_values5 = doc1.append('accounts', {})
			# row_values5.account = "Service Charge - MPConso"
			# row_values5.debit_in_account_currency = flt(0)
			# row_values5.credit_in_account_currency = flt(15)

			#doc1.save(ignore_permissions=True)
			# doc1.submit()

	# def before_cancel(self):
	# 	name = frappe.db.get_value('Journal Entry', {'reference_document': self.name, "document_status": "Active"}, 'name')
	# 	frappe.db.set_value('Journal Entry', name, 'docstatus', 2)
	# 	frappe.db.commit()