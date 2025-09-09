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
	status_value = getattr(filters, 'branch')
	branch_fr_ip = ""
	branch = ""
	pt_type = "Agreement to Sell"
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
	elif str(current_ip) == str(branch_ip['alapan']):
		branch_fr_ip = "Garcia's Pawnshop - ALP"
	elif str(current_ip) == str(branch_ip['noveleta']):
		branch_fr_ip = "Garcia's Pawnshop - NOV"
	elif str(current_ip) == str(branch_ip['pascam']):
		branch_fr_ip = "Garcia's Pawnshop - PSC"
	
	if status_value == None:
		branch = branch_fr_ip
	else:
		branch = status_value


	data_act = frappe.get_all(pt_type, filters={'branch': branch, 'workflow_state': "Active"}, fields=['form_number', 'customer_tracker', 'customer_name', 'ats_tracking_no', 'total_value', 'date_of_sale', 'branch'])
	data_active = data_act

	for i in range(len(data_active)):
		description = ""

	
		detailsL = frappe.db.get_list("Jewelry List", filters={'parent': data_active[i]['form_number']}, fields=['item_no'])
		for j in range(len(detailsL)):
			if detailsL[j]['item_no'] != "0-0J-0":
				details = frappe.db.get_list("Jewelry Items", filters={'item_no': detailsL[j]['item_no']}, fields=['item_no','type', 'karat_category', 'karat', 'total_weight', 'color', 'colors_if_multi', 'additional_for_stone', 'densi','comments'])
				for doc in details:
					densi, comments, colorMulti, addForStone  = "", "", "", ""
					if doc.densi != None:
						densi = ", " + doc.densi
					if doc.comments != None:
						comments = ", " + doc.comments
					if doc.colors_if_multi != None:
						colorMulti = ", " + doc.colors_if_multi
					if doc.additional_for_stone != None:
						addForStone = ", Stone:" + str(doc.additional_for_Stone)
					description += "One " + doc.type + ", " + doc.karat_category + ", " + doc.karat + ", " + str(doc.total_weight) + ", " + doc.color + colorMulti + densi + comments + colorMulti + addForStone + "; "
		data_active[i]['description'] = description

	data = data_active
	return columns, data

def get_columns():
	columns = [
		{
			'fieldname': 'ats_tracking_no',
			'label': _('Inventory Tracker'),
			'fieldtype': 'Data',
			'width': 100
		},

		{
			'fieldname': 'customer_name',
			'label': _('Customer Name'),
			'fieldtype': 'Data',
			'width': 200
		},

		{
			'fieldname': 'form_number',
			'label': _('Form number'),
			'fieldtype': 'Link',
			'options': 'Agreement to Sell',
			'width': 100
		},

		{
			'fieldname': 'description',
			'label': _('Item Description'),
			'fieldtype': 'Small Text',
			'width': 500
		},

		{
			'fieldname': 'total_value',
			'label': _('Total amount'),
			'fieldtype': 'Currency',
			'width': 100,
			'sum': 1
		},

		{
			'fieldname': 'date_of_sale',
			'label': _('Date of sale'),
			'fieldtype': 'Date',
			'width': 150
		}
		
	]
	return columns
