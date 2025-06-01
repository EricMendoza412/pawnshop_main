# Copyright (c) 2023, Rabie Moses Santillan and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from pawnshop_management.pawnshop_management.custom_codes.get_ip import get_ip_from_settings


def execute(filters=None):
	columns, data = [], []
	branch = ""
	current_ip = frappe.local.request_ip
	branch_ip = get_ip_from_settings()
	if str(current_ip) == str(branch_ip['cavite_city']):
		branch = "Garcia's Pawnshop - CC"
	elif str(current_ip) == str(branch_ip['poblacion']):
		branch = "Garcia's Pawnshop - POB"
	elif str(current_ip) == str(branch_ip['molino']):
		branch = "Garcia's Pawnshop - MOL"
	elif str(current_ip) == str(branch_ip['gtc']):
		branch = "Garcia's Pawnshop - GTC"
	elif str(current_ip) == str(branch_ip['tanza']):
		branch = "Garcia's Pawnshop - TNZ"
	elif str(current_ip) == str(branch_ip['alapan']):
		branch = "Garcia's Pawnshop - ALP"
	elif str(current_ip) == str(branch_ip['noveleta']):
		branch = "Garcia's Pawnshop - NOV"
	elif str(current_ip) == str(branch_ip['pascam']):
		branch = "Garcia's Pawnshop - PSC"

	
	data = frappe.db.sql("""
		SELECT workflow_state, pawn_ticket, date_loan_granted, desired_principal
		FROM `tabPawn Ticket Jewelry`
		WHERE `tabPawn Ticket Jewelry`.docstatus=1
		AND `tabPawn Ticket Jewelry`.workflow_state = 'Redeemed'
		AND `tabPawn Ticket Jewelry`.change_status_date = CURDATE()
		AND `tabPawn Ticket Jewelry`.branch = %s
	""", (branch), as_dict=True)

	columns = get_columns()
	return columns, data

def get_columns():
	columns = [

		{
			'fieldname': 'workflow_state',
			'label': _('Status'),
			'fieldtype': 'Data',
			'width': 200
		},

		{
			'fieldname': 'pawn_ticket',
			'label': _('Pawn Ticket'),
			'fieldtype': 'Data',
			'width': 200
		},

		{
			'fieldname': 'date_loan_granted',
			'label': _('Date Loan Granted'),
			'fieldtype': 'Data',
			'width': 200
		},

		{
			'fieldname': 'desired_principal',
			'label': _('Principal'),
			'fieldtype': 'Data',
			'width': 200
		}
		
	]
	return columns