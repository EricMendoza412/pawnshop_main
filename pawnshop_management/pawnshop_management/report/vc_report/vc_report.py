# Copyright (c) 2023, Rabie Moses Santillan and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from pawnshop_management.pawnshop_management.custom_codes.get_ip import get_ip_from_settings
from frappe import get_list
from pawnshop_management.operations_access_control.vault_custodian import require_vault_custodian_access


def execute(filters=None):
	require_vault_custodian_access(filters)
	return get_vc_report_data(filters)


def get_vc_report_data(filters=None):
	status_value = getattr(filters, 'branch')
	columns, data = [], []
	branch = ""

	if status_value == None:
		branch_fr_ip = ""
		current_ip = getattr(frappe.local, "request_ip", None)
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
		elif str(current_ip) == str(branch_ip['alapan']):
			branch_fr_ip = "Garcia\\'s Pawnshop - BUC"
		elif str(current_ip) == str(branch_ip['noveleta']):
			branch_fr_ip = "Garcia\\'s Pawnshop - NOV"
		elif str(current_ip) == str(branch_ip['pascam']):
			branch_fr_ip = "Garcia\\'s Pawnshop - PSC"
		elif str(current_ip) == str(branch_ip['test']):
			branch_fr_ip = "TEST"
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

	
	data_rejected_J = frappe.db.sql(f"""
        SELECT branch, change_status_date, '' as old_pawn_ticket, workflow_state, pawn_ticket, date_loan_granted, '' as inventory_tracking_no, desired_principal, net_proceeds, '' as item_series, 'J' as pt_type, '' as interest, '' as interest_payment, '' as discount, '' as other_discount_tawad, '' as inventory_tracking, '' as previous_interest_payment
        FROM `tabPawn Ticket Jewelry`
        WHERE `tabPawn Ticket Jewelry`.docstatus=2
        AND `tabPawn Ticket Jewelry`.workflow_state = 'Rejected'
        {conditions}
    """, as_dict=True)

	data_rejected_J = [
		pt for pt in data_rejected_J
		if not frappe.db.get_value('Pawn Ticket Jewelry', {'amended_from': pt.pawn_ticket}, 'name')
	]

	data_rejected_NJ = frappe.db.sql(f"""
        SELECT branch, change_status_date, '' as old_pawn_ticket, workflow_state, pawn_ticket, date_loan_granted, '' as inventory_tracking_no, desired_principal, net_proceeds, '' as item_series, 'NJ' as pt_type, '' as interest, '' as interest_payment, '' as discount, '' as other_discount_tawad, '' as inventory_tracking, '' as previous_interest_payment
        FROM `tabPawn Ticket Non Jewelry`
        WHERE `tabPawn Ticket Non Jewelry`.docstatus=2
        AND `tabPawn Ticket Non Jewelry`.workflow_state = 'Rejected'
        {conditions3}
    """, as_dict=True)

	data_rejected_NJ = [
		ptNJ for ptNJ in data_rejected_NJ
		if not frappe.db.get_value('Pawn Ticket Non Jewelry', {'amended_from': ptNJ.pawn_ticket}, 'name')
	]

	data_redeemed_J = frappe.db.sql(f"""
        SELECT branch, change_status_date, old_pawn_ticket, workflow_state, pawn_ticket, date_loan_granted, inventory_tracking_no, desired_principal, '' as net_proceeds, item_series, 'J' as pt_type, '' as interest, '' as interest_payment, '' as discount, '' as other_discount_tawad, '' as inventory_tracking, '' as previous_interest_payment
        FROM `tabPawn Ticket Jewelry`
        WHERE `tabPawn Ticket Jewelry`.docstatus=1
        AND `tabPawn Ticket Jewelry`.workflow_state = 'Redeemed'
        {conditions}
    """, as_dict=True)
	
	data_renewed_J = frappe.db.sql(f"""
		SELECT branch, change_status_date, old_pawn_ticket, workflow_state, pawn_ticket, date_loan_granted, inventory_tracking_no, desired_principal, '' as net_proceeds, item_series, 'J' as pt_type, '' as interest, '' as interest_payment, '' as discount, '' as other_discount_tawad, '' as inventory_tracking, '' as previous_interest_payment
		FROM `tabPawn Ticket Jewelry`
		WHERE `tabPawn Ticket Jewelry`.docstatus=1
		AND `tabPawn Ticket Jewelry`.old_pawn_ticket IS NOT NULL
		{conditions2}
	""", as_dict=True)

	data_new_sangla_J = frappe.db.sql(f"""
		SELECT branch, change_status_date, '' as old_pawn_ticket, workflow_state, pawn_ticket, date_loan_granted, inventory_tracking_no, desired_principal, net_proceeds, item_series, 'J' as pt_type, '' as interest, '' as interest_payment, '' as discount, '' as other_discount_tawad, '' as inventory_tracking, '' as previous_interest_payment
		FROM `tabPawn Ticket Jewelry`
		WHERE `tabPawn Ticket Jewelry`.docstatus=1
		AND `tabPawn Ticket Jewelry`.old_pawn_ticket IS NULL		
		{conditions2}
	""", as_dict=True)

	data_redeemed_NJ = frappe.db.sql(f"""
        SELECT branch, change_status_date, old_pawn_ticket, workflow_state, pawn_ticket, date_loan_granted, inventory_tracking_no, desired_principal, '' as net_proceeds, item_series, 'NJ' as pt_type, '' as interest, '' as interest_payment, '' as discount, '' as other_discount_tawad, '' as inventory_tracking, '' as previous_interest_payment
        FROM `tabPawn Ticket Non Jewelry`
        WHERE `tabPawn Ticket Non Jewelry`.docstatus=1
        AND `tabPawn Ticket Non Jewelry`.workflow_state = 'Redeemed'
        {conditions3}
    """, as_dict=True)
	
	data_renewed_NJ = frappe.db.sql(f"""
		SELECT branch, change_status_date, old_pawn_ticket, workflow_state, pawn_ticket, date_loan_granted, inventory_tracking_no, desired_principal, net_proceeds, item_series, 'NJ' as pt_type, '' as interest, '' as interest_payment, '' as discount, '' as other_discount_tawad, '' as inventory_tracking, '' as previous_interest_payment
		FROM `tabPawn Ticket Non Jewelry`
		WHERE `tabPawn Ticket Non Jewelry`.docstatus=1
		AND `tabPawn Ticket Non Jewelry`.old_pawn_ticket IS NOT NULL
		{conditions4}
	""", as_dict=True)

	data_new_sangla_NJ = frappe.db.sql(f"""
		SELECT branch, change_status_date, '' as old_pawn_ticket, workflow_state, pawn_ticket, date_loan_granted, inventory_tracking_no, desired_principal, net_proceeds, item_series, 'NJ' as pt_type, '' as interest, '' as interest_payment, '' as discount, '' as other_discount_tawad, '' as inventory_tracking, '' as previous_interest_payment
		FROM `tabPawn Ticket Non Jewelry`
		WHERE `tabPawn Ticket Non Jewelry`.docstatus=1
		AND `tabPawn Ticket Non Jewelry`.old_pawn_ticket IS NULL
		{conditions4}
	""", as_dict=True)

	data_pr = frappe.db.sql(f"""
		SELECT
			`tabProvisional Receipt`.branch,
			`tabProvisional Receipt`.principal_amount,
			`tabProvisional Receipt`.principal_amount as change_status_date,
			`tabProvisional Receipt`.new_pawn_ticket_no as old_pawn_ticket,
			`tabProvisional Receipt`.transaction_type as workflow_state,
			`tabProvisional Receipt`.pawn_ticket_no as pawn_ticket,
			`tabProvisional Receipt`.date_issued as date_loan_granted,
			`tabProvisional Receipt`.pawn_ticket_type as inventory_tracking_no,
			`tabProvisional Receipt`.additional_amortization as desired_principal,
			`tabProvisional Receipt`.total as net_proceeds,
			COALESCE(`new_jewelry_pawn_ticket`.net_proceeds, `new_non_jewelry_pawn_ticket`.net_proceeds) as new_net_proceeds,
			`tabProvisional Receipt`.series as item_series,
			'' as pt_type,
			`tabProvisional Receipt`.interest,
			`tabProvisional Receipt`.interest_payment,
			`tabProvisional Receipt`.discount,
			`tabProvisional Receipt`.other_discount_tawad,
			`tabProvisional Receipt`.inventory_tracking,
			`tabProvisional Receipt`.previous_interest_payment,
			`tabProvisional Receipt`.date_loan_granted as dummy_date
		FROM `tabProvisional Receipt`
		LEFT JOIN `tabPawn Ticket Jewelry` `new_jewelry_pawn_ticket`
			ON `tabProvisional Receipt`.pawn_ticket_type = 'Pawn Ticket Jewelry'
			AND `new_jewelry_pawn_ticket`.pawn_ticket = `tabProvisional Receipt`.new_pawn_ticket_no
			AND `new_jewelry_pawn_ticket`.docstatus = 1
		LEFT JOIN `tabPawn Ticket Non Jewelry` `new_non_jewelry_pawn_ticket`
			ON `tabProvisional Receipt`.pawn_ticket_type = 'Pawn Ticket Non Jewelry'
			AND `new_non_jewelry_pawn_ticket`.pawn_ticket = `tabProvisional Receipt`.new_pawn_ticket_no
			AND `new_non_jewelry_pawn_ticket`.docstatus = 1
		WHERE `tabProvisional Receipt`.docstatus=1
		{conditions5}
	""", as_dict=True)

	data = data_redeemed_J + data_renewed_J + data_new_sangla_J + data_redeemed_NJ + data_renewed_NJ + data_new_sangla_NJ + data_pr + data_rejected_J + data_rejected_NJ
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
