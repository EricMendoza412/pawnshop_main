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
		data = frappe.get_all('Inventory Count', filters={'branch':branch},  fields=['date', 'in_count_b', 'principal_in_b','out_count_b','principal_out_b', 'returned_b','principal_ret_b', 'pulled_out_b', 'principal_po_b','total_b', 'principal_totalb'], order_by='date desc',)
	else:
		data = frappe.get_all('Inventory Count', filters=filters,  fields=['date', 'in_count_b', 'principal_in_b','out_count_b','principal_out_b', 'returned_b','principal_ret_b', 'pulled_out_b', 'principal_po_b','total_b', 'principal_totalb'], order_by='date desc',)

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
			'fieldname': 'in_count_b',
			'label': 'IN',
			'fieldtype': 'Int',
			'width': 100
		},

		{
			'fieldname': 'principal_in_b',
			'label': 'Principal',
			'fieldtype': 'Currency',
			'width': 100
		},

		{
			'fieldname': 'out_count_b',
			'label': 'OUT',
			'fieldtype': 'Int',
			'width': 100
		},

		{
			'fieldname': 'principal_out_b',
			'label': 'Principal',
			'fieldtype': 'Currency',
			'width': 100
		},

		{
			'fieldname': 'returned_b',
			'label': 'Returned',
			'fieldtype': 'Int',
			'width': 100
		},

		{
			'fieldname': 'principal_ret_b',
			'label': 'Principal',
			'fieldtype': 'Currency',
			'width': 100
		},

		{
			'fieldname': 'pulled_out_b',
			'label': 'Pulled Out',
			'fieldtype': 'Int',
			'width': 100
		},

		{
			'fieldname': 'principal_po_b',
			'label': 'Principal',
			'fieldtype': 'Currency',
			'width': 100
		},

		{
			'fieldname': 'total_b',
			'label': 'Total',
			'fieldtype': 'Int',
			'width': 100
		},

		{
			'fieldname': 'principal_totalb',
			'label': 'Principal',
			'fieldtype': 'Currency',
			'width': 150
		}
	]
	return columns