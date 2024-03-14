# Copyright (c) 2021, Rabie Moses Santillan and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import today

class JewelryItems(Document):		
	def before_save(self):
		if frappe.db.exists('Pawn Ticket Jewelry', self.name) == None:
			settings = frappe.get_doc('Pawnshop Naming Series', self.branch)
			settings.jewelry_item_count += 1
			settings.save(ignore_permissions=True)


	def on_update(self):	
		query = """
			SELECT ptj.name
			FROM `tabPawn Ticket Jewelry` AS ptj
			INNER JOIN `tabJewelry List` AS jl ON ptj.name = jl.parent
			WHERE jl.item_no = %s
			ORDER BY ptj.modified DESC
			LIMIT 1
		"""
		parent_doc_name = frappe.db.sql(query, (self.name,))
		
		if parent_doc_name:
			acc_parent_doc_name = parent_doc_name[0][0]
			parent_doc = frappe.get_doc("Pawn Ticket Jewelry", acc_parent_doc_name)
			parent_pt_name = parent_doc.name

			frappe.db.set_value('Pawn Ticket Jewelry', parent_pt_name, 'workflow_state', 'Rejected')
			frappe.db.set_value('Pawn Ticket Jewelry', parent_pt_name, 'change_status_date', today())
			frappe.db.set_value('Pawn Ticket Jewelry', parent_pt_name, 'docstatus', 2)
			frappe.db.commit()

			# transfer PT details to the next version 
			previous_pawn_ticket = frappe.get_doc("Pawn Ticket Jewelry", parent_pt_name)
			new_pawn_ticket = frappe.new_doc("Pawn Ticket Jewelry")
			new_pawn_ticket.branch = previous_pawn_ticket.branch
			new_pawn_ticket.item_series = previous_pawn_ticket.item_series
			if previous_pawn_ticket.amended_from == None:
				new_pawn_ticket.pawn_ticket = str(previous_pawn_ticket.name) + '-1'
			else:
				split_old_pt = previous_pawn_ticket.name.split('-')
				split_old_pt[2] = int(split_old_pt[2]) + 1
				new_pawn_ticket.pawn_ticket = split_old_pt[0] + '-' + split_old_pt[1] + '-' + str(split_old_pt[2]) 
			new_pawn_ticket.amended_from = previous_pawn_ticket.name
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

			#recompute for Principal, Interest and Net Proceeds after saving and before submitting
			new_items = new_pawn_ticket.jewelry_items
			total_principal = 0
			for items in new_items:
				total_principal = total_principal + items.desired_principal
			new_pawn_ticket.desired_principal = total_principal
			interest_rate = previous_pawn_ticket.interest / previous_pawn_ticket.desired_principal
			new_interest = (total_principal * interest_rate)
			new_pawn_ticket.interest = new_interest
			new_pawn_ticket.net_proceeds = total_principal - new_interest
			new_pawn_ticket.submit()
		
		else:
			#perform query in Agreement to Sell
			query2 = """
				SELECT ats.name
				FROM `tabAgreement to Sell` AS ats
				INNER JOIN `tabJewelry List` AS jl ON ats.name = jl.parent
				WHERE jl.item_no = %s
				ORDER BY ats.modified DESC
				LIMIT 1
			"""
			parent_ats_name = frappe.db.sql(query2, (self.name,))
			if parent_ats_name:
				acc_parent_doc_name = parent_ats_name[0][0]
				parent_doc = frappe.get_doc("Agreement to Sell", acc_parent_doc_name)
				parent_ats_name = parent_doc.name

			frappe.db.set_value('Agreement to Sell', parent_ats_name, 'workflow_state', 'Rejected')
			frappe.db.set_value('Agreement to Sell', parent_ats_name, 'change_status_date', today())
			frappe.db.set_value('Agreement to Sell', parent_ats_name, 'docstatus', 2)
			frappe.db.commit()

			# transfer PT details to the next version 
			previous_ats = frappe.get_doc("Agreement to Sell", parent_ats_name)
			new_ats = frappe.new_doc("Agreement to Sell")
			new_ats.branch = previous_ats.branch
			if previous_ats.amended_from == None:
				new_ats.form_number= str(previous_ats.name) + '-1'
			else: 
				split_old_pt = previous_ats.name.split('-')
				split_old_pt[2] = int(split_old_pt[2]) + 1
				new_ats.form_number = split_old_pt[0] + '-' + split_old_pt[1] + '-' + str(split_old_pt[2]) 
			new_ats.amended_from = previous_ats.name
			new_ats.date_of_sale = previous_ats.date_of_sale
			new_ats.customer_tracker = previous_ats.customer_tracker
			new_ats.customer_name = previous_ats.customer_name
			new_ats.ats_tracking_no = previous_ats.ats_tracking_no
			new_ats.agreement = previous_ats.agreement
			previous_items = previous_ats.jewelry_items
			
			for i in range(len(previous_items)):
				new_ats.append("jewelry_items", {
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
			new_ats.total_value = previous_ats.total_value
			new_ats.seller_name_and_signature = previous_ats.seller_name_and_signature
			new_ats.cashier_name_and_signature = previous_ats.cashier_name_and_signature
			new_ats.appraiser_name_and_signature = previous_ats.appraiser_name_and_signature
			new_ats.save(ignore_permissions=True)

			#recompute for Total after saving and before submitting
			new_items = new_ats.jewelry_items
			total_amount = 0
			for items in new_items:
				total_amount = total_amount + items.desired_principal
			new_ats.total_value = total_amount
			new_ats.submit()



