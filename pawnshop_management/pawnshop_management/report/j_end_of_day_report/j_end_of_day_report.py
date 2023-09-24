# Copyright (c) 2013, Rabie Moses Santillan and contributors
# For license information, please see license.txt

from hashlib import new
from tokenize import String
from unittest.util import strclass
import frappe
from frappe import _ # _ for to set the string into literal string
from pawnshop_management.pawnshop_management.custom_codes.get_ip import get_ip_from_settings

import frappe
from frappe.model.base_document import BaseDocument
import json


def execute(filters=None):
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
	
	columns, data = [], []
	columns = get_columns()

	workflow = getattr(filters, 'workflow_state')
	branch_filter = getattr(filters, 'branch')
	if branch_filter != None:
		branch = branch_filter
	series = getattr(filters, 'item_series')


	data = frappe.get_all("Pawn Ticket Jewelry", filters={'workflow_state': workflow, 'branch': branch, 'item_series': series}, fields=['pawn_ticket', 'customers_tracking_no', 'customers_full_name', 'inventory_tracking_no', 'desired_principal', 'date_loan_granted', 'maturity_date', 'expiry_date', 'workflow_state', '_comments'])
	for i in range(len(data)):
		description = ""
		comments = string_extractor(data[i]["_comments"])
		details = frappe.db.get_list("Jewelry List", filters={'parent': data[i]['pawn_ticket']}, fields=['item_no', 'type', 'karat_category', 'karat', 'weight', 'color', 'colors_if_multi', 'additional_for_stone', 'comments'])
		customer = frappe.get_doc('Customer', data[i]['customers_tracking_no'])
		data[i]['contact_no'] = customer.mobile_no
		for j in range(len(details)):
			if details[j]["colors_if_multi"] == None:
				details[j]["colors_if_multi"] = ''

			if details[j]['additional_for_stone'] == None:
				details[j]['additional_for_stone'] = ''
				
			description += str(details[j]["item_no"]) + ", " + details[j]["type"] + ", " + str(details[j]["karat_category"]) + ", " + str(details[j]["karat"]) + ", " + str(details[j]["weight"]) + ", " + str(details[j]["color"]) + ", " + str(details[j]["colors_if_multi"]) + ", " + str(details[j]["additional_for_stone"]) + str(details[j]["comments"]) + "; "
		data[i]['description'] = description
		data[i]["comments"] = comments
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
			'fieldname': 'contact_no',
			'label': _('Contact #'),
			'fieldtype': 'Data',
			'width': 150
		},

		{
			'fieldname': 'inventory_tracking_no',
			'label': _('Inventory Tracking No'),
			'fieldtype': 'Link',
			'options': 'Jewelry Batch',
			'width': 100
		},

		{
			'fieldname': 'description',
			'label': _('Item Description'),
			'fieldtype': 'Small Text',
			'width': 500
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
			'width': 100
		},
		
		{
			'fieldname': 'maturity_date',
			'label': _('Maturity Date'),
			'fieldtype': 'Date',
			'width': 100
		},

		{
			'fieldname': 'expiry_date',
			'label': _('Expiry Date'),
			'fieldtype': 'Date',
			'width': 100
		},

		{
			'fieldname': 'workflow_state',
			'label': _('Status'),
			'fieldtype': 'Data',
			'width': 100
		},

		{
			'fieldname': 'comments',
			'label': _('Comments'),
			'fieldtype': 'Small Text',
			'width': 300
		}
		
	]
	return columns

def string_extractor(string=None):
	new_string = ""
	if string == None:
		return new_string
	else:
		first = string.rfind("<p>") + 3
		last = string.rfind("</p>")
		new_string = string[first:last]
	return new_string
