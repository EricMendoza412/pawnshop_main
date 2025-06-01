# Copyright (c) 2013, Rabie Moses Santillan and contributors
# For license information, please see license.txt

import frappe
from frappe import _ # _ for to set the string into literal string
from pawnshop_management.pawnshop_management.custom_codes.get_ip import get_ip_from_settings

def execute(filters=None):
	columns, data = [], []
	branch_filter = getattr(filters, 'date')
	
	if branch_filter == None:
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

		data = frappe.get_all('Inventory Count', filters={'branch':branch}, fields=['date', 'in_count_a','principal_in_a', 'out_count_a','principal_out_a', 'returned_a','principal_ret_a', 'pulled_out_a','principal_po_a', 'total_a', 'principal_totala'], order_by='date desc')
	else:
		data = frappe.get_all('Inventory Count', filters=filters, fields=['date', 'in_count_a','principal_in_a', 'out_count_a','principal_out_a', 'returned_a','principal_ret_a', 'pulled_out_a','principal_po_a', 'total_a', 'principal_totala'], order_by='date desc')

	columns = get_columns()
	return columns, data

def get_columns():
	columns = [
		{
			'fieldname': 'date',
			'label': 'Date',
			'fieldtype': 'Date',
			'width': 150
		},

		{
			'fieldname': 'in_count_a',
			'label': 'IN',
			'fieldtype': 'Int',
			'width': 100
		},

		{
			'fieldname': 'principal_in_a',
			'label': 'Principal',
			'fieldtype': 'Currency',
			'width': 100
		},

		{
			'fieldname': 'out_count_a',
			'label': 'OUT',
			'fieldtype': 'Int',
			'width': 100
		},

		{
			'fieldname': 'principal_out_a',
			'label': 'Principal',
			'fieldtype': 'Currency',
			'width': 100
		},

		{
			'fieldname': 'returned_a',
			'label': 'Returned',
			'fieldtype': 'Int',
			'width': 100
		},

		{
			'fieldname': 'principal_ret_a',
			'label': 'Principal',
			'fieldtype': 'Currency',
			'width': 100
		},

		{
			'fieldname': 'pulled_out_a',
			'label': 'Pulled Out',
			'fieldtype': 'Int',
			'width': 100
		},

		{
			'fieldname': 'principal_po_a',
			'label': 'Principal',
			'fieldtype': 'Currency',
			'width': 100
		},

		{
			'fieldname': 'total_a',
			'label': 'Total',
			'fieldtype': 'Int',
			'width': 100
		},

		{
			'fieldname': 'principal_totala',
			'label': 'Principal',
			'fieldtype': 'Currency',
			'width': 150
		}
	]
	return columns
