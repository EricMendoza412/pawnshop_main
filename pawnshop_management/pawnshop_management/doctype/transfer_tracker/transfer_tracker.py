# Copyright (c) 2024, Rabie Moses Santillan and contributors
# For license information, please see license.txt

# import frappe
import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime


class TransferTracker(Document):
	def before_save(self):
		if frappe.db.exists('Transfer Tracker', self.name) == None:
			if self.amended_from == None:
				settings = frappe.get_doc('Pawnshop Naming Series', self.origin)
				settings.nj_transfer_form += 1
				settings.save(ignore_permissions=True)

	def on_update(self):
		if self.workflow_state == "For Receiving":
			#change workflow state of all items in the child table to In Transit
			for item in self.nj_items:
				# item_doc = frappe.get_doc('Non Jewelry Items', item.item_no)
				# item_doc.workflow_state = "In Transit"
				# item_doc.save(ignore_permissions=True)
				frappe.db.set_value('Non Jewelry Items', item.item_no, 'workflow_state', 'In Transit')
				#change workflow state of all pawn tickets in the child table to Pulled Out if the transfer type is Pull out of Expired Sangla
				if self.transfer_type == "Pull out of Expired Sangla":
					item_pawnticket = frappe.get_doc('Pawn Ticket Non Jewelry', item.last_pawn_ticket)
					item_pawnticket.db_set('workflow_state', 'Pulled Out', update_modified=True)
					item_pawnticket.db_set('change_status_date', now_datetime(), update_modified=True)
			for item in self.j_items:
				# item_doc = frappe.get_doc('Jewelry Items', item.item_no)
				# item_doc.workflow_state = "In Transit"
				# item_doc.save(ignore_permissions=True)
				frappe.db.set_value('Jewelry Items', item.item_no, 'workflow_state', 'In Transit')

				if self.transfer_type == "Pull out of Expired Sangla":
					item_pawnticket = frappe.get_doc('Pawn Ticket Jewelry', item.last_pawn_ticket)
					item_pawnticket.db_set('workflow_state', 'Pulled Out', update_modified=True)
					item_pawnticket.db_set('change_status_date', now_datetime(), update_modified=True)

			for item in self.sb_items:
				frappe.db.set_value('Jewelry Items', item.item_no, 'workflow_state', 'In Transit')
				if self.transfer_type == "Pull out of Expired Sangla":
					item_pawnticket = frappe.get_doc('Agreement to Sell', item.last_pawn_ticket)
					item_pawnticket.db_set('workflow_state', 'Pulled Out', update_modified=True)
					item_pawnticket.db_set('change_status_date', now_datetime(), update_modified=True)

			
	#Do something when document changes status from For Receiving to Complete
	def on_update_after_submit(self):
		if self.workflow_state == "Complete":
			#Update the item location in Item table depending on transfer type
			if self.transfer_type == "Pull out of Expired Sangla":
				#change current_location of all items in the child table to Subastado NJ
				for item in self.nj_items:
					item_doc = frappe.get_doc('Non Jewelry Items', item.item_no)
					item_doc.current_location = self.destination
					item_doc.pt_principal = item.pt_principal
					item_doc.workflow_state = "Unprocessed"
					item_doc.date_received = now_datetime()
					item_doc.save(ignore_permissions=True)
				for item in self.j_items:
					frappe.db.set_value('Jewelry Items', item.item_no, 'workflow_state', 'Unprocessed')
					frappe.db.set_value('Jewelry Items', item.item_no, 'pt_principal', item.principal)
					frappe.db.set_value('Jewelry Items', item.item_no, 'current_location', self.destination)
					frappe.db.set_value('Jewelry Items', item.item_no, 'date_received', now_datetime())
				for item in self.sb_items:
					frappe.db.set_value('Jewelry Items', item.item_no, 'workflow_state', 'Unprocessed')
					frappe.db.set_value('Jewelry Items', item.item_no, 'pt_principal', item.principal)
					frappe.db.set_value('Jewelry Items', item.item_no, 'current_location', self.destination)
					frappe.db.set_value('Jewelry Items', item.item_no, 'date_received', now_datetime())
					
			elif self.transfer_type == "Transfer of Display Items":
				#change current_location of all items in the child table to destination
				for item in self.nj_items:
					item_doc = frappe.get_doc('Non Jewelry Items', item.item_no)
					item_doc.current_location = self.destination
					item_doc.workflow_state = "For Sale"
					item_doc.save(ignore_permissions=True)
				for item in self.j_items:
					frappe.db.set_value('Jewelry Items', item.item_no, 'workflow_state', 'For Sale')
					frappe.db.set_value('Jewelry Items', item.item_no, 'current_location', self.destination)
					if self.transfer_type == "Issue as company used item" or self.destination == "Accounting Office":
						frappe.db.set_value('Jewelry Items', item.item_no, 'person_responsible', self.person_responsible)

			elif self.transfer_type == "Issue as company used item":
				#change current_location of all items in the child table to destination
				for item in self.nj_items:
					item_doc = frappe.get_doc('Non Jewelry Items', item.item_no)
					item_doc.current_location = self.destination
					item_doc.workflow_state = "Company used"
					if self.destination == "Accounting Office":
						item_doc.person_accountable = frappe.session.user
					else:
						item_doc.person_accountable = None
					item_doc.save(ignore_permissions=True)

			# # put date today in date_received and put name of current user in the field received_by
			self.db_set('date_received', now_datetime(), update_modified=True)
			self.db_set('received_by', frappe.session.user, update_modified=True)


@frappe.whitelist()
def get_jewelry_pullout_items(origin, from_date, to_date):
	if not origin or not from_date or not to_date:
		return []

	pawn_tickets = frappe.get_all(
		"Pawn Ticket Jewelry",
		fields=["name", "desired_principal", "date_loan_granted"],
		filters={
			"branch": origin,
			"date_loan_granted": ["between", [from_date, to_date]],
			"workflow_state": ["in", ["Active", "Expired"]],
			"docstatus": 1,
		},
		order_by="date_loan_granted asc, name asc",
		limit_page_length=0,
	)

	if not pawn_tickets:
		return []

	ticket_names = [ticket.name for ticket in pawn_tickets]
	ticket_map = {ticket.name: ticket for ticket in pawn_tickets}

	jewelry_rows = frappe.get_all(
		"Jewelry List",
		fields=[
			"parent",
			"item_no",
			"type",
			"karat",
			"weight",
			"densi",
			"color",
			"suggested_appraisal_value",
		],
		filters={
			"parent": ["in", ticket_names],
			"parenttype": "Pawn Ticket Jewelry",
		},
		order_by="parent asc, idx asc",
		limit_page_length=0,
	)

	if not jewelry_rows:
		return []

	item_names = sorted({row.item_no for row in jewelry_rows if row.item_no})
	selling_price_map = {}
	if item_names:
		selling_price_map = {
			row.name: row.selling_price
			for row in frappe.get_all(
				"Jewelry Items",
				fields=["name", "selling_price"],
				filters={"name": ["in", item_names]},
				limit_page_length=0,
			)
		}

	items_by_ticket = {}
	for row in jewelry_rows:
		items_by_ticket.setdefault(row.parent, []).append(row)

	result = []
	for ticket_name in ticket_names:
		ticket = ticket_map[ticket_name]
		items = items_by_ticket.get(ticket_name, [])
		total_appraisal = sum((row.suggested_appraisal_value or 0) for row in items)
		allocated_principal = 0

		for index, item in enumerate(items):
			appraisal_value = item.suggested_appraisal_value or 0
			if index == len(items) - 1:
				principal = (ticket.desired_principal or 0) - allocated_principal
			elif total_appraisal:
				principal = round((ticket.desired_principal or 0) * (appraisal_value / total_appraisal))
				allocated_principal += principal
			else:
				principal = 0

			result.append(
				{
					"last_pawn_ticket": ticket_name,
					"item_no": item.item_no,
					"type": item.type,
					"weight": item.weight,
					"karat": item.karat,
					"color": item.color,
					"densi": item.densi,
					"principal": principal,
					"selling_price": selling_price_map.get(item.item_no, 0),
					"date_loan_granted": ticket.date_loan_granted,
				}
			)

	return result
