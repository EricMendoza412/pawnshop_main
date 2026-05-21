# Copyright (c) 2022, Rabie Moses Santillan and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import flt
from frappe.model.document import Document
from frappe.utils import today
from pawnshop_management.pawnshop_management.report.vc_report.vc_report import execute as execute_vc_report


def _report_rows(report_date, branch):
	filters = frappe._dict({
		"change_status_date": report_date,
		"branch": branch.replace("'", "\\'") if branch else branch,
	})
	_columns, data = execute_vc_report(filters)
	return data


def _same_date(first, second):
	return str(first or "")[:10] == str(second or "")[:10]


def _amount(value):
	return flt(value or 0)


def _principal_amount(row):
	principal = row.get("principal_amount")
	if principal is not None:
		return _amount(principal)

	return _amount(row.get("change_status_date"))


def _new_net_proceeds(row, fallback):
	new_net_proceeds = row.get("new_net_proceeds")
	if new_net_proceeds is not None:
		return _amount(new_net_proceeds)

	return fallback


def _append_log_row(doc, table, source, section, **values):
	row = doc.append(table, {})
	row.section = section
	row.series = values.get("series", source.get("item_series"))
	row.pawn_ticket_type = values.get("pawn_ticket_type", source.get("inventory_tracking_no") or source.get("pt_type"))
	row.transaction_date = values.get("transaction_date", source.get("date_loan_granted"))
	row.inventory_no = values.get("inventory_no", source.get("inventory_tracking_no"))
	row.pawn_ticket = values.get("pawn_ticket", source.get("pawn_ticket"))
	row.old_pawn_ticket = values.get("old_pawn_ticket", source.get("old_pawn_ticket"))
	row.new_pawn_ticket = values.get("new_pawn_ticket")
	row.principal = _amount(values.get("principal", source.get("desired_principal")))
	row.net_proceeds = _amount(values.get("net_proceeds", source.get("net_proceeds")))
	row.old_principal = _amount(values.get("old_principal"))
	row.old_net_proceeds = _amount(values.get("old_net_proceeds"))
	row.new_principal = _amount(values.get("new_principal"))
	row.accrued_interest = _amount(values.get("accrued_interest", source.get("interest_payment")))
	row.short_term_discount = _amount(values.get("short_term_discount", source.get("discount")))
	row.other_discount = _amount(values.get("other_discount", source.get("other_discount_tawad")))
	row.amortization_amount = _amount(values.get("amortization_amount"))
	row.partial_interest_paid = _amount(values.get("partial_interest_paid"))
	row.status = values.get("status", source.get("workflow_state"))
	return row


def create_transaction_log_for_cash_position_report(cash_position_report):
	if frappe.db.exists("Pawnshop Transaction Log", {"cash_position_report": cash_position_report.name}):
		return

	data = _report_rows(cash_position_report.date, cash_position_report.branch)
	log = frappe.new_doc("Pawnshop Transaction Log")
	log.date = cash_position_report.date
	log.branch = cash_position_report.branch
	log.cash_position_report = cash_position_report.name

	totals = frappe._dict(
		count=0, countB=0, countNJ=0,
		countRD=0, countRDB=0, countRDBNJ=0,
		sumNPro=0, sumNProB=0, sumNProNJ=0,
		sum=0, sumB=0, sumBNJ=0,
		sumNPRDA=0, sumNPRDB=0, sumNPRDBNJ=0,
		sumAIRDA=0, sumAIRDB=0, sumAIRDBNJ=0,
		sumDRDA=0, sumDRDB=0, sumDRDBNJ=0,
		sumODTA=0, sumODTB=0, sumODTBNJ=0,
		sumRN=0, sumRNB=0, sumRNNJ=0,
		sumNPA=0, sumNPB=0, sumNPNJ=0,
		sumAI=0, sumAIB=0, sumAINJ=0,
		sumD=0, sumDB=0, sumDNJ=0,
		sumwRN=0, sumwRNB=0, sumwRNNJ=0,
		sumwNPA=0, sumwNPB=0, sumwNPNJ=0,
		sumwNPRA=0, sumwNPRB=0, sumwNPRNJ=0,
		sumwAI=0, sumwAIB=0, sumwAINJ=0,
		sumwD=0, sumwDB=0, sumwDNJ=0,
		sumAmort=0, sumAmortB=0, sumAmortBNJ=0,
		sumPrincipal=0, sumPrincipalB=0, sumPrincipalBNJ=0,
		sumPint=0, sumPintB=0,
		NJRNA_NP=0, sumComAccInt=0,
	)

	for row in data:
		workflow_state = row.get("workflow_state")
		item_series = row.get("item_series")
		pt_type = row.get("pt_type")
		pawn_ticket_type = row.get("inventory_tracking_no")
		principal = _principal_amount(row)
		interest = _amount(row.get("interest"))
		net_proceeds = _amount(row.get("net_proceeds"))
		desired_principal = _amount(row.get("desired_principal"))
		net_from_principal = principal - interest

		if workflow_state == "Rejected":
			_append_log_row(
				log, "cancelled_pawn_tickets", row, "Cancelled Pawn Tickets",
				principal=desired_principal, net_proceeds=net_proceeds, status=workflow_state,
			)

		if row.get("old_pawn_ticket") == "" and (
			workflow_state == "Active" or (
				workflow_state == "Redeemed" and _same_date(row.get("date_loan_granted"), row.get("change_status_date"))
			)
		):
			if item_series == "A":
				_append_log_row(log, "new_sangla", row, "New Sangla", series="A")
				totals.count += 1
				totals.sumNPro += net_proceeds
			elif item_series == "B" and pt_type == "J":
				_append_log_row(log, "new_sangla", row, "New Sangla", series="B")
				totals.countB += 1
				totals.sumNProB += net_proceeds
			elif pt_type == "NJ":
				_append_log_row(log, "new_sangla", row, "New Sangla", series="NJ")
				totals.countNJ += 1
				totals.sumNProNJ += net_proceeds

		if workflow_state == "Redemption":
			if item_series == "A":
				_append_log_row(log, "redeemed_pawn_tickets", row, "Redeemed Pawn Tickets", series="A", inventory_no=row.get("inventory_tracking"), principal=principal, net_proceeds=net_from_principal)
				totals.countRD += 1
				totals.sum += principal
				totals.sumNPRDA += net_from_principal
				totals.sumAIRDA += _amount(row.get("interest_payment"))
				totals.sumDRDA += _amount(row.get("discount"))
				totals.sumODTA += _amount(row.get("other_discount_tawad"))
			elif item_series == "B" and pawn_ticket_type == "Pawn Ticket Jewelry":
				_append_log_row(log, "redeemed_pawn_tickets", row, "Redeemed Pawn Tickets", series="B", inventory_no=row.get("inventory_tracking"), principal=principal, net_proceeds=net_from_principal)
				totals.countRDB += 1
				totals.sumB += principal
				totals.sumNPRDB += net_from_principal
				totals.sumAIRDB += _amount(row.get("interest_payment"))
				totals.sumDRDB += _amount(row.get("discount"))
				totals.sumODTB += _amount(row.get("other_discount_tawad"))
			elif item_series == "B" and pawn_ticket_type == "Pawn Ticket Non Jewelry":
				_append_log_row(log, "redeemed_pawn_tickets", row, "Redeemed Pawn Tickets", series="NJ", inventory_no=row.get("inventory_tracking"), principal=principal, net_proceeds=net_from_principal)
				totals.countRDBNJ += 1
				totals.sumBNJ += principal
				totals.sumNPRDBNJ += net_from_principal
				totals.sumAIRDBNJ += _amount(row.get("interest_payment"))
				totals.sumDRDBNJ += _amount(row.get("discount"))
				totals.sumODTBNJ += _amount(row.get("other_discount_tawad"))

		if workflow_state == "Renewal":
			if item_series == "A":
				_append_log_row(log, "renewed_pawn_tickets", row, "Renewed Pawn Tickets", series="A", inventory_no=row.get("inventory_tracking"), old_pawn_ticket=row.get("pawn_ticket"), new_pawn_ticket=row.get("old_pawn_ticket"), principal=principal, net_proceeds=net_from_principal)
				totals.sumRN += principal
				totals.sumNPA += net_from_principal
				totals.sumAI += _amount(row.get("interest_payment"))
				totals.sumD += _amount(row.get("other_discount_tawad"))
			elif item_series == "B" and pawn_ticket_type == "Pawn Ticket Jewelry":
				_append_log_row(log, "renewed_pawn_tickets", row, "Renewed Pawn Tickets", series="B", inventory_no=row.get("inventory_tracking"), old_pawn_ticket=row.get("pawn_ticket"), new_pawn_ticket=row.get("old_pawn_ticket"), principal=principal, net_proceeds=net_from_principal)
				totals.sumRNB += principal
				totals.sumNPB += net_from_principal
				totals.sumAIB += _amount(row.get("interest_payment"))
				totals.sumDB += _amount(row.get("other_discount_tawad"))
			elif item_series == "B" and pawn_ticket_type == "Pawn Ticket Non Jewelry":
				_append_log_row(log, "renewed_pawn_tickets", row, "Renewed Pawn Tickets", series="NJ", inventory_no=row.get("inventory_tracking"), old_pawn_ticket=row.get("pawn_ticket"), new_pawn_ticket=row.get("old_pawn_ticket"), principal=principal, net_proceeds=net_from_principal)
				totals.sumRNNJ += principal
				totals.sumNPNJ += net_from_principal
				totals.sumAINJ += _amount(row.get("interest_payment"))
				totals.sumDNJ += _amount(row.get("other_discount_tawad"))

		if workflow_state == "Renewal w/ Amortization":
			new_principal = principal - desired_principal
			new_net_proceeds = _new_net_proceeds(row, net_from_principal)
			if item_series == "A":
				_append_log_row(log, "renewed_with_amortization", row, "Renewed Pawn Tickets with Amortization", series="A", inventory_no=row.get("inventory_tracking"), old_pawn_ticket=row.get("pawn_ticket"), new_pawn_ticket=row.get("old_pawn_ticket"), old_principal=principal, amortization_amount=desired_principal, old_net_proceeds=new_net_proceeds, new_principal=new_principal)
				totals.sumwRN += principal
				totals.sumwNPA += new_net_proceeds
				totals.sumwNPRA += new_principal
				totals.sumwAI += _amount(row.get("interest_payment"))
				totals.sumwD += _amount(row.get("other_discount_tawad"))
			elif item_series == "B" and pawn_ticket_type == "Pawn Ticket Jewelry":
				_append_log_row(log, "renewed_with_amortization", row, "Renewed Pawn Tickets with Amortization", series="B", inventory_no=row.get("inventory_tracking"), old_pawn_ticket=row.get("pawn_ticket"), new_pawn_ticket=row.get("old_pawn_ticket"), old_principal=principal, amortization_amount=desired_principal, old_net_proceeds=new_net_proceeds, new_principal=new_principal)
				totals.sumwRNB += principal
				totals.sumwNPB += new_net_proceeds
				totals.sumwNPRB += new_principal
				totals.sumwAIB += _amount(row.get("interest_payment"))
				totals.sumwDB += _amount(row.get("other_discount_tawad"))
			elif item_series == "B" and pawn_ticket_type == "Pawn Ticket Non Jewelry":
				_append_log_row(log, "renewed_with_amortization", row, "Renewed Pawn Tickets with Amortization", series="NJ", inventory_no=row.get("inventory_tracking"), old_pawn_ticket=row.get("pawn_ticket"), new_pawn_ticket=row.get("old_pawn_ticket"), old_principal=principal, amortization_amount=desired_principal, old_net_proceeds=new_net_proceeds, new_principal=new_principal)
				totals.sumwRNNJ += principal
				totals.sumwNPNJ += new_net_proceeds
				totals.sumwNPRNJ += new_principal
				totals.sumwAINJ += _amount(row.get("interest_payment"))
				totals.sumwDNJ += _amount(row.get("other_discount_tawad"))

		if workflow_state == "Amortization":
			new_principal = principal - desired_principal
			if item_series == "A":
				_append_log_row(log, "amortizations_only", row, "Amortizations Only", series="A", inventory_no=row.get("inventory_tracking"), amortization_amount=desired_principal, new_principal=new_principal)
				totals.sumAmort += desired_principal
				totals.sumPrincipal += new_principal
			elif item_series == "B" and pawn_ticket_type == "Pawn Ticket Jewelry":
				_append_log_row(log, "amortizations_only", row, "Amortizations Only", series="B", inventory_no=row.get("inventory_tracking"), amortization_amount=desired_principal, new_principal=new_principal)
				totals.sumAmortB += desired_principal
				totals.sumPrincipalB += new_principal
			elif item_series == "B" and pawn_ticket_type == "Pawn Ticket Non Jewelry":
				_append_log_row(log, "amortizations_only", row, "Amortizations Only", series="NJ", inventory_no=row.get("inventory_tracking"), amortization_amount=desired_principal, new_principal=new_principal)
				totals.sumAmortBNJ += desired_principal
				totals.sumPrincipalBNJ += new_principal

		if workflow_state == "Interest Payment":
			if item_series == "A":
				_append_log_row(log, "interest_payments", row, "Interest Payment", series="A", partial_interest_paid=net_proceeds)
				totals.sumPint += net_proceeds
			elif item_series == "B":
				_append_log_row(log, "interest_payments", row, "Interest Payment", series="B", partial_interest_paid=net_proceeds)
				totals.sumPintB += net_proceeds

		if _amount(row.get("previous_interest_payment")) > 0:
			totals.sumComAccInt += _amount(row.get("previous_interest_payment"))
		if _same_date(row.get("dummy_date"), cash_position_report.date) and workflow_state == "Amortization" and pawn_ticket_type == "Pawn Ticket Non Jewelry" and principal:
			totals.NJRNA_NP += net_proceeds * (1 - (interest / principal))
		if pt_type == "NJ" and row.get("old_pawn_ticket") != "":
			totals.NJRNA_NP += net_proceeds

	total_hulog_with_rn = totals.sumwRN + totals.sumwRNB + totals.sumwRNNJ - totals.sumwNPRA - totals.sumwNPRB - totals.sumwNPRNJ
	summary = [
		("New Sangla Count", totals.count + totals.countB + totals.countNJ),
		("Redemption Count", totals.countRD + totals.countRDB + totals.countRDBNJ),
		("New Sangla Net Proceeds (J)", totals.sumNPro + totals.sumNProB),
		("New Sangla Net Proceeds (NJ)", totals.sumNProNJ),
		("Hulog w/out Renew (Amortization Only)", totals.sumAmort + totals.sumAmortB + totals.sumAmortBNJ),
		("Additional Pawn", totals.sumNPro + totals.sumNProB + totals.sumNProNJ + totals.sumNPA + totals.sumNPB + (((totals.sumwNPRA + totals.sumwNPRB) * 0.95) + totals.NJRNA_NP)),
		("Additional Redeem", totals.sum + totals.sumAIRDA - totals.sumODTA + totals.sumB + totals.sumAIRDB - totals.sumODTB + totals.sumBNJ + totals.sumAIRDBNJ - totals.sumODTBNJ + totals.sumRN + totals.sumAI - totals.sumD + totals.sumRNB + totals.sumAIB - totals.sumDB + totals.sumRNNJ + totals.sumAINJ - totals.sumDNJ + totals.sumwRN + totals.sumwAI - totals.sumwD + totals.sumwRNB + totals.sumwAIB - totals.sumwDB + totals.sumwRNNJ + totals.sumwAINJ - totals.sumwDNJ - total_hulog_with_rn),
		("J Principal(Tubos)", totals.sumAmort + totals.sumAmortB + totals.sum + totals.sumB + (totals.sumwRN - totals.sumwNPRA) + (totals.sumwRNB - totals.sumwNPRB)),
		("NJ Principal(Tubos)", totals.sumAmortBNJ + totals.sumBNJ + (totals.sumwRNNJ - totals.sumwNPRNJ)),
		("Additional Partial Payment", totals.sumPint + totals.sumPintB),
		("Total Discount", totals.sumDRDA + totals.sumDRDB + totals.sumDRDBNJ),
		("Hulog w/ Renew", total_hulog_with_rn),
		("Completion of Accrued Interest", totals.sumComAccInt),
	]
	for description, total in summary:
		summary_row = log.append("summary", {})
		summary_row.description = description
		summary_row.total = _amount(total)

	log.save(ignore_permissions=True)
	return log

@frappe.whitelist()
def check_new_submissions(loaded_at: str, branch: str = None):
	"""
	Returns whether there are any submitted docs after `loaded_at`.
	Uses `modified` as a practical proxy for 'submitted time' (submit updates modified).
	"""
	doctypes_to_check = ["Pawn Ticket Jewelry", "Pawn Ticket Non Jewelry", "Agreement to Sell", "Provisional Receipt", "Subastado Sales Commissions", "Fund Transfer", "Acknowledgement Receipt" ]
	filters_common = {"docstatus": ["!=", 2]}
	details = []

	# Optional scoping
	if branch:
		filters_common["branch"] = branch

	for dt in doctypes_to_check:
		# clone base filters and add modified > loaded_at
		filters = filters_common.copy()
		filters["modified"] = [">", loaded_at]

		# If you only need to know existence, db.exists is super fast:
		# name = frappe.db.exists(dt, filters)
		# If you want details for the message:
		rows = frappe.get_all(
			dt,
			filters=filters,
			fields=["name", "modified"],
			order_by="modified asc",
			limit=10,  # cap for message; increase if needed
		)
		for row in rows:
			details.append({"doctype": dt, "name": row.name, "modified": row.modified})

	return {"has_new": len(details) > 0, "details": details}

class CashPositionReport(Document):
	def on_submit(self):
		create_transaction_log_for_cash_position_report(self)

	def create_inventory_count_document(self):
#A IN count
		a_in_count_of_the_day = frappe.db.count('Pawn Ticket Jewelry', {'date_loan_granted': self.date ,'item_series': 'A', 'branch': self.branch, 'workflow_state': 'Active'}) 
		a_renewed_count_of_the_day = frappe.db.count('Pawn Ticket Jewelry', {'change_status_date': self.date, 'workflow_state': 'Renewed', 'item_series': 'A', 'branch': self.branch})
		a_in_rd_of_the_day = frappe.db.count('Pawn Ticket Jewelry', {'date_loan_granted': self.date ,'item_series': 'A', 'branch': self.branch, 'workflow_state': 'Redeemed'})
		a_in_count = a_in_count_of_the_day - a_renewed_count_of_the_day + a_in_rd_of_the_day
#A IN principal
		a_in_principal_active = frappe.db.get_all('Pawn Ticket Jewelry', filters={"branch": self.branch, "item_series": 'A', "date_loan_granted": self.date, 'workflow_state': 'Active'}, fields=['desired_principal'], pluck='desired_principal')
		a_in_principal_renewed = frappe.db.get_all('Pawn Ticket Jewelry', filters={"branch": self.branch, "item_series": 'A', "change_status_date": self.date, 'workflow_state': 'Renewed'}, fields=['desired_principal'], pluck='desired_principal')	
		a_in_principal_rnwam = frappe.db.get_all('Provisional Receipt', filters={"docstatus": 1, "branch": self.branch, "date_issued": self.date, "series": 'A', "pawn_ticket_type": 'Pawn Ticket Jewelry', "transaction_type": 'Renewal w/ Amortization'}, fields=['additional_amortization'], pluck='additional_amortization')
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
		print(f'{sum_active_in},{sum_renewed_in},{sum_rd_in_a},{sum_rn_amort_a}')	
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
#A Total principal
		a_principal_total_act = frappe.db.get_all('Pawn Ticket Jewelry', filters={"branch": self.branch, "item_series": 'A', 'workflow_state': 'Active'}, fields=['desired_principal'], pluck='desired_principal')
		a_principal_total_exp = frappe.db.get_all('Pawn Ticket Jewelry', filters={"branch": self.branch, "item_series": 'A', 'workflow_state': 'Expired'}, fields=['desired_principal'], pluck='desired_principal')
		a_principal_total = 0
		for record in a_principal_total_act:
			a_principal_total += record
		for record2 in a_principal_total_exp:
			a_principal_total += record2
#B IN count
		b_in_count_of_the_day = frappe.db.count('Pawn Ticket Jewelry', {'date_loan_granted': self.date ,'item_series': 'B', 'branch': self.branch, 'workflow_state': 'Active'})
		b_renewed_count_of_the_day = frappe.db.count('Pawn Ticket Jewelry', {'change_status_date': self.date, 'workflow_state': 'Renewed', 'item_series': 'B', 'branch': self.branch})
		b_in_rd_of_the_day = frappe.db.count('Pawn Ticket Jewelry', {'date_loan_granted': self.date ,'item_series': 'B', 'branch': self.branch, 'workflow_state': 'Redeemed'})
		b_in_count = b_in_count_of_the_day - b_renewed_count_of_the_day + b_in_rd_of_the_day
#B IN principal
		b_in_principal_active = frappe.db.get_all('Pawn Ticket Jewelry', filters={"branch": self.branch, "item_series": 'B', "date_loan_granted": self.date, 'workflow_state': 'Active'}, fields=['desired_principal'], pluck='desired_principal')
		b_in_principal_renewed = frappe.db.get_all('Pawn Ticket Jewelry', filters={"branch": self.branch, "item_series": 'B', "change_status_date": self.date, 'workflow_state': 'Renewed'}, fields=['desired_principal'], pluck='desired_principal')	
		b_in_principal_rnwam = frappe.db.get_all('Provisional Receipt', filters={"docstatus": 1, "branch": self.branch, "series": 'B', "date_issued": self.date, "pawn_ticket_type": 'Pawn Ticket Jewelry', "transaction_type": 'Renewal w/ Amortization'}, fields=['additional_amortization'], pluck='additional_amortization')
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
			#if a pawnticket was renewed only and then amortized after, in the same day. This would create a discrepancy. Must also add back Amortization only for PTs renewed only same day
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
#B Total principal
		b_principal_total_act = frappe.db.get_all('Pawn Ticket Jewelry', filters={"branch": self.branch, "item_series": 'B', 'workflow_state': 'Active'}, fields=['desired_principal'], pluck='desired_principal')
		b_principal_total_exp = frappe.db.get_all('Pawn Ticket Jewelry', filters={"branch": self.branch, "item_series": 'B', 'workflow_state': 'Expired'}, fields=['desired_principal'], pluck='desired_principal')
		b_principal_total = 0
		for record in b_principal_total_act:
			b_principal_total += record
		for record2 in b_principal_total_exp:
			b_principal_total += record2
#BNJ IN count
		nj_in_count_of_the_day = frappe.db.count('Pawn Ticket Non Jewelry', {'date_loan_granted': self.date , 'workflow_state': 'Active', 'branch': self.branch})
		nj_renewed_count_of_the_day = frappe.db.count('Pawn Ticket Non Jewelry', {'change_status_date': self.date, 'workflow_state': 'Renewed', 'branch': self.branch})
		bnj_in_rd_of_the_day = frappe.db.count('Pawn Ticket Non Jewelry', {'date_loan_granted': self.date , 'branch': self.branch, 'workflow_state': 'Redeemed'})
		nj_in_count = nj_in_count_of_the_day - nj_renewed_count_of_the_day + bnj_in_rd_of_the_day
#BNJ IN principal
		bnj_in_principal_active = frappe.db.get_all('Pawn Ticket Non Jewelry', filters={"branch": self.branch, "date_loan_granted": self.date, 'workflow_state': 'Active'}, fields=['desired_principal'], pluck='desired_principal')
		bnj_in_principal_renewed = frappe.db.get_all('Pawn Ticket Non Jewelry', filters={"branch": self.branch, "change_status_date": self.date, 'workflow_state': 'Renewed'}, fields=['desired_principal'], pluck='desired_principal')	
		bnj_in_principal_rnwam = frappe.db.get_all('Provisional Receipt', filters={"docstatus": 1, "branch": self.branch, "date_issued": self.date, "series": 'B', "pawn_ticket_type": 'Pawn Ticket Non Jewelry', "transaction_type": 'Renewal w/ Amortization'}, fields=['additional_amortization'], pluck='additional_amortization')
		bnj_in_principal_am = frappe.db.get_all('Provisional Receipt', filters={"docstatus": 1, "branch": self.branch, "date_issued": self.date, "series": 'B', "pawn_ticket_type": 'Pawn Ticket Non Jewelry', "transaction_type": 'Amortization', "date_loan_granted": self.date}, fields=['additional_amortization'], pluck='additional_amortization')
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
		sum_amort_bnj = 0
		for record in bnj_in_principal_am:
			sum_amort_bnj += record	
			#if a pawnticket was renewed only and then amortized after, in the same day. This would create a discrepancy. Must also add back Amortization only for PTs renewed only same day	
		bnj_in_principal = sum_active_in_bnj - sum_renewed_in_bnj + sum_rd_in_bnj + sum_rn_amort_bnj + sum_amort_bnj
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
#BNJ Total principal
		bnj_principal_total_act = frappe.db.get_all('Pawn Ticket Non Jewelry', filters={"branch": self.branch, 'workflow_state': 'Active'}, fields=['desired_principal'], pluck='desired_principal')
		bnj_principal_total_exp = frappe.db.get_all('Pawn Ticket Non Jewelry', filters={"branch": self.branch, 'workflow_state': 'Expired'}, fields=['desired_principal'], pluck='desired_principal')
		bnj_principal_total = 0
		for record in bnj_principal_total_act:
			bnj_principal_total += record
		for record2 in bnj_principal_total_exp:
			bnj_principal_total += record2

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
		invetory_count_doc.principal_totala = a_principal_total

		invetory_count_doc.in_count_b = b_in_count
		invetory_count_doc.principal_in_b = b_in_principal
		invetory_count_doc.out_count_b = b_out_count
		invetory_count_doc.principal_out_b = b_out_principal
		invetory_count_doc.returned_b = b_returned_of_the_day
		invetory_count_doc.principal_ret_b = b_ret_principal
		invetory_count_doc.pulled_out_b = b_pulled_out_of_the_day
		invetory_count_doc.principal_po_b = b_po_principal
		invetory_count_doc.total_b = b_total_active
		invetory_count_doc.principal_totalb = b_principal_total
		
		invetory_count_doc.in_count_nj = nj_in_count
		invetory_count_doc.principal_in_nj = bnj_in_principal
		invetory_count_doc.out_count_nj = nj_out_count
		invetory_count_doc.principal_out_nj = bnj_out_principal
		invetory_count_doc.pulled_out_nj = nj_pulled_out_of_the_day
		invetory_count_doc.principal_po_nj = bnj_po_principal
		invetory_count_doc.returned_nj = nj_returned_of_the_day
		invetory_count_doc.principal_ret_nj = bnj_ret_principal
		invetory_count_doc.total_nj = nj_total_active
		invetory_count_doc.principal_totalnj = bnj_principal_total
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

			
