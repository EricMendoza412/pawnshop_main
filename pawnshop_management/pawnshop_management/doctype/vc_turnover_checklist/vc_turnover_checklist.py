# Copyright (c) 2026, Rabie Santillan and Eric Mendoza and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.naming import make_autoname
from frappe.utils import cint, flt, getdate, now_datetime, today

from pawnshop_management.pawnshop_management.doctype.pawnshop_transaction_log.pawnshop_transaction_log import (
	get_branch_code,
)
from pawnshop_management.pawnshop_management.report.vc_turnover_list.vc_turnover_list import (
	execute as execute_vc_turnover_list,
)
from pawnshop_management.operations_access_control.access_control import (
	get_active_branch_role_user,
	has_active_branch_role,
	require_active_branch_role,
)


TURNOVER_LIST_TYPES = ("A-Jewelry", "B-Jewelry", "B-Non Jewelry", "Agreement to Sell")
GADGET_WORKFLOW_STATES = ("For Sale", "Reserved")
MANAGER_ROLES = {"Operations Manager", "Supervisor"}
PHP_BREAKDOWN_FIELDS = {
	1000.0: "php_1000",
	500.0: "php_500",
	200.0: "php_200",
	100.0: "php_100",
	50.0: "php_50",
	20.0: "php_20",
	10.0: "php_10",
	5.0: "php_5",
	1.0: "php_1",
	0.25: "php_025",
}
USD_BREAKDOWN_FIELDS = {
	100.0: "usd_100",
	50.0: "usd_50",
	20.0: "usd_20",
	10.0: "usd_10",
	5.0: "usd_5",
	2.0: "usd_2",
	1.0: "usd_1",
}


class VCTurnoverChecklist(Document):
	def autoname(self):
		branch_code = get_branch_code(self.branch)
		if branch_code:
			self.name = make_autoname(f"VCT{branch_code}-.######")
			return

		self.name = make_autoname("VCT-.######")

	def before_validate(self):
		if self.is_new() and not self.workflow_state:
			self.workflow_state = "Draft"

		if self.is_new():
			self.branch = get_branch_from_request_ip()
			self.date = today()

		if not self.branch:
			self.branch = get_branch_from_request_ip()

		if not self.date:
			self.date = today()

		self.populate_system_fields()
		if self.docstatus == 0:
			self.populate_vault_cash_fields()
		self.calculate_totals()

	def validate(self):
		if not self.endorsed_by:
			frappe.throw(_("Endorser cannot be found, please contact IT department."))

		if self.docstatus == 1 and not self.received_by:
			frappe.throw(_("Received By is required before submitting VC Turnover Checklist."))

		self.validate_acceptance()
		self.validate_manual_cash_breakdowns()

	def before_submit(self):
		self.populate_system_fields()
		self.calculate_totals()

		if not self.endorsed_by:
			frappe.throw(_("Endorser cannot be found, please contact IT department."))

		if not self.received_by:
			frappe.throw(_("Received By is required before submitting VC Turnover Checklist."))

		if self.workflow_state != "For Acceptance":
			frappe.throw(_("Submit the VC Turnover Checklist through the workflow action."))

	def on_submit(self):
		sync_acceptance_workflow_action(self)

	def before_cancel(self):
		if self.workflow_state not in {"For Acceptance", "Rejected"}:
			frappe.throw(_("Only VC Turnover Checklists pending acceptance can be rejected."))

	def on_cancel(self):
		self.db_set("workflow_state", "Rejected", update_modified=False)
		sync_acceptance_workflow_action(self)

	def on_update_after_submit(self):
		sync_acceptance_workflow_action(self)
		if self.workflow_state == "Accepted":
			self.update_branch_vault_custodian()

	def validate_acceptance(self):
		if self.workflow_state != "Accepted":
			return

		if frappe.session.user != self.received_by:
			frappe.throw(_("Only the Received By user can accept this VC Turnover Checklist."), frappe.PermissionError)

		if not self.accepted_by:
			self.accepted_by = frappe.session.user

		if not self.accepted_datetime:
			self.accepted_datetime = now_datetime()

	def update_branch_vault_custodian(self):
		frappe.db.set_value("Branch", self.branch, "vault_custodian", self.received_by)
		frappe.clear_cache(doctype="Branch")

	def populate_system_fields(self):
		if not self.branch:
			self.branch = get_branch_from_request_ip()

		if self.branch:
			self.endorsed_by = get_active_branch_role_user(self.branch, "Vault Custodian")

		self.populate_gadget_counts()
		self.populate_turnover_items()

	def populate_gadget_counts(self):
		counts = get_gadget_counts(self.branch)
		self.cellphone_count = counts.get("Cellphone", 0)
		self.tablet_count = counts.get("Tablet", 0)
		self.laptop_count = counts.get("Laptop", 0)
		self.dslr_count = counts.get("Camera", 0)
		self.gadget_under_installment = get_non_jewelry_item_count(
			self.branch,
			"Under Installment",
		)
		self.branch_mobile_phones = get_non_jewelry_item_count(
			self.branch,
			"Company Used",
		)

	def populate_turnover_items(self):
		if not self.branch:
			return

		rows = get_turnover_rows(self.branch)
		self.set("turnover_items", [])

		for source in rows:
			row = self.append("turnover_items", {})
			row.list_type = source.get("list_type")
			row.inventory_tracker = source.get("inventory_tracker")
			row.customer_name = source.get("customer_name")
			row.reference_no = source.get("reference_no")
			row.item_description = source.get("item_description")
			row.amount = source.get("amount")
			row.date_loan_granted = source.get("date_loan_granted")
			row.maturity_date = source.get("maturity_date")
			row.expiry_date = source.get("expiry_date")
			row.date_of_sale = source.get("date_of_sale")

		self.sangla_envelopes_cb = sum(1 for row in rows if row.get("list_type") == "A-Jewelry")
		self.sangla_envelopes_ncb = sum(1 for row in rows if row.get("list_type") == "B-Jewelry")
		self.sangla_non_jewelry = sum(1 for row in rows if row.get("list_type") == "B-Non Jewelry")
		self.sanglang_benta = sum(1 for row in rows if row.get("list_type") == "Agreement to Sell")

	def populate_vault_cash_fields(self):
		if not self.branch:
			return

		previous = _get_stored_cash_sources(self)
		values = get_vault_cash_autofill(self.branch, self.date)

		for currency, total_field, breakdown_fields in (
			("php", "forex_reserved_php", PHP_BREAKDOWN_FIELDS.values()),
			("usd", "forex_reserved_usd", USD_BREAKDOWN_FIELDS.values()),
		):
			source_type = values.get(f"{currency}_cash_source_type") or ""
			source_document = values.get(f"{currency}_cash_source_document") or ""
			self.set(total_field, values.get(total_field) or 0)

			breakdown = values.get(f"{currency}_breakdown")
			if source_type == "Vault Cash Position" or not source_type:
				for fieldname in breakdown_fields:
					self.set(fieldname, (breakdown or {}).get(fieldname, 0))
			elif _should_clear_transfer_breakdown(previous, currency, self.branch):
				for fieldname in breakdown_fields:
					self.set(fieldname, 0)

			self.set(f"{currency}_cash_source_type", source_type)
			self.set(f"{currency}_cash_source_document", source_document)

	def validate_manual_cash_breakdowns(self):
		for currency, source_field, total_field, breakdown_total_field in (
			("PHP", "php_cash_source_type", "forex_reserved_php", "php_total"),
			("USD", "usd_cash_source_type", "forex_reserved_usd", "usd_total"),
		):
			if self.get(source_field) != "Fund Transfer":
				continue

			in_vault = flt(self.get(total_field), 2)
			breakdown_total = flt(self.get(breakdown_total_field), 2)
			if abs(in_vault - breakdown_total) > 0.005:
				frappe.throw(
					_("{0} Reserved Cash Breakdown total must equal {0} In Vault ({1}).").format(
						currency, frappe.format_value(in_vault, {"fieldtype": "Currency"})
					)
				)

	def calculate_totals(self):
		self.jewelry_display_total = sum(
			cint(self.get(fieldname) or 0)
			for fieldname in (
				"necklace_count",
				"pendant_count",
				"earrings_count",
				"rings_count",
				"bracelet_count",
				"bangle_count",
				"set_count",
			)
		)
		self.gadgets_display_total = sum(
			cint(self.get(fieldname) or 0)
			for fieldname in ("cellphone_count", "tablet_count", "laptop_count", "dslr_count")
		)
		self.php_total = sum(
			flt(self.get(fieldname) or 0)
			for fieldname in (
				"php_1000",
				"php_500",
				"php_200",
				"php_100",
				"php_50",
				"php_20",
				"php_10",
				"php_5",
				"php_1",
				"php_025",
			)
		)
		self.usd_total = sum(
			flt(self.get(fieldname) or 0)
			for fieldname in ("usd_100", "usd_50", "usd_20", "usd_10", "usd_5", "usd_2", "usd_1")
		)
		self.petty_cash_total = sum(
			flt(self.get(fieldname) or 0)
			for fieldname in (
				"petty_php_1000",
				"petty_php_500",
				"petty_php_200",
				"petty_php_100",
				"petty_php_50",
				"petty_php_20",
				"petty_php_10",
				"petty_php_5",
				"petty_php_1",
				"petty_php_025",
			)
		)


def get_turnover_rows(branch):
	rows = []

	for list_type in TURNOVER_LIST_TYPES:
		_filters = frappe._dict({"branch": branch, "series": list_type})
		_columns, data = execute_vc_turnover_list(_filters)

		for item in data:
			if list_type == "Agreement to Sell":
				if not item.get("date_of_sale"):
					continue

				rows.append(
					frappe._dict(
						list_type=list_type,
						inventory_tracker=item.get("ats_tracking_no"),
						customer_name=item.get("customer_name"),
						reference_no=item.get("form_number"),
						item_description=item.get("description"),
						amount=item.get("total_value"),
						date_of_sale=item.get("date_of_sale"),
					)
				)
			else:
				if not item.get("date_loan_granted"):
					continue

				rows.append(
					frappe._dict(
						list_type=list_type,
						inventory_tracker=item.get("inventory_tracking_no"),
						customer_name=item.get("customers_full_name"),
						reference_no=item.get("pawn_ticket"),
						item_description=item.get("description"),
						amount=item.get("desired_principal"),
						date_loan_granted=item.get("date_loan_granted"),
						maturity_date=item.get("maturity_date"),
						expiry_date=item.get("expiry_date"),
					)
				)

	return rows


def get_gadget_counts(branch):
	if not branch:
		return {}

	result = frappe._dict({"Cellphone": 0, "Tablet": 0, "Laptop": 0, "Camera": 0})
	rows = frappe.get_all(
		"Non Jewelry Items",
		fields=["type", "count(name) as count"],
		filters={
			"current_location": branch,
			"workflow_state": ["in", GADGET_WORKFLOW_STATES],
		},
		group_by="type",
		limit_page_length=0,
	)

	for row in rows:
		if row.type in result:
			result[row.type] = cint(row.count)

	return result


def get_non_jewelry_item_count(branch, workflow_state):
	if not branch:
		return 0

	return cint(
		frappe.db.count(
			"Non Jewelry Items",
			{
				"current_location": branch,
				"workflow_state": workflow_state,
			},
		)
	)


def get_branch_from_request_ip():
	current_ip = getattr(frappe.local, "request_ip", None)
	if not current_ip:
		return None

	branch = frappe.db.get_value(
		"Branch IP Addressing",
		{"ip_address": current_ip},
		["name", "branch"],
		as_dict=True,
	)

	if not branch:
		return None

	return branch.name or branch.branch


@frappe.whitelist()
def get_default_branch():
	return get_branch_from_request_ip()


def get_vault_cash_autofill(branch, business_date=None):
	business_date = getdate(business_date or today())
	values = {}
	vault_cash_position = frappe.db.get_value(
		"Vault Cash Position",
		{
			"branch": branch,
			"business_date": ["<=", business_date],
			"docstatus": 1,
		},
		"name",
		order_by="business_date desc, count_datetime desc, creation desc",
	)
	vault_doc = frappe.get_doc("Vault Cash Position", vault_cash_position) if vault_cash_position else None

	for currency, total_field, actual_cash_field, table_field, breakdown_fields in (
		("php", "forex_reserved_php", "php_actual_cash", "php_denominations", PHP_BREAKDOWN_FIELDS),
		("usd", "forex_reserved_usd", "usd_actual_cash", "usd_denominations", USD_BREAKDOWN_FIELDS),
	):
		fund_transfer = frappe.db.get_value(
			"Fund Transfer",
			{
				"branch": branch,
				"business_date": business_date,
				"currency": currency.upper(),
				"docstatus": 1,
				"status": "Submitted",
			},
			["name", "civ_balance"],
			as_dict=True,
			order_by="date_of_transfer desc, creation desc",
		)

		if fund_transfer:
			values.update(
				{
					total_field: flt(fund_transfer.civ_balance),
					f"{currency}_cash_source_type": "Fund Transfer",
					f"{currency}_cash_source_document": fund_transfer.name,
					f"{currency}_breakdown": None,
				}
			)
			continue

		if vault_doc:
			breakdown = {fieldname: 0 for fieldname in breakdown_fields.values()}
			for row in vault_doc.get(table_field):
				fieldname = breakdown_fields.get(flt(row.denomination))
				if fieldname:
					breakdown[fieldname] = flt(row.amount)
			values.update(
				{
					total_field: flt(vault_doc.get(actual_cash_field)),
					f"{currency}_cash_source_type": "Vault Cash Position",
					f"{currency}_cash_source_document": vault_doc.name,
					f"{currency}_breakdown": breakdown,
				}
			)
			continue

		values.update(
			{
				total_field: 0,
				f"{currency}_cash_source_type": "",
				f"{currency}_cash_source_document": "",
				f"{currency}_breakdown": {fieldname: 0 for fieldname in breakdown_fields.values()},
			}
		)

	return values


@frappe.whitelist()
def get_vault_cash_autofill_values(branch, business_date=None):
	if not branch:
		branch = get_branch_from_request_ip()
	if not branch:
		return {}
	require_active_branch_role(frappe.session.user, branch, "Vault Custodian")
	return get_vault_cash_autofill(branch, business_date)


def _get_stored_cash_sources(doc):
	if doc.is_new() or not doc.name:
		return frappe._dict()
	return frappe.db.get_value(
		"VC Turnover Checklist",
		doc.name,
		[
			"branch",
			"php_cash_source_type",
			"php_cash_source_document",
			"usd_cash_source_type",
			"usd_cash_source_document",
		],
		as_dict=True,
	) or frappe._dict()


def _should_clear_transfer_breakdown(previous, currency, branch):
	return previous.get("branch") != branch or previous.get(f"{currency}_cash_source_type") == "Vault Cash Position"


@frappe.whitelist()
def get_autofill_values(branch):
	if not branch:
		branch = get_branch_from_request_ip()

	if not branch:
		return {}

	require_active_branch_role(frappe.session.user, branch, "Vault Custodian")

	rows = get_turnover_rows(branch)
	gadget_counts = get_gadget_counts(branch)
	cash_values = get_vault_cash_autofill(branch, today())

	values = {
		"branch": branch,
		"endorsed_by": get_active_branch_role_user(branch, "Vault Custodian"),
		"sangla_envelopes_cb": sum(1 for row in rows if row.get("list_type") == "A-Jewelry"),
		"sangla_envelopes_ncb": sum(1 for row in rows if row.get("list_type") == "B-Jewelry"),
		"sangla_non_jewelry": sum(1 for row in rows if row.get("list_type") == "B-Non Jewelry"),
		"sanglang_benta": sum(1 for row in rows if row.get("list_type") == "Agreement to Sell"),
		"cellphone_count": gadget_counts.get("Cellphone", 0),
		"tablet_count": gadget_counts.get("Tablet", 0),
		"laptop_count": gadget_counts.get("Laptop", 0),
		"dslr_count": gadget_counts.get("Camera", 0),
		"gadget_under_installment": get_non_jewelry_item_count(branch, "Under Installment"),
		"branch_mobile_phones": get_non_jewelry_item_count(branch, "Company Used"),
	}
	values.update(cash_values)
	return values


def get_permission_query_conditions(user=None):
	user = user or frappe.session.user

	if _is_system_manager(user):
		return None

	escaped_user = frappe.db.escape(user)
	return (
		"(exists (select `tabBranch`.`name` "
		"from `tabBranch` "
		"where `tabBranch`.`name` = `tabVC Turnover Checklist`.`branch` "
		f"and `tabBranch`.`vault_custodian` = {escaped_user}) "
		f"or `tabVC Turnover Checklist`.`received_by` = {escaped_user} "
		f"or `tabVC Turnover Checklist`.`endorsed_by` = {escaped_user} "
		f"or `tabVC Turnover Checklist`.`owner` = {escaped_user})"
	)


def sync_acceptance_workflow_action(doc):
	"""Keep the pending workflow action assigned only to the named receiver."""
	if not doc.name:
		return

	filters = {
		"reference_doctype": "VC Turnover Checklist",
		"reference_name": doc.name,
	}
	frappe.db.delete("Workflow Action", filters)

	if cint(doc.docstatus) != 1 or doc.workflow_state != "For Acceptance" or not doc.received_by:
		return

	frappe.get_doc(
		{
			"doctype": "Workflow Action",
			"reference_doctype": "VC Turnover Checklist",
			"reference_name": doc.name,
			"workflow_state": doc.workflow_state,
			"status": "Open",
			"user": doc.received_by,
		}
	).insert(ignore_permissions=True)


def has_permission(doc, ptype=None, user=None):
	user = user or frappe.session.user
	permission_type = ptype or "read"

	if permission_type == "create":
		return (
			_is_system_manager(user)
			or (
				_user_has_doctype_permission(user, "VC Turnover Checklist", "create")
				and _is_current_branch_vault_custodian(doc, user)
			)
		)

	if permission_type == "submit":
		if doc.workflow_state in {"For Acceptance", "Accepted"} and user == doc.received_by:
			return True
		return (
			_is_system_manager(user)
			or (
				_user_has_doctype_permission(user, "VC Turnover Checklist", "submit")
				and _is_current_branch_vault_custodian(doc, user)
			)
		)

	if permission_type == "write":
		if _is_current_branch_vault_custodian(doc, user):
			if _is_submitting_document(doc):
				return _user_has_doctype_permission(user, "VC Turnover Checklist", "submit")

			if cint(doc.docstatus) == 0:
				return (
					_user_has_doctype_permission(user, "VC Turnover Checklist", "write")
					or _user_has_doctype_permission(user, "VC Turnover Checklist", "create")
				)

			if cint(doc.docstatus) == 1 and doc.workflow_state == "For Acceptance":
				return _user_has_doctype_permission(user, "VC Turnover Checklist", "submit")

		if doc.workflow_state in {"For Acceptance", "Accepted"}:
			return user == doc.received_by or _is_system_manager(user)
		return _is_system_manager(user)

	if permission_type in {"cancel", "delete"}:
		return _is_system_manager(user)

	if _is_system_manager(user):
		return True

	if permission_type == "read":
		return _is_current_branch_vault_custodian(doc, user) or user in {doc.received_by, doc.endorsed_by, doc.owner}

	return None


def _user_has_any_role(user, roles):
	return bool(set(frappe.get_roles(user)).intersection(roles))


def _is_system_manager(user):
	return user == "Administrator" or _user_has_any_role(user, {"System Manager"})


def _is_current_branch_vault_custodian(doc, user):
	branch = getattr(doc, "branch", None) or get_branch_from_request_ip()
	if not branch:
		return False

	return has_active_branch_role(user, branch, "Vault Custodian")


def _is_submitting_document(doc):
	return bool(getattr(doc.flags, "in_submit", False) or getattr(doc, "_action", None) == "submit")


def _user_has_doctype_permission(user, doctype, permission_type):
	if user == "Administrator":
		return True

	user_roles = set(frappe.get_roles(user))
	permission_doctype = "Custom DocPerm" if frappe.db.exists("Custom DocPerm", {"parent": doctype}) else "DocPerm"
	permissions = frappe.get_all(
		permission_doctype,
		fields=["role", permission_type],
		filters={
			"parent": doctype,
			"role": ["in", list(user_roles)],
			"permlevel": 0,
		},
	)

	return any(
		permission.role in user_roles and cint(permission.get(permission_type))
		for permission in permissions
	)
