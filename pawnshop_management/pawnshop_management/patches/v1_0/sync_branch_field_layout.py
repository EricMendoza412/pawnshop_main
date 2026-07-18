import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


BRANCH_FIELD_LAYOUT = {
	"pawnshop_details_section": "branch",
	"pawnshop_cashier": "pawnshop_details_section",
	"fx_cashier": "pawnshop_cashier",
	"remittance_cashier": "fx_cashier",
	"vault_custodian": "remittance_cashier",
	"contact_information": "vault_custodian",
	"facebook_account": "contact_information",
	"contact_number": "facebook_account",
}


def execute():
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
				"read_only": 1,
			},
			{
				"fieldname": "fx_cashier",
				"label": "FX Cashier",
				"fieldtype": "Link",
				"options": "User",
				"insert_after": "pawnshop_cashier",
				"read_only": 1,
			},
			{
				"fieldname": "remittance_cashier",
				"label": "Remittance Cashier",
				"fieldtype": "Link",
				"options": "User",
				"insert_after": "fx_cashier",
				"read_only": 1,
			},
			{
				"fieldname": "vault_custodian",
				"label": "Vault Custodian",
				"fieldtype": "Link",
				"options": "User",
				"insert_after": "remittance_cashier",
				"read_only": 1,
			},
			{
				"fieldname": "contact_information",
				"label": "Contact Information",
				"fieldtype": "Section Break",
				"insert_after": "vault_custodian",
			},
			{
				"fieldname": "facebook_account",
				"label": "Facebook Account",
				"fieldtype": "Data",
				"insert_after": "contact_information",
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
	for fieldname, insert_after in BRANCH_FIELD_LAYOUT.items():
		custom_field = frappe.db.exists("Custom Field", "Branch-{0}".format(fieldname))
		if custom_field:
			frappe.db.set_value(
				"Custom Field",
				custom_field,
				"insert_after",
				insert_after,
				update_modified=False,
			)

	frappe.clear_cache(doctype="Branch")
