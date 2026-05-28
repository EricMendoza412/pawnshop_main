import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
	contact_number_field = frappe.db.exists("Custom Field", "Branch-contact_number")
	if contact_number_field:
		frappe.db.set_value(
			"Custom Field",
			contact_number_field,
			"fieldtype",
			"Data",
			update_modified=False,
		)

	custom_fields = {
		"Branch": [
			{
				"fieldname": "pawnshop_details_section",
				"label": "Pawnshop Details",
				"fieldtype": "Section Break",
				"insert_after": "branch",
			},
			{
				"fieldname": "pawnshop_cashier",
				"label": "Pawnshop Cashier",
				"fieldtype": "Link",
				"options": "User",
				"insert_after": "pawnshop_details_section",
			},
			{
				"fieldname": "fx_cashier",
				"label": "FX Cashier",
				"fieldtype": "Link",
				"options": "User",
				"insert_after": "pawnshop_cashier",
			},
			{
				"fieldname": "remittance_cashier",
				"label": "Remittance Cashier",
				"fieldtype": "Link",
				"options": "User",
				"insert_after": "fx_cashier",
			},
			{
				"fieldname": "facebook_account",
				"label": "Facebook Account",
				"fieldtype": "Data",
				"insert_after": "remittance_cashier",
			},
			{
				"fieldname": "contact_number",
				"label": "Contact Number",
				"fieldtype": "Data",
				"insert_after": "facebook_account",
			},
		]
	}

	create_custom_fields(custom_fields, update=True)
	frappe.clear_cache(doctype="Branch")
