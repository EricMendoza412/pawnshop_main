# Copyright (c) 2013, Rabie Moses Santillan and contributors
# For license information, please see license.txt

import frappe
from frappe import _ # _ for to set the string into literal string
from pawnshop_management.pawnshop_management.custom_codes.get_ip import get_ip_from_settings

import frappe
from frappe.model.base_document import BaseDocument
import json

# @frappe.whitelist()
# def get_full_user_name(user=None):
# 	p = frappe.db.get_value("User", user, "full_name")
# 	return p


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
	elif str(current_ip) == str(branch_ip['noveleta']):
		branch = "Garcia's Pawnshop - NOV"	
	elif str(current_ip) == str(branch_ip['pascam']):
		branch = "Garcia's Pawnshop - PSC"	
	elif str(current_ip) == str(branch_ip['test']):
		branch = "TEST"	

	columns, data = [], []
	columns = get_columns()

	workflow = getattr(filters, 'workflow_state')
	branch_filter = getattr(filters, 'branch')
	if branch_filter != None:
		branch = branch_filter

	data = frappe.get_all("Pawn Ticket Non Jewelry", filters={'branch': branch, 'workflow_state': workflow}, fields=['pawn_ticket', 'customers_tracking_no', 'customers_full_name', 'inventory_tracking_no', 'desired_principal', 'date_loan_granted', 'maturity_date', 'expiry_date', 'workflow_state', 'texted_upon_maturity', 'texted_upon_expiry', '_comments'])
	comments = string_extractor
	for i in range(len(data)):
		description = ""
		comments = string_extractor(data[i]["_comments"])
		details = frappe.db.get_list("Non Jewelry List", filters={'parent': data[i]['pawn_ticket']}, fields=['item_no', 'type', 'brand', 'model', 'model_number', '_comments'])
		customer = frappe.get_doc('Customer', data[i]['customers_tracking_no'])
		contact = frappe.get_doc('Contact', customer.customer_primary_contact)
		data[i]['contact_no'] = contact.mobile_no
		for j in range(len(details)):
			#commentsNJ = string_extractor(details[j]["_comments"])
			description += details[j]["item_no"] + ", " + details[j]["type"] + ", " + details[j]["brand"] + ", " + details[j]["model"] + ", " + details[j]["model_number"] + "; "
		data[i]['description'] = description
		data[i]['comments'] = comments
	return columns, data

def get_columns():
	columns = [
		{
			'fieldname': 'pawn_ticket',
			'label': _('Pawn Ticket'),
			'fieldtype': 'Link',
			'options': 'Pawn Ticket Non Jewelry',
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
			'options': 'Non Jewelry Batch',
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
			'fieldname': 'texted_upon_maturity',
			'label': _('Txted(MD)'),
			'fieldtype': 'Check',
			'width': 100
		},

		{
			'fieldname': 'texted_upon_expiry',
			'label': _('Txted(ED)'),
			'fieldtype': 'Check',
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
