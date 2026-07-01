# Copyright (c) 2021, Rabie Moses Santillan and contributors
# For license information, please see license.txt

# from pydoc import doc
import frappe
from frappe.model.document import Document
from frappe.utils import today

class NonJewelryItems(Document):
	def validate(self):
		self.validate_assistant_appraiser_edit()

	def validate_assistant_appraiser_edit(self):
		if self.is_new():
			return

		previous_doc = self.get_doc_before_save()
		if not previous_doc or previous_doc.assistant_appraiser == self.assistant_appraiser:
			return

		if frappe.session.user == "Administrator" or "Administrator" in frappe.get_roles(frappe.session.user):
			return

		frappe.throw("Only Administrator can edit Assistant Appraiser.")

	def before_save(self):
		self.remove_empty_reserved_buyers()

		# if the status is Pawned and the document is new, increment the item count in the naming series	
		if frappe.db.exists('Pawn Ticket Non Jewelry', self.name) == None and self.workflow_state == 'Pawned':
			if frappe.db.exists('Pawnshop Naming Series', self.branch):
				settings = frappe.get_doc('Pawnshop Naming Series', self.branch)
				# if branch is Subastado NJ, increment the inventory count and not the item count
				if self.branch == 'Subastado NJ':
					settings.inventory_count += 1
				else:			
					settings.item_count += 1
				settings.save(ignore_permissions=True)

	def remove_empty_reserved_buyers(self):
		self.reserved_buyers = [
			row for row in self.get("reserved_buyers", [])
			if row.customer_name or row.reservation_datetime or row.comments or row.reserved_by
		]

	def on_update(self):
		query = """
			SELECT ptnj.name
			FROM `tabPawn Ticket Non Jewelry` AS ptnj
			INNER JOIN `tabNon Jewelry List` AS njl ON ptnj.name = njl.parent
			WHERE njl.item_no = %s
			ORDER BY ptnj.modified DESC
			LIMIT 1
		"""
		parent_doc_name = frappe.db.sql(query, (self.name,))

		if not parent_doc_name:
			return

		parent_pt_name = parent_doc_name[0][0]
		previous_workflow_state = frappe.db.get_value(
			"Pawn Ticket Non Jewelry", parent_pt_name, "workflow_state"
		)
		if previous_workflow_state not in ("Active", "Expired"):
			return

		frappe.db.set_value('Pawn Ticket Non Jewelry', parent_pt_name, 'workflow_state', 'Rejected')
		frappe.db.set_value('Pawn Ticket Non Jewelry', parent_pt_name, 'change_status_date', today())
		frappe.db.set_value('Pawn Ticket Non Jewelry', parent_pt_name, 'docstatus', 2)
		frappe.db.commit()

		previous_pawn_ticket = frappe.get_doc("Pawn Ticket Non Jewelry", parent_pt_name)
		new_pawn_ticket = frappe.new_doc("Pawn Ticket Non Jewelry")
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
		new_pawn_ticket.customer_birthday = previous_pawn_ticket.customer_birthday
		new_pawn_ticket.inventory_tracking_no = previous_pawn_ticket.inventory_tracking_no
		new_pawn_ticket.created_by_pr = previous_pawn_ticket.created_by_pr
		new_pawn_ticket.comments = previous_pawn_ticket.comments
		new_pawn_ticket.original_principal = previous_pawn_ticket.original_principal
		new_pawn_ticket.interest_rate = previous_pawn_ticket.interest_rate
		new_pawn_ticket.last_j_sangla_date_in_branch = previous_pawn_ticket.last_j_sangla_date_in_branch
		new_pawn_ticket.last_j_sangla_date_in_gp = previous_pawn_ticket.last_j_sangla_date_in_gp
		new_pawn_ticket.last_nj_sangla_date_in_branch = previous_pawn_ticket.last_nj_sangla_date_in_branch
		new_pawn_ticket.last_nj_sangla_date_in_gp = previous_pawn_ticket.last_nj_sangla_date_in_gp
		new_pawn_ticket.texted_upon_maturity = previous_pawn_ticket.texted_upon_maturity
		new_pawn_ticket.texted_upon_expiry = previous_pawn_ticket.texted_upon_expiry

		previous_items = previous_pawn_ticket.non_jewelry_items
		for i in range(len(previous_items)):
			new_pawn_ticket.append("non_jewelry_items", {
				"item_no": previous_items[i].item_no,
				"type": previous_items[i].type,
				"brand": previous_items[i].brand,
				"model": previous_items[i].model,
				"model_number": previous_items[i].model_number,
				"suggested_appraisal_value": previous_items[i].suggested_appraisal_value,
				"main_appraiser": previous_items[i].main_appraiser
			})

		new_pawn_ticket.desired_principal = previous_pawn_ticket.desired_principal
		new_pawn_ticket.interest = previous_pawn_ticket.interest
		new_pawn_ticket.net_proceeds = previous_pawn_ticket.net_proceeds
		new_pawn_ticket.save(ignore_permissions=True)

		total_principal = previous_pawn_ticket.desired_principal
		if previous_pawn_ticket.interest_rate:
			used_interest_rate = previous_pawn_ticket.interest_rate / 100
		elif previous_pawn_ticket.desired_principal:
			used_interest_rate = previous_pawn_ticket.interest / previous_pawn_ticket.desired_principal
		else:
			used_interest_rate = 0

		new_interest = total_principal * used_interest_rate
		new_pawn_ticket.desired_principal = total_principal
		new_pawn_ticket.interest = new_interest
		new_pawn_ticket.net_proceeds = total_principal - new_interest
		new_pawn_ticket.submit()
