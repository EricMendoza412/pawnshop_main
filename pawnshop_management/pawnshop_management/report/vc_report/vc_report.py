# Copyright (c) 2023, Rabie Moses Santillan and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from pawnshop_management.pawnshop_management.custom_codes.get_ip import get_ip_from_settings


def execute(filters=None):
	status_value = getattr(filters, 'branch')
	columns, data = [], []
	branch = ""
	branch_fr_ip = ""
	current_ip = frappe.local.request_ip
	branch_ip = get_ip_from_settings()
	if str(current_ip) == str(branch_ip['cavite_city']):
		branch_fr_ip = "Garcia\\'s Pawnshop - CC"
	elif str(current_ip) == str(branch_ip['poblacion']):
		branch_fr_ip = "Garcia\\'s Pawnshop - POB"
	elif str(current_ip) == str(branch_ip['molino']):
		branch_fr_ip = "Garcia\\'s Pawnshop - MOL"
	elif str(current_ip) == str(branch_ip['gtc']):
		branch_fr_ip = "Garcia\\'s Pawnshop - GTC"
	elif str(current_ip) == str(branch_ip['tanza']):
		branch_fr_ip = "Garcia\\'s Pawnshop - TNZ"

	if status_value == None:
		branch = branch_fr_ip
	else:
		branch = status_value
		
	conditions = ""
	if filters:
		conditions += f" AND `tabPawn Ticket Jewelry`.change_status_date = '{filters.get('change_status_date')}' "
		conditions += f" AND `tabPawn Ticket Jewelry`.branch = '{branch}' "

	conditions2 = ""
	if filters:
		conditions2 += f" AND `tabPawn Ticket Jewelry`.date_loan_granted = '{filters.get('change_status_date')}' "
		conditions2 += f" AND `tabPawn Ticket Jewelry`.branch = '{branch}' "

	conditions3 = ""
	if filters:
		conditions3 += f" AND `tabPawn Ticket Non Jewelry`.change_status_date = '{filters.get('change_status_date')}' "
		conditions3 += f" AND `tabPawn Ticket Non Jewelry`.branch = '{branch}' "

	conditions4 = ""
	if filters:
		conditions4 += f" AND `tabPawn Ticket Non Jewelry`.date_loan_granted = '{filters.get('change_status_date')}' "
		conditions4 += f" AND `tabPawn Ticket Non Jewelry`.branch = '{branch}' "

	conditions5 = ""
	if filters:
		conditions5 += f" AND `tabProvisional Receipt`.date_issued = '{filters.get('change_status_date')}' "
		conditions5 += f" AND `tabProvisional Receipt`.branch = '{branch}' "


	data_redeemed_J = frappe.db.sql(f"""
        SELECT branch, change_status_date, old_pawn_ticket, workflow_state, pawn_ticket, date_loan_granted, inventory_tracking_no, desired_principal, '' as net_proceeds, item_series, 'J' as pt_type, '' as interest, '' as interest_payment, '' as discount
        FROM `tabPawn Ticket Jewelry`
        WHERE `tabPawn Ticket Jewelry`.docstatus=1
        AND `tabPawn Ticket Jewelry`.workflow_state = 'Redeemed'
        {conditions}
    """, as_dict=True)
	
	data_renewed_J = frappe.db.sql(f"""
		SELECT branch, change_status_date, old_pawn_ticket, workflow_state, pawn_ticket, date_loan_granted, inventory_tracking_no, desired_principal, '' as net_proceeds, item_series, 'J' as pt_type, '' as interest, '' as interest_payment, '' as discount
		FROM `tabPawn Ticket Jewelry`
		WHERE `tabPawn Ticket Jewelry`.docstatus=1
		AND `tabPawn Ticket Jewelry`.old_pawn_ticket IS NOT NULL
		{conditions2}
	""", as_dict=True)

	data_new_sangla_J = frappe.db.sql(f"""
		SELECT branch, change_status_date, '' as old_pawn_ticket, workflow_state, pawn_ticket, date_loan_granted, inventory_tracking_no, desired_principal, net_proceeds, item_series, 'J' as pt_type, '' as interest, '' as interest_payment, '' as discount
		FROM `tabPawn Ticket Jewelry`
		WHERE `tabPawn Ticket Jewelry`.docstatus=1
		AND `tabPawn Ticket Jewelry`.old_pawn_ticket IS NULL		
		{conditions2}
	""", as_dict=True)

	data_redeemed_NJ = frappe.db.sql(f"""
        SELECT branch, change_status_date, old_pawn_ticket, workflow_state, pawn_ticket, date_loan_granted, inventory_tracking_no, desired_principal, '' as net_proceeds, item_series, 'NJ' as pt_type, '' as interest, '' as interest_payment, '' as discount
        FROM `tabPawn Ticket Non Jewelry`
        WHERE `tabPawn Ticket Non Jewelry`.docstatus=1
        AND `tabPawn Ticket Non Jewelry`.workflow_state = 'Redeemed'
        {conditions3}
    """, as_dict=True)
	
	data_renewed_NJ = frappe.db.sql(f"""
		SELECT branch, change_status_date, old_pawn_ticket, workflow_state, pawn_ticket, date_loan_granted, inventory_tracking_no, desired_principal, '' as net_proceeds, item_series, 'NJ' as pt_type, '' as interest, '' as interest_payment, '' as discount
		FROM `tabPawn Ticket Non Jewelry`
		WHERE `tabPawn Ticket Non Jewelry`.docstatus=1
		AND `tabPawn Ticket Non Jewelry`.old_pawn_ticket IS NOT NULL
		{conditions4}
	""", as_dict=True)

	data_new_sangla_NJ = frappe.db.sql(f"""
		SELECT branch, change_status_date, '' as old_pawn_ticket, workflow_state, pawn_ticket, date_loan_granted, inventory_tracking_no, desired_principal, net_proceeds, item_series, 'NJ' as pt_type, '' as interest, '' as interest_payment, '' as discount
		FROM `tabPawn Ticket Non Jewelry`
		WHERE `tabPawn Ticket Non Jewelry`.docstatus=1
		AND `tabPawn Ticket Non Jewelry`.old_pawn_ticket IS NULL
		{conditions4}
	""", as_dict=True)

	data_pr = frappe.db.sql(f"""
		SELECT branch, principal_amount as change_status_date, new_pawn_ticket_no as old_pawn_ticket, transaction_type as workflow_state, pawn_ticket_no as pawn_ticket, date_issued as date_loan_granted, pawn_ticket_type as inventory_tracking_no, additional_amortization as desired_principal, total as net_proceeds, series as item_series, '' as pt_type, interest, interest_payment, discount
		FROM `tabProvisional Receipt`
		WHERE `tabProvisional Receipt`.docstatus=1
		{conditions5}
	""", as_dict=True)

	data = data_redeemed_J + data_renewed_J + data_new_sangla_J + data_redeemed_NJ + data_renewed_NJ + data_new_sangla_NJ + data_pr
	columns = get_columns()
	return columns, data

def get_columns():
	columns = [
		{
			'fieldname': 'pawn_ticket',
			'label': _('Pawn Ticket'),
			'fieldtype': 'Data',
			'width': 200
		},

		{
			'fieldname': 'date_loan_granted',
			'label': _('DLG or Change Status Date'),
			'fieldtype': 'Date',
			'width': 200
		}
		
	]
	return columns