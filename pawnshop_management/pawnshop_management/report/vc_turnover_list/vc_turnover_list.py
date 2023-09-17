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
	series = getattr(filters, 'series')
	branch_fr_ip = ""
	branch = ""
	item_series = ""
	pt_type = ""
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

	if status_value == None:
		branch = branch_fr_ip
	else:
		branch = status_value
	
	if series == "A-Jewelry":
		item_series = "A"
		pt_type = "Pawn Ticket Jewelry"
	elif series == "B-Jewelry":
		item_series = "B"
		pt_type = "Pawn Ticket Jewelry"
	elif series == "B-Non Jewelry":
		item_series = "B"
		pt_type = "Pawn Ticket Non Jewelry"


	data_act = frappe.get_all(pt_type, filters={'branch': branch, 'workflow_state': "Active", 'item_series': item_series}, fields=['pawn_ticket', 'customers_tracking_no', 'customers_full_name', 'inventory_tracking_no', 'desired_principal', 'date_loan_granted', 'maturity_date', 'expiry_date', 'branch', 'item_series'])
	data_exp = frappe.get_all(pt_type, filters={'branch': branch, 'workflow_state': "Expired", 'item_series': item_series}, fields=['pawn_ticket', 'customers_tracking_no', 'customers_full_name', 'inventory_tracking_no', 'desired_principal', 'date_loan_granted', 'maturity_date', 'expiry_date', 'branch', 'item_series'])
	data_ret = frappe.get_all(pt_type, filters={'branch': branch, 'workflow_state': "Returned", 'item_series': item_series}, fields=['pawn_ticket', 'customers_tracking_no', 'customers_full_name', 'inventory_tracking_no', 'desired_principal', 'date_loan_granted', 'maturity_date', 'expiry_date', 'branch', 'item_series'])
	data_active = data_act + data_exp + data_ret

	for i in range(len(data_active)):
		description = ""

		if pt_type == "Pawn Ticket Non Jewelry":
			detailsL = frappe.db.get_list("Non Jewelry List", filters={'parent': data_active[i]['pawn_ticket']}, fields=['item_no'])
			njItem = frappe.get_doc('Non Jewelry Items', detailsL[0]['item_no'])
			comments, charger, case, box, earphones, not_openline, others, pin, manual, sim_card, sd_card, bag, extra_bat, extra_lens = "","","","","","","","","","","","","",""
			if njItem.comments != None:
				comments = ", " + njItem.comments
			if njItem.others != None:
				others = ", " + njItem.others

			if njItem.charger:
				charger = ", w/ charger"
			else:
				charger = ", No charger"
			if njItem.case:
				case = ", w/ case"
			if njItem.box:
				box = ", w/ box"
			if njItem.earphones:
				earphones = ", w/ earphones"
			if njItem.not_openline:
				not_openline = ", Not Openline"	
			if njItem.pin:
				pin = ", w/ pin"
			if njItem.manual:
				manual = ", w/ manual"
			if njItem.sim_card:
				sim_card = ", w/ Sim Card"
			if njItem.sd_card:
				sd_card = ", w/ SD card"
			if njItem.bag:
				bag = ", w/ bag"
			if njItem.extra_battery:
				extra_bat = ", w/ extra battery"
			if njItem.extra_lens:
				extra_lens = ", w/ extra lens"

			description += "One " + njItem.type + ", " + njItem.brand + ", " + njItem.model + ", " + njItem.model_number + ", Color:" + njItem.color + ", " + njItem.ram + "/" + njItem.internal_memory + ", " + njItem.category + not_openline + comments + charger + case + box + earphones + others + pin + manual + sim_card + sd_card + bag + extra_bat + extra_lens +"; "
		elif pt_type == "Pawn Ticket Jewelry":
			detailsL = frappe.db.get_list("Jewelry List", filters={'parent': data_active[i]['pawn_ticket']}, fields=['item_no'])
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
			'fieldname': 'inventory_tracking_no',
			'label': _('Inventory Tracker'),
			'fieldtype': 'Link',
			'options': 'Jewelry Batch',
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
			'fieldname': 'pawn_ticket',
			'label': _('Pawn Ticket'),
			'fieldtype': 'Link',
			'options': 'Pawn Ticket Jewelry',
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
			'width': 150
		},

		{
			'fieldname': 'maturity_date',
			'label': _('Maturity Date'),
			'fieldtype': 'Date',
			'width': 150
		},

		{
			'fieldname': 'expiry_date',
			'label': _('Expiry Date'),
			'fieldtype': 'Date',
			'width': 150
		}
		
	]
	return columns
