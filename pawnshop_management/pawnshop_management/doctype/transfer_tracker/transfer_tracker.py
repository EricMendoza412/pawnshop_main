# Copyright (c) 2024, Rabie Moses Santillan and contributors
# For license information, please see license.txt

# import frappe
import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime
from pawnshop_management.operations_access_control.access_control import (
	has_active_branch_role,
	is_system_manager,
)
from pawnshop_management.operations_access_control.vault_custodian import require_vault_custodian_access


class TransferTracker(Document):
	def validate(self):
		if not is_system_manager(frappe.session.user):
			require_vault_custodian_access(branch=self.origin)

	def before_submit(self):
		if not is_system_manager(frappe.session.user):
			require_vault_custodian_access(branch=self.origin)

		if not self.witnessed_by or not self.rover:
			frappe.throw("Witnessed By and Rover are required before submitting Transfer Tracker.")

		for item in self.nj_items:
			if item.item_no:
				item.previous_workflow_state = frappe.db.get_value(
					'Non Jewelry Items',
					item.item_no,
					'workflow_state'
				)

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
					item_doc.workflow_state = "Reserved" if item.previous_workflow_state == "Reserved" else "For Sale"
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
def get_pawn_ticket_series(doctype, tickets):
	if doctype not in ("Pawn Ticket Jewelry", "Pawn Ticket Non Jewelry"):
		frappe.throw("Invalid pawn ticket doctype")

	if isinstance(tickets, str):
		tickets = frappe.parse_json(tickets)

	ticket_names = sorted({ticket for ticket in (tickets or []) if ticket})
	if not ticket_names:
		return []

	return frappe.get_all(
		doctype,
		fields=["name", "item_series"],
		filters={"name": ["in", ticket_names]},
		limit_page_length=0,
	)


@frappe.whitelist()
def get_non_jewelry_pullout_items(origin, from_date, to_date):
	require_vault_custodian_access(branch=origin)

	if not origin or not from_date or not to_date:
		return []

	pawn_tickets = frappe.get_all(
		"Pawn Ticket Non Jewelry",
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

	non_jewelry_rows = frappe.get_all(
		"Non Jewelry List",
		fields=["parent", "item_no", "type"],
		filters={
			"parent": ["in", ticket_names],
			"parenttype": "Pawn Ticket Non Jewelry",
		},
		order_by="parent asc, idx asc",
		limit_page_length=0,
	)

	if not non_jewelry_rows:
		return []

	item_names = sorted({row.item_no for row in non_jewelry_rows if row.item_no})
	item_info_map = {}
	if item_names:
		item_info_map = {
			row.name: row
			for row in frappe.get_all(
				"Non Jewelry Items",
				fields=["name", "selling_price", "charger", "case", "box", "bag", "type"],
				filters={"name": ["in", item_names]},
				limit_page_length=0,
			)
		}

	result = []
	for row in non_jewelry_rows:
		ticket = ticket_map.get(row.parent)
		item_info = item_info_map.get(row.item_no)
		if not ticket or not item_info:
			continue

		result.append(
			{
				"last_pawn_ticket": row.parent,
				"item_no": row.item_no,
				"type": row.type or item_info.type,
				"charger": item_info.charger or 0,
				"case": item_info.case or 0,
				"box": item_info.box or 0,
				"bag": item_info.bag or 0,
				"pt_principal": ticket.desired_principal or 0,
				"selling_price": item_info.selling_price or 0,
				"date_loan_granted": ticket.date_loan_granted,
			}
		)

	return result


@frappe.whitelist()
def get_jewelry_pullout_items(origin, from_date, to_date):
	require_vault_custodian_access(branch=origin)

	if not origin or not from_date or not to_date:
		return []

	pawn_tickets = frappe.get_all(
		"Pawn Ticket Jewelry",
		fields=["name", "item_series", "desired_principal", "date_loan_granted"],
		filters={
			"branch": origin,
			"date_loan_granted": ["between", [from_date, to_date]],
			"workflow_state": ["in", ["Active", "Expired"]],
			"docstatus": 1,
		},
		order_by="item_series asc, date_loan_granted asc, name asc",
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


@frappe.whitelist()
def get_sb_jewelry_pullout_items(origin, from_date, to_date):
	require_vault_custodian_access(branch=origin)

	if not origin or not from_date or not to_date:
		return []

	agreement_docs = frappe.get_all(
		"Agreement to Sell",
		fields=["name", "date_of_sale"],
		filters={
			"branch": origin,
			"date_of_sale": ["between", [from_date, to_date]],
			"workflow_state": "Active",
			"docstatus": 1,
		},
		order_by="date_of_sale asc, name asc",
		limit_page_length=0,
	)

	if not agreement_docs:
		return []

	agreement_names = [doc.name for doc in agreement_docs]

	jewelry_rows = frappe.get_all(
		"Jewelry List",
		fields=["parent", "item_no", "type", "karat", "weight", "densi", "color"],
		filters={
			"parent": ["in", agreement_names],
			"parenttype": "Agreement to Sell",
		},
		order_by="parent asc, idx asc",
		limit_page_length=0,
	)

	if not jewelry_rows:
		return []

	item_names = sorted({row.item_no for row in jewelry_rows if row.item_no})
	item_info_map = {}
	if item_names:
		item_info_map = {
			row.name: row
			for row in frappe.get_all(
				"Jewelry Items",
				fields=["name", "appraisal_value", "selling_price", "total_weight", "karat", "color", "densi", "type"],
				filters={"name": ["in", item_names]},
				limit_page_length=0,
			)
		}

	result = []
	for row in jewelry_rows:
		item_info = item_info_map.get(row.item_no)
		if not item_info:
			continue

		result.append(
			{
				"last_pawn_ticket": row.parent,
				"item_no": row.item_no,
				"type": row.type or item_info.type,
				"weight": row.weight or item_info.total_weight,
				"karat": row.karat or item_info.karat,
				"color": row.color or item_info.color,
				"densi": row.densi or item_info.densi,
				"principal": item_info.appraisal_value or 0,
				"selling_price": item_info.selling_price or 0,
			}
		)

	return result


def get_permission_query_conditions(user=None):
	user = user or frappe.session.user
	if is_system_manager(user):
		return None

	escaped_user = frappe.db.escape(user)
	return (
		"exists (select `tabBranch`.`name` "
		"from `tabBranch` "
		"where `tabBranch`.`name` = `tabTransfer Tracker`.`origin` "
		f"and `tabBranch`.`vault_custodian` = {escaped_user})"
	)


def has_permission(doc, ptype=None, user=None):
	user = user or frappe.session.user
	if is_system_manager(user):
		return True

	branch = getattr(doc, "origin", None)
	if not branch:
		return False

	return has_active_branch_role(user, branch, "Vault Custodian")
