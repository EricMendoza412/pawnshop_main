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
		data = frappe.get_all('Inventory Count', filters={'branch':branch}, fields=['date', 'in_count_nj', 'principal_in_nj', 'out_count_nj', 'principal_out_nj', 'returned_nj', 'principal_ret_nj', 'pulled_out_nj', 'principal_po_nj', 'total_nj'], order_by='date desc',)
	else:
		data = frappe.get_all('Inventory Count', filters=filters, fields=['date', 'in_count_nj', 'principal_in_nj', 'out_count_nj', 'principal_out_nj', 'returned_nj', 'principal_ret_nj', 'pulled_out_nj', 'principal_po_nj', 'total_nj'], order_by='date desc',)

	columns = get_columns()
	return columns, data

def get_columns():
	columns = [
		{
			'fieldname': 'date',
			'label': 'Date',
			'fieldtype': 'Date',
			'width': 200
		},

		{
			'fieldname': 'in_count_nj',
			'label': 'IN',
			'fieldtype': 'Int',
			'width': 100
		},

		{
			'fieldname': 'principal_in_nj',
			'label': 'Principal',
			'fieldtype': 'Currency',
			'width': 100
		},

		{
			'fieldname': 'out_count_nj',
			'label': 'OUT',
			'fieldtype': 'Int',
			'width': 100
		},

		{
			'fieldname': 'principal_out_nj',
			'label': 'Principal',
			'fieldtype': 'Currency',
			'width': 100
		},

		{
			'fieldname': 'returned_nj',
			'label': 'Returned',
			'fieldtype': 'Int',
			'width': 100
		},

		{
			'fieldname': 'principal_ret_nj',
			'label': 'Principal',
			'fieldtype': 'Currency',
			'width': 100
		},

		{
			'fieldname': 'pulled_out_nj',
			'label': 'Pulled Out',
			'fieldtype': 'Int',
			'width': 100
		},

		{
			'fieldname': 'principal_po_nj',
			'label': 'Principal',
			'fieldtype': 'Currency',
			'width': 100
		},

		{
			'fieldname': 'total_nj',
			'label': 'Total',
			'fieldtype': 'Int',
			'width': 100
		}
	]
	return columns

