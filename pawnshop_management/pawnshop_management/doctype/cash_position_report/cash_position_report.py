# Copyright (c) 2022, Rabie Moses Santillan and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import flt
from frappe.model.document import Document
from frappe.utils import today

class CashPositionReport(Document):
	def create_inventory_count_document(self):
#A IN count
		a_in_count_of_the_day = frappe.db.count('Pawn Ticket Jewelry', {'date_loan_granted': self.date ,'item_series': 'A', 'branch': self.branch, 'workflow_state': 'Active'}) 
		a_renewed_count_of_the_day = frappe.db.count('Pawn Ticket Jewelry', {'change_status_date': self.date, 'workflow_state': 'Renewed', 'item_series': 'A', 'branch': self.branch})
		a_in_rd_of_the_day = frappe.db.count('Pawn Ticket Jewelry', {'date_loan_granted': self.date ,'item_series': 'A', 'branch': self.branch, 'workflow_state': 'Redeemed'})
		a_in_count = a_in_count_of_the_day - a_renewed_count_of_the_day + a_in_rd_of_the_day
#A IN principal
		a_in_principal_active = frappe.db.get_all('Pawn Ticket Jewelry', filters={"branch": self.branch, "item_series": 'A', "date_loan_granted": self.date, 'workflow_state': 'Active'}, fields=['desired_principal'], pluck='desired_principal')
		a_in_principal_renewed = frappe.db.get_all('Pawn Ticket Jewelry', filters={"branch": self.branch, "item_series": 'A', "change_status_date": self.date, 'workflow_state': 'Renewed'}, fields=['desired_principal'], pluck='desired_principal')	
		a_in_principal_rnwam = frappe.db.get_all('Provisional Receipt', filters={"docstatus": 1, "branch": self.branch, "series": 'A', "pawn_ticket_type": 'Pawn Ticket Jewelry', "transaction_type": 'Renewal w/ Amortization'}, fields=['additional_amortization'], pluck='additional_amortization')
		a_in_rd = frappe.db.get_all('Pawn Ticket Jewelry', filters={"branch": self.branch, "item_series": 'A', "date_loan_granted": self.date, 'workflow_state': 'Redeemed'}, fields=['desired_principal'], pluck='desired_principal')
		sum_active_in = 0
		for record in a_in_principal_active:
			sum_active_in += record
		sum_renewed_in = 0
		for record in a_in_principal_renewed:
			sum_renewed_in += record
		sum_rd_in_a = 0
		for record in a_in_rd:
			sum_rd_in_a += record
		sum_rn_amort_a = 0
		for record in a_in_principal_rnwam:
			sum_rn_amort_a += record	
		a_in_principal = sum_active_in - sum_renewed_in + sum_rd_in_a + sum_rn_amort_a
#A OUT count
		a_out_count = frappe.db.count('Pawn Ticket Jewelry', {'change_status_date': self.date, 'workflow_state': 'Redeemed', 'item_series': 'A', 'branch': self.branch})
#A OUT principal
		a_principal_redeemed = frappe.db.get_all('Pawn Ticket Jewelry', filters={"branch": self.branch, "item_series": 'A', "change_status_date": self.date, 'workflow_state': 'Redeemed'}, fields=['desired_principal'], pluck='desired_principal')
		a_out_principal = 0
		for record in a_principal_redeemed:
			a_out_principal += record
#A PO count
		a_pulled_out_of_the_day = frappe.db.count('Pawn Ticket Jewelry', {'change_status_date': self.date, 'item_series': 'A', 'workflow_state': 'Pulled Out', 'branch': self.branch})
#A PO principal
		a_principal_pulled_out = frappe.db.get_all('Pawn Ticket Jewelry', filters={"branch": self.branch, "item_series": 'A', "change_status_date": self.date, 'workflow_state': 'Pulled Out'}, fields=['desired_principal'], pluck='desired_principal')
		a_po_principal = 0
		for record in a_principal_pulled_out:
			a_po_principal += record
#A RET count
		a_returned_of_the_day = frappe.db.count('Pawn Ticket Jewelry', {'change_status_date': self.date, 'item_series': 'A', 'workflow_state': 'Returned', 'branch': self.branch})
#A RET principal
		a_principal_returned = frappe.db.get_all('Pawn Ticket Jewelry', filters={"branch": self.branch, "item_series": 'A', "change_status_date": self.date, 'workflow_state': 'Returned'}, fields=['desired_principal'], pluck='desired_principal')
		a_ret_principal = 0
		for record in a_principal_returned:
			a_ret_principal += record
#A Total
		a_total_active = frappe.db.count('Pawn Ticket Jewelry', {'date_loan_granted': ['<=', self.date], 'item_series': 'A', 'workflow_state': ['in', ['Active', 'Expired', 'Returned']], 'branch': self.branch})
#B IN count
		b_in_count_of_the_day = frappe.db.count('Pawn Ticket Jewelry', {'date_loan_granted': self.date ,'item_series': 'B', 'branch': self.branch, 'workflow_state': 'Active'})
		b_renewed_count_of_the_day = frappe.db.count('Pawn Ticket Jewelry', {'change_status_date': self.date, 'workflow_state': 'Renewed', 'item_series': 'B', 'branch': self.branch})
		b_in_rd_of_the_day = frappe.db.count('Pawn Ticket Jewelry', {'date_loan_granted': self.date ,'item_series': 'B', 'branch': self.branch, 'workflow_state': 'Redeemed'})
		b_in_count = b_in_count_of_the_day - b_renewed_count_of_the_day + b_in_rd_of_the_day
#B IN principal
		b_in_principal_active = frappe.db.get_all('Pawn Ticket Jewelry', filters={"branch": self.branch, "item_series": 'B', "date_loan_granted": self.date, 'workflow_state': 'Active'}, fields=['desired_principal'], pluck='desired_principal')
		b_in_principal_renewed = frappe.db.get_all('Pawn Ticket Jewelry', filters={"branch": self.branch, "item_series": 'B', "change_status_date": self.date, 'workflow_state': 'Renewed'}, fields=['desired_principal'], pluck='desired_principal')	
		b_in_principal_rnwam = frappe.db.get_all('Provisional Receipt', filters={"docstatus": 1, "branch": self.branch, "series": 'B', "pawn_ticket_type": 'Pawn Ticket Jewelry', "transaction_type": 'Renewal w/ Amortization'}, fields=['additional_amortization'], pluck='additional_amortization')
		b_in_rd = frappe.db.get_all('Pawn Ticket Jewelry', filters={"branch": self.branch, "item_series": 'B', "date_loan_granted": self.date, 'workflow_state': 'Redeemed'}, fields=['desired_principal'], pluck='desired_principal')
		sum_active_in_b = 0
		for record in b_in_principal_active:
			sum_active_in_b += record
		sum_renewed_in_b = 0
		for record in b_in_principal_renewed:
			sum_renewed_in_b += record
		sum_rd_in_b = 0
		for record in b_in_rd:
			sum_rd_in_b += record
		sum_rn_amort_b = 0
		for record in b_in_principal_rnwam:
			sum_rn_amort_b += record	
		b_in_principal = sum_active_in_b - sum_renewed_in_b + sum_rd_in_b + sum_rn_amort_b
#B OUT count
		b_out_count = frappe.db.count('Pawn Ticket Jewelry', {'change_status_date': self.date, 'workflow_state': 'Redeemed', 'item_series': 'B', 'branch': self.branch})
#B OUT principal
		b_principal_redeemed = frappe.db.get_all('Pawn Ticket Jewelry', filters={"branch": self.branch, "item_series": 'B', "change_status_date": self.date, 'workflow_state': 'Redeemed'}, fields=['desired_principal'], pluck='desired_principal')
		b_out_principal = 0
		for record in b_principal_redeemed:
			b_out_principal += record
#B PO count
		b_pulled_out_of_the_day = frappe.db.count('Pawn Ticket Jewelry', {'change_status_date': self.date, 'item_series': 'B', 'workflow_state': 'Pulled Out', 'branch': self.branch})
#B PO principal
		b_principal_pulled_out = frappe.db.get_all('Pawn Ticket Jewelry', filters={"branch": self.branch, "item_series": 'B', "change_status_date": self.date, 'workflow_state': 'Pulled Out'}, fields=['desired_principal'], pluck='desired_principal')
		b_po_principal = 0
		for record in b_principal_pulled_out:
			b_po_principal += record
#B RET count
		b_returned_of_the_day = frappe.db.count('Pawn Ticket Jewelry', {'change_status_date': self.date, 'item_series': 'B', 'workflow_state': 'Returned', 'branch': self.branch})
#B RET principal
		b_principal_returned = frappe.db.get_all('Pawn Ticket Jewelry', filters={"branch": self.branch, "item_series": 'B', "change_status_date": self.date, 'workflow_state': 'Returned'}, fields=['desired_principal'], pluck='desired_principal')
		b_ret_principal = 0
		for record in b_principal_returned:
			b_ret_principal += record
#B Total
		b_total_active = frappe.db.count('Pawn Ticket Jewelry', {'date_loan_granted': ['<=', self.date], 'item_series': 'B', 'workflow_state': ['in', ['Active', 'Expired', 'Returned']], 'branch': self.branch})
#BNJ IN count
		nj_in_count_of_the_day = frappe.db.count('Pawn Ticket Non Jewelry', {'date_loan_granted': self.date , 'workflow_state': 'Active', 'branch': self.branch})
		nj_renewed_count_of_the_day = frappe.db.count('Pawn Ticket Non Jewelry', {'change_status_date': self.date, 'workflow_state': 'Renewed', 'branch': self.branch})
		bnj_in_rd_of_the_day = frappe.db.count('Pawn Ticket Non Jewelry', {'date_loan_granted': self.date , 'branch': self.branch, 'workflow_state': 'Redeemed'})
		nj_in_count = nj_in_count_of_the_day - nj_renewed_count_of_the_day + bnj_in_rd_of_the_day
#BNJ IN principal
		bnj_in_principal_active = frappe.db.get_all('Pawn Ticket Non Jewelry', filters={"branch": self.branch, "date_loan_granted": self.date, 'workflow_state': 'Active'}, fields=['desired_principal'], pluck='desired_principal')
		bnj_in_principal_renewed = frappe.db.get_all('Pawn Ticket Non Jewelry', filters={"branch": self.branch, "change_status_date": self.date, 'workflow_state': 'Renewed'}, fields=['desired_principal'], pluck='desired_principal')	
		bnj_in_principal_rnwam = frappe.db.get_all('Provisional Receipt', filters={"docstatus": 1, "branch": self.branch, "series": 'B', "pawn_ticket_type": 'Pawn Ticket Non Jewelry', "transaction_type": 'Renewal w/ Amortization'}, fields=['additional_amortization'], pluck='additional_amortization')
		bnj_in_rd = frappe.db.get_all('Pawn Ticket Non Jewelry', filters={"branch": self.branch, "date_loan_granted": self.date, 'workflow_state': 'Redeemed'}, fields=['desired_principal'], pluck='desired_principal')
		sum_active_in_bnj = 0
		for record in bnj_in_principal_active:
			sum_active_in_bnj += record
		sum_renewed_in_bnj = 0
		for record in bnj_in_principal_renewed:
			sum_renewed_in_bnj += record
		sum_rd_in_bnj = 0
		for record in bnj_in_rd:
			sum_rd_in_bnj += record	
		sum_rn_amort_bnj = 0
		for record in bnj_in_principal_rnwam:
			sum_rn_amort_bnj += record	
		bnj_in_principal = sum_active_in_bnj - sum_renewed_in_bnj + sum_rd_in_bnj + sum_rn_amort_bnj
#BNJ OUT count
		nj_out_count = frappe.db.count('Pawn Ticket Non Jewelry', {'change_status_date': self.date, 'workflow_state': 'Redeemed', 'branch': self.branch})
#BNJ OUT principal
		bnj_principal_redeemed = frappe.db.get_all('Pawn Ticket Non Jewelry', filters={"branch": self.branch, "change_status_date": self.date, 'workflow_state': 'Redeemed'}, fields=['desired_principal'], pluck='desired_principal')
		bnj_out_principal = 0
		for record in bnj_principal_redeemed:
			bnj_out_principal += record
#BNJ PO count
		nj_pulled_out_of_the_day = frappe.db.count('Pawn Ticket Non Jewelry', {'change_status_date': self.date, 'workflow_state': 'Pulled Out', 'branch': self.branch})
#BNJ PO principal
		bnj_principal_pulled_out = frappe.db.get_all('Pawn Ticket Non Jewelry', filters={"branch": self.branch, "change_status_date": self.date, 'workflow_state': 'Pulled Out'}, fields=['desired_principal'], pluck='desired_principal')
		bnj_po_principal = 0
		for record in bnj_principal_pulled_out:
			bnj_po_principal += record
#BNJ RET count
		nj_returned_of_the_day = frappe.db.count('Pawn Ticket Non Jewelry', {'change_status_date': self.date, 'workflow_state': 'Returned', 'branch': self.branch})
#BNJ RET principal
		bnj_principal_returned = frappe.db.get_all('Pawn Ticket Non Jewelry', filters={"branch": self.branch, "change_status_date": self.date, 'workflow_state': 'Returned'}, fields=['desired_principal'], pluck='desired_principal')
		bnj_ret_principal = 0
		for record in bnj_principal_returned:
			bnj_ret_principal += record
#BNJ Total
		nj_total_active = frappe.db.count('Pawn Ticket Non Jewelry', {'date_loan_granted': ['<=', self.date], 'workflow_state': ['in', ['Active', 'Expired', 'Returned']], 'branch': self.branch})

#assign to document fields
		invetory_count_doc = frappe.new_doc('Inventory Count')
		invetory_count_doc.date = self.date
		invetory_count_doc.branch = self.branch
		invetory_count_doc.in_count_a = a_in_count
		invetory_count_doc.principal_in_a = a_in_principal
		invetory_count_doc.out_count_a = a_out_count
		invetory_count_doc.principal_out_a = a_out_principal
		invetory_count_doc.returned_a = a_returned_of_the_day
		invetory_count_doc.principal_ret_a = a_ret_principal
		invetory_count_doc.pulled_out_a = a_pulled_out_of_the_day
		invetory_count_doc.principal_po_a = a_po_principal
		invetory_count_doc.total_a = a_total_active

		invetory_count_doc.in_count_b = b_in_count
		invetory_count_doc.principal_in_b = b_in_principal
		invetory_count_doc.out_count_b = b_out_count
		invetory_count_doc.principal_out_b = b_out_principal
		invetory_count_doc.returned_b = b_returned_of_the_day
		invetory_count_doc.principal_ret_b = b_ret_principal
		invetory_count_doc.pulled_out_b = b_pulled_out_of_the_day
		invetory_count_doc.principal_po_b = b_po_principal
		invetory_count_doc.total_b = b_total_active
		
		invetory_count_doc.in_count_nj = nj_in_count
		invetory_count_doc.principal_in_nj = bnj_in_principal
		invetory_count_doc.out_count_nj = nj_out_count
		invetory_count_doc.principal_out_nj = bnj_out_principal
		invetory_count_doc.pulled_out_nj = nj_pulled_out_of_the_day
		invetory_count_doc.principal_po_nj = bnj_po_principal
		invetory_count_doc.returned_nj = nj_returned_of_the_day
		invetory_count_doc.principal_ret_nj = bnj_ret_principal
		invetory_count_doc.total_nj = nj_total_active
		invetory_count_doc.save(ignore_permissions=True)
# Added Comment
	def before_save(self):
		# if self.shortage_overage > 0:
		# 	doc1 = frappe.new_doc('Journal Entry')
		# 	doc1.voucher_type = 'Journal Entry'
		# 	doc1.company = 'MP Consolidated'
		# 	doc1.posting_date = self.date
		# 	doc1.reference_doctype = "Cash Position Report"
		# 	doc1.reference_document = self.name

		# 	row_values1 = doc1.append('accounts', {})
		# 	if self.branch == "Garcia's Pawnshop - CC":
		# 		row_values1.account = "Cash/Shortage Overage - Pawnshop - CC - MPConso"
		# 	elif self.branch == "Garcia's Pawnshop - GTC":
		# 		row_values1.account = "5300-002 - Cash Shortage / Overage - Pawnshop - GTC - MPConso"
		# 		row_values1.branch = "Garcia's Pawnshop - GTC"
		# 		row_values1.cost_center = "4 - Gen. Trias - MPConso"
		# 	elif self.branch == "Garcia's Pawnshop - MOL":
		# 		row_values1.account = "Cash/Shortage Overage - Pawnshop - MOL - MPConso"
		# 	elif self.branch == "Garcia's Pawnshop - POB":
		# 		row_values1.account = "Cash/Shortage Overage - Pawnshop - POB - MPConso"
		# 	elif self.branch == "Garcia's Pawnshop - TNZ":
		# 		row_values1.account = "Cash/Shortage Overage - Pawnshop - TNZ - MPConso"
		# 	elif self.branch == "Rabie's House":
		# 		row_values1.account = "Cash/Shortage Overage - Pawnshop - CC - MPConso"
		# 	row_values1.debit_in_account_currency = flt(self.shortage_overage)
		# 	row_values1.credit_in_account_currency = flt(0)

		# 	row_values2 = doc1.append('accounts', {})
		# 	if self.branch == "Garcia's Pawnshop - CC":
		# 		row_values2.account = "1110-001 - Cash on Hand - Pawnshop - CC - MPConso"
		# 	elif self.branch == "Garcia's Pawnshop - GTC":
		# 		row_values2.account = "1110-002 - Cash on Hand - Pawnshop - GTC - MPConso"
		# 		row_values2.branch = "Garcia's Pawnshop - GTC"
		# 		row_values2.cost_center = "4 - Gen. Trias - MPConso"
		# 	elif self.branch == "Garcia's Pawnshop - MOL":
		# 		row_values2.account = "1110-003 - Cash on Hand - Pawnshop - MOL - MPConso"
		# 	elif self.branch == "Garcia's Pawnshop - POB":
		# 		row_values2.account = "1110-004 - Cash on Hand - Pawnshop - POB - MPConso"
		# 	elif self.branch == "Garcia's Pawnshop - TNZ":
		# 		row_values2.account = "1110-005 - Cash on Hand - Pawnshop - TNZ - MPConso"
		# 	elif self.branch == "Rabie's House":
		# 		row_values2.account = "1110-001 - Cash on Hand - Pawnshop - CC - MPConso"
		# 	row_values2.debit_in_account_currency = flt(0)
		# 	row_values2.credit_in_account_currency = flt(self.shortage_overage)

		# 	doc1.save(ignore_permissions=True)
		# 	doc1.submit()
		# elif self.shortage_overage < 0:
		# 	doc1 = frappe.new_doc('Journal Entry')
		# 	doc1.voucher_type = 'Journal Entry'
		# 	doc1.company = 'MP Consolidated'
		# 	doc1.posting_date = self.date
		# 	doc1.reference_doctype = "Cash Position Report"
		# 	doc1.reference_document = self.name

		# 	row_values1 = doc1.append('accounts', {})
		# 	if self.branch == "Garcia's Pawnshop - CC":
		# 		row_values1.account = "1110-001 - Cash on Hand - Pawnshop - CC - MPConso"
		# 	elif self.branch == "Garcia's Pawnshop - GTC":
		# 		row_values1.account = "1110-002 - Cash on Hand - Pawnshop - GTC - MPConso"
		# 		row_values1.branch = "Garcia's Pawnshop - GTC"
		# 		row_values1.cost_center = "4 - Gen. Trias - MPConso"
		# 	elif self.branch == "Garcia's Pawnshop - MOL":
		# 		row_values1.account = "1110-003 - Cash on Hand - Pawnshop - MOL - MPConso"
		# 	elif self.branch == "Garcia's Pawnshop - POB":
		# 		row_values1.account = "1110-004 - Cash on Hand - Pawnshop - POB - MPConso"
		# 	elif self.branch == "Garcia's Pawnshop - TNZ":
		# 		row_values1.account = "1110-005 - Cash on Hand - Pawnshop - TNZ - MPConso"
		# 	elif self.branch == "Rabie's House":
		# 		row_values1.account = "1110-001 - Cash on Hand - Pawnshop - CC - MPConso"
		# 	row_values1.debit_in_account_currency = flt(0)
		# 	row_values1.credit_in_account_currency = flt(abs(self.shortage_overage))

		# 	row_values2 = doc1.append('accounts', {})
		# 	if self.branch == "Garcia's Pawnshop - CC":
		# 		row_values2.account = "Cash/Shortage Overage - Pawnshop - CC - MPConso"
		# 	elif self.branch == "Garcia's Pawnshop - GTC":
		# 		row_values2.account = "5300-002 - Cash Shortage / Overage - Pawnshop - GTC - MPConso"
		# 		row_values2.branch = "Garcia's Pawnshop - GTC"
		# 		row_values2.cost_center = "4 - Gen. Trias - MPConso"
		# 	elif self.branch == "Garcia's Pawnshop - MOL":
		# 		row_values2.account = "Cash/Shortage Overage - Pawnshop - MOL - MPConso"
		# 	elif self.branch == "Garcia's Pawnshop - POB":
		# 		row_values2.account = "Cash/Shortage Overage - Pawnshop - POB - MPConso"
		# 	elif self.branch == "Garcia's Pawnshop - TNZ":
		# 		row_values2.account = "Cash/Shortage Overage - Pawnshop - TNZ - MPConso"
		# 	elif self.branch == "Rabie's House":
		# 		row_values2.account = "Cash/Shortage Overage - Pawnshop - CC - MPConso"
		# 	row_values2.debit_in_account_currency = flt(abs(self.shortage_overage))
		# 	row_values2.credit_in_account_currency = flt(0)

		# 	doc1.save(ignore_permissions=True)
		# 	doc1.submit()
		self.create_inventory_count_document()

			