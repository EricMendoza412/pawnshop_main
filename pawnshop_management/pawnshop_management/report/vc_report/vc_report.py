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
		branch = "Garcia\\'s Pawnshop - CC"
	elif str(current_ip) == str(branch_ip['poblacion']):
		branch = "Garcia\\'s Pawnshop - POB"
	elif str(current_ip) == str(branch_ip['molino']):
		branch = "Garcia\\'s Pawnshop - MOL"
	elif str(current_ip) == str(branch_ip['gtc']):
		branch = "Garcia\\'s Pawnshop - GTC"
	elif str(current_ip) == str(branch_ip['tanza']):
		branch = "Garcia\\'s Pawnshop - TNZ"

	conditions = ""
	if filters:
		conditions += f" AND `tabPawn Ticket Jewelry`.change_status_date = '{filters.get('change_status_date')}' "
		conditions += f" AND `tabPawn Ticket Jewelry`.branch = '{branch}' "

	conditions2 = ""
	if filters:
		conditions2 += f" AND `tabPawn Ticket Jewelry`.date_loan_granted = '{filters.get('change_status_date')}' "
		conditions2 += f" AND `tabPawn Ticket Jewelry`.branch = '{branch}' "

	data_redeemed_J = frappe.db.sql(f"""
        SELECT branch, change_status_date, '' as old_pawn_ticket, workflow_state, pawn_ticket, date_loan_granted, desired_principal
        FROM `tabPawn Ticket Jewelry`
        WHERE `tabPawn Ticket Jewelry`.docstatus=1
        AND `tabPawn Ticket Jewelry`.workflow_state = 'Redeemed'
        {conditions}
    """, as_dict=True)
	
	data_renewed_J = frappe.db.sql(f"""
		SELECT branch, change_status_date, old_pawn_ticket, workflow_state, pawn_ticket, date_loan_granted, desired_principal
		FROM `tabPawn Ticket Jewelry`
		WHERE `tabPawn Ticket Jewelry`.docstatus=1
		AND `tabPawn Ticket Jewelry`.old_pawn_ticket IS NOT NULL
		{conditions2}
	""", as_dict=True)

	data_new_sangla_J = frappe.db.sql(f"""
		SELECT branch, change_status_date, '' as old_pawn_ticket, workflow_state, pawn_ticket, date_loan_granted, desired_principal
		FROM `tabPawn Ticket Jewelry`
		WHERE `tabPawn Ticket Jewelry`.docstatus=1
		AND `tabPawn Ticket Jewelry`.old_pawn_ticket IS NULL
		{conditions2}
	""", as_dict=True)

	data = data_redeemed_J + data_renewed_J + data_new_sangla_J
	columns = get_columns()
	return columns, data

def get_columns():
	columns = [
		{
			'fieldname': 'old_pawn_ticket',
			'label': _('Old Pawn Ticket'),
			'fieldtype': 'Data',
			'width': 100
		},

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
			'fieldtype': 'Date',
			'width': 200
		},

		{
			'fieldname': 'desired_principal',
			'label': _('New PT Principal'),
			'fieldtype': 'Data',
			'width': 200
		}
		
	]
	return columns