import frappe
from frappe.utils import today
# from flask import jsonify

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
	new_pawn_ticket.interest = previous_pawn_ticket.interest
	new_pawn_ticket.net_proceeds = previous_pawn_ticket.net_proceeds
	new_pawn_ticket.save(ignore_permissions=True)
	new_pawn_ticket.submit()
	
	# check if from Renewal, replace the New Pawn ticket field with the correct PT
	pr_renewal_check = frappe.get_all("Provisional Receipt", filters={"new_pawn_ticket_no": pawn_ticket, "date_issued": today()}, fields=["name"])
	if pr_renewal_check:
		frappe.db.set_value('Provisional Receipt',pr_renewal_check[0].name, 'new_pawn_ticket_no',nxt_pt)

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
	new_pawn_ticket.interest = previous_pawn_ticket.interest
	new_pawn_ticket.net_proceeds = previous_pawn_ticket.net_proceeds
	new_pawn_ticket.save(ignore_permissions=True)
	new_pawn_ticket.submit()

	# check if from Renewal, replace the New Pawn ticket field with the correct PT
	pr_renewal_check = frappe.get_all("Provisional Receipt", filters={"new_pawn_ticket_no": pawn_ticket, "date_issued": today()}, fields=["name"])
	if pr_renewal_check:
		frappe.db.set_value('Provisional Receipt',pr_renewal_check[0].name, 'new_pawn_ticket_no',nxt_pt)