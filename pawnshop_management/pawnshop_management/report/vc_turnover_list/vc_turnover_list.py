# Copyright (c) 2013, Rabie Moses Santillan and contributors
# For license information, please see license.txt

from hashlib import new
from tokenize import String
from unittest.util import strclass
import frappe
from frappe import _ # _ for to set the string into literal string
from pawnshop_management.pawnshop_management.custom_codes.get_ip import get_ip_from_settings

def execute(filters=None):
	columns, data = [], []
	columns = get_columns()

	branch_fr_ip = ""
	current_ip = frappe.local.request_ip
	branch_ip = get_ip_from_settings()
	if str(current_ip) == str(branch_ip['cavite_city']):
		branch_fr_ip = "Garcia's Pawnshop - CC"
	elif str(current_ip) == str(branch_ip['poblacion']):
		branch_fr_ip = "Garcia's Pawnshop - POB"
	elif str(current_ip) == str(branch_ip['molino']):
		branch_fr_ip = "Garcia's Pawnshop - MOL"
	elif str(current_ip) == str(branch_ip['gtc']):
		branch_fr_ip = "Garcia's Pawnshop - GTC"
	elif str(current_ip) == str(branch_ip['tanza']):
		branch_fr_ip = "Garcia's Pawnshop - TNZ"

	data_act = frappe.get_all("Pawn Ticket Jewelry", filters={'branch': branch_fr_ip, 'workflow_state': "Active"}, fields=['pawn_ticket', 'customers_tracking_no', 'customers_full_name', 'inventory_tracking_no', 'desired_principal', 'date_loan_granted', 'workflow_state'])
	data_exp = frappe.get_all("Pawn Ticket Jewelry", filters={'branch': branch_fr_ip, 'workflow_state': "Expired"}, fields=['pawn_ticket', 'customers_tracking_no', 'customers_full_name', 'inventory_tracking_no', 'desired_principal', 'date_loan_granted', 'workflow_state'])
	data_active = data_act + data_exp

	for i in range(len(data_active)):
		description = ""
		details = frappe.db.get_list("Jewelry List", filters={'parent': data_active[i]['pawn_ticket']}, fields=['type', 'karat_category', 'karat', 'weight', 'color', 'colors_if_multi', 'additional_for_stone', 'densi','comments'])
		for j in range(len(details)):
			if details[j]['colors_if_multi'] == None:
				details[j]['colors_if_multi'] = ''
			else:
				details[j]['colors_if_multi'] = "," + details[j]['colors_if_multi']

			if details[j]['additional_for_stone'] == None:
				details[j]['additional_for_stone'] = ''
			else:
				details[j]['additional_for_stone'] = "," + details[j]['additional_for_stone']
			
			if details[j]['densi'] == None:
				details[j]['densi'] = ''
			else:
				details[j]['densi'] = "," + details[j]['densi']	
			
			if details[j]['comments'] == None:
				details[j]['comments'] = ''
			else:
				details[j]['comments'] = "," + details[j]['comments']	
				
			description += "One " + details[j]["type"] + ", " + str(details[j]["karat_category"]) + ", " + str(details[j]["karat"]) + ", " + str(details[j]["weight"]) + ", " + str(details[j]["color"]) + str(details[j]["colors_if_multi"]) + str(details[j]["additional_for_stone"]) + str(details[j]["densi"]) + str(details[j]["comments"]) + "; "
		data_active[i]['description'] = description

	data = data_active
	return columns, data

def get_columns():
	columns = [
		{
			'fieldname': 'pawn_ticket',
			'label': _('Pawn Ticket'),
			'fieldtype': 'Link',
			'options': 'Pawn Ticket Jewelry',
			'width': 100
		},

		{
			'fieldname': 'customers_full_name',
			'label': _('Customer Name'),
			'fieldtype': 'Data',
			'options': 'Customer',
			'width': 200
		},

		{
			'fieldname': 'inventory_tracking_no',
			'label': _('Inventory Tracker'),
			'fieldtype': 'Link',
			'options': 'Jewelry Batch',
			'width': 100
		},

		{
			'fieldname': 'description',
			'label': _('Item Description'),
			'fieldtype': 'Small Text',
			'width': 600
		},

		{
			'fieldname': 'desired_principal',
			'label': _('Principal'),
			'fieldtype': 'Currency',
			'width': 100
		},

		{
			'fieldname': 'date_loan_granted',
			'label': _('Date Loan Granted'),
			'fieldtype': 'Date',
			'width': 150
		},

		{
			'fieldname': 'workflow_state',
			'label': _('Status'),
			'fieldtype': 'Data',
			'width': 100
		}
		
	]
	return columns
