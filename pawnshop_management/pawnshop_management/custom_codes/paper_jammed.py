import frappe
from frappe.utils import today
# from flask import jsonify

RENEWAL_TRANSACTION_TYPES = ("Renewal", "Renewal w/ Amortization")


def update_connected_provisional_receipt(previous_pawn_ticket, pawn_ticket_type, old_pawn_ticket_no, new_pawn_ticket_no):
	"""Keep a renewal PR pointed at the replacement pawn ticket."""
	pr_name = previous_pawn_ticket.created_by_pr

	if pr_name and frappe.db.exists("Provisional Receipt", pr_name):
		pr = frappe.db.get_value(
			"Provisional Receipt",
			pr_name,
			["transaction_type", "new_pawn_ticket_no"],
			as_dict=True,
		)
		if pr and pr.transaction_type in RENEWAL_TRANSACTION_TYPES and pr.new_pawn_ticket_no == old_pawn_ticket_no:
			frappe.db.set_value("Provisional Receipt", pr_name, "new_pawn_ticket_no", new_pawn_ticket_no)
		return

	pr_renewal_check = frappe.get_all(
		"Provisional Receipt",
		filters={
			"pawn_ticket_type": pawn_ticket_type,
			"new_pawn_ticket_no": old_pawn_ticket_no,
			"transaction_type": ["in", RENEWAL_TRANSACTION_TYPES],
		},
		fields=["name"],
		order_by="creation desc",
		limit=1,
	)
	if pr_renewal_check:
		frappe.db.set_value("Provisional Receipt", pr_renewal_check[0].name, "new_pawn_ticket_no", new_pawn_ticket_no)


@frappe.whitelist()
def transfer_to_next_pt_j(pawn_ticket, nxt_pt):
	
    # cancel paper jammed pawn ticket
	frappe.db.set_value('Pawn Ticket Jewelry', pawn_ticket, 'workflow_state', 'Rejected')
	frappe.db.set_value('Pawn Ticket Jewelry', pawn_ticket, 'change_status_date', today())
	frappe.db.set_value('Pawn Ticket Jewelry', pawn_ticket, 'transfer_pt', nxt_pt)
	frappe.db.set_value('Pawn Ticket Jewelry', pawn_ticket, 'docstatus', 2)
	frappe.db.commit()

    # transfer paper jammed PT details to the next PT
	previous_pawn_ticket = frappe.get_doc("Pawn Ticket Jewelry", pawn_ticket)
	new_pawn_ticket = frappe.new_doc("Pawn Ticket Jewelry")
	new_pawn_ticket.branch = previous_pawn_ticket.branch
	new_pawn_ticket.item_series = previous_pawn_ticket.item_series
	#Must fetch next available pawn ticket in the same series
	new_pawn_ticket.pawn_ticket = nxt_pt
	new_pawn_ticket.date_loan_granted = previous_pawn_ticket.date_loan_granted
	new_pawn_ticket.maturity_date = previous_pawn_ticket.maturity_date
	new_pawn_ticket.expiry_date = previous_pawn_ticket.expiry_date
	new_pawn_ticket.old_pawn_ticket = previous_pawn_ticket.old_pawn_ticket
	new_pawn_ticket.customers_tracking_no = previous_pawn_ticket.customers_tracking_no
	new_pawn_ticket.customers_full_name = previous_pawn_ticket.customers_full_name
	new_pawn_ticket.inventory_tracking_no = previous_pawn_ticket.inventory_tracking_no
	new_pawn_ticket.created_by_pr = previous_pawn_ticket.created_by_pr
	new_pawn_ticket.main_appraiser_acct = previous_pawn_ticket.main_appraiser_acct
	new_pawn_ticket.main_appraiser = previous_pawn_ticket.main_appraiser
	new_pawn_ticket.assistant_appraiser_acct = previous_pawn_ticket.assistant_appraiser_acct
	new_pawn_ticket.assistant_appraiser = previous_pawn_ticket.assistant_appraiser
	previous_items = previous_pawn_ticket.jewelry_items
	for i in range(len(previous_items)):
		new_pawn_ticket.append("jewelry_items", {
		    "item_no": previous_items[i].item_no,
		    "type": previous_items[i].type,
		    "karat_category": previous_items[i].karat_category,
		    "karat": previous_items[i].karat,
		    "weight": previous_items[i].weight,
		    "color": previous_items[i].color,
		    "colors_if_multi": previous_items[i].colors_if_multi,
		    "additional_for_stone": previous_items[i].additional_for_stone,
		    "suggested_appraisal_value": previous_items[i].suggested_appraisal_value,
		    "desired_principal": previous_items[i].desired_principal,
		    "comments": previous_items[i].comments
		})
	new_pawn_ticket.desired_principal = previous_pawn_ticket.desired_principal
	new_pawn_ticket.original_principal = previous_pawn_ticket.original_principal
	new_pawn_ticket.interest = previous_pawn_ticket.interest
	new_pawn_ticket.net_proceeds = previous_pawn_ticket.net_proceeds
	new_pawn_ticket.last_j_sangla_date_in_branch = previous_pawn_ticket.last_j_sangla_date_in_branch
	new_pawn_ticket.last_j_sangla_date_in_gp = previous_pawn_ticket.last_j_sangla_date_in_gp
	new_pawn_ticket.last_nj_sangla_date_in_branch = previous_pawn_ticket.last_nj_sangla_date_in_branch
	new_pawn_ticket.last_nj_sangla_date_in_gp = previous_pawn_ticket.last_nj_sangla_date_in_gp
	new_pawn_ticket.save(ignore_permissions=True)
	new_pawn_ticket.submit()
	
	update_connected_provisional_receipt(previous_pawn_ticket, "Pawn Ticket Jewelry", pawn_ticket, nxt_pt)
	# Return something the client can use
	return {"status": "ok", "old_pt": pawn_ticket, "new_pt_docname": new_pawn_ticket.name, "new_pt": nxt_pt}

@frappe.whitelist()
def transfer_to_next_pt_nj(pawn_ticket, nxt_pt):
	
    # cancel paper jammed pawn ticket
	frappe.db.set_value('Pawn Ticket Non Jewelry', pawn_ticket, 'workflow_state', 'Rejected')
	frappe.db.set_value('Pawn Ticket Non Jewelry', pawn_ticket, 'change_status_date', today())
	frappe.db.set_value('Pawn Ticket Non Jewelry', pawn_ticket, 'transfer_pt', nxt_pt)
	frappe.db.set_value('Pawn Ticket Non Jewelry', pawn_ticket, 'docstatus', 2)
	frappe.db.commit()

    # transfer paper jammed PT details to the next PT
	previous_pawn_ticket = frappe.get_doc("Pawn Ticket Non Jewelry", pawn_ticket)
	new_pawn_ticket = frappe.new_doc("Pawn Ticket Non Jewelry")
	new_pawn_ticket.branch = previous_pawn_ticket.branch
	new_pawn_ticket.item_series = previous_pawn_ticket.item_series
	# Must fetch next available pawn ticket in the same series
	new_pawn_ticket.pawn_ticket = nxt_pt
	new_pawn_ticket.date_loan_granted = previous_pawn_ticket.date_loan_granted
	new_pawn_ticket.maturity_date = previous_pawn_ticket.maturity_date
	new_pawn_ticket.expiry_date = previous_pawn_ticket.expiry_date
	new_pawn_ticket.old_pawn_ticket = previous_pawn_ticket.old_pawn_ticket
	new_pawn_ticket.customers_tracking_no = previous_pawn_ticket.customers_tracking_no
	new_pawn_ticket.customers_full_name = previous_pawn_ticket.customers_full_name
	new_pawn_ticket.inventory_tracking_no = previous_pawn_ticket.inventory_tracking_no
	new_pawn_ticket.created_by_pr = previous_pawn_ticket.created_by_pr
	new_pawn_ticket.interest_rate = previous_pawn_ticket.interest_rate
	previous_items = previous_pawn_ticket.non_jewelry_items
	for i in range(len(previous_items)):
		new_pawn_ticket.append("non_jewelry_items", {
		    "item_no": previous_items[i].item_no,
		    "type": previous_items[i].type,
		    "brand": previous_items[i].brand,
			"model": previous_items[i].model,
			"model_number": previous_items[i].model_number,
			"suggested_appraisal_value": previous_items[i].suggested_appraisal_value
		})
	new_pawn_ticket.desired_principal = previous_pawn_ticket.desired_principal
	new_pawn_ticket.original_principal = previous_pawn_ticket.original_principal
	new_pawn_ticket.interest = previous_pawn_ticket.interest
	new_pawn_ticket.net_proceeds = previous_pawn_ticket.net_proceeds
	new_pawn_ticket.last_j_sangla_date_in_branch = previous_pawn_ticket.last_j_sangla_date_in_branch
	new_pawn_ticket.last_j_sangla_date_in_gp = previous_pawn_ticket.last_j_sangla_date_in_gp
	new_pawn_ticket.last_nj_sangla_date_in_branch = previous_pawn_ticket.last_nj_sangla_date_in_branch
	new_pawn_ticket.last_nj_sangla_date_in_gp = previous_pawn_ticket.last_nj_sangla_date_in_gp
	new_pawn_ticket.save(ignore_permissions=True)
	new_pawn_ticket.submit()

	update_connected_provisional_receipt(previous_pawn_ticket, "Pawn Ticket Non Jewelry", pawn_ticket, nxt_pt)
	# Return something the client can use
	return {"status": "ok", "old_pt": pawn_ticket, "new_pt_docname": new_pawn_ticket.name, "new_pt": nxt_pt}
