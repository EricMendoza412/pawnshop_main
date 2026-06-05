import frappe
from frappe import _


BRANCH_CODES = {
	"Garcia's Pawnshop - CC": "CC",
	"Garcia's Pawnshop - POB": "POB",
	"Garcia's Pawnshop - MOL": "MOL",
	"Garcia's Pawnshop - GTC": "GTC",
	"Garcia's Pawnshop - TNZ": "TNZ",
	"Garcia's Pawnshop - BUC": "BUC",
	"Garcia's Pawnshop - NOV": "NOV",
	"Garcia's Pawnshop - PSC": "PSC",
	"TEST": "TEST",
}


def execute(filters=None):
	filters = frappe._dict(filters or {})
	branch = normalize_branch(filters.get("branch")) or get_branch_from_ip()
	report_date = filters.get("date")

	inventory_count = get_inventory_count(branch, report_date)
	columns = get_columns()
	data = get_data(inventory_count, branch)
	return columns, data


def normalize_branch(branch):
	if isinstance(branch, (list, tuple)):
		return branch[0] if branch else None

	if isinstance(branch, str):
		return branch.strip() or None

	return branch


def get_branch_from_ip():
	current_ip = getattr(frappe.local, "request_ip", None)
	if not current_ip:
		return None

	return frappe.db.get_value("Branch IP Addressing", {"ip_address": current_ip}, "name")


@frappe.whitelist()
def get_default_branch():
	return get_branch_from_ip()


def get_inventory_count(branch, report_date):
	filters = {}
	if branch:
		filters["branch"] = branch
	if report_date:
		filters["date"] = report_date

	fields = [
		"date", "branch",
		"in_count_a", "principal_in_a", "out_count_a", "principal_out_a",
		"returned_a", "principal_ret_a", "pulled_out_a", "principal_po_a",
		"total_a", "principal_totala",
		"in_count_b", "principal_in_b", "out_count_b", "principal_out_b",
		"returned_b", "principal_ret_b", "pulled_out_b", "principal_po_b",
		"total_b", "principal_totalb",
		"in_count_nj", "principal_in_nj", "out_count_nj", "principal_out_nj",
		"returned_nj", "principal_ret_nj", "pulled_out_nj", "principal_po_nj",
		"total_nj", "principal_totalnj",
		"in_count_sb", "principal_in_sb", "pulled_out_sb", "principal_po_sb",
		"total_sb", "principal_totalsb",
	]

	return frappe.db.get_value(
		"Inventory Count",
		filters,
		fields,
		as_dict=True,
		order_by="date desc",
	) or frappe._dict({"branch": branch, "date": report_date})


def get_data(doc, branch):
	branch = doc.get("branch") or branch
	branch_code = BRANCH_CODES.get(branch, branch or "")

	return [
		get_series_row(doc, branch_code, "JEWELRY - A", "a"),
		get_series_row(doc, branch_code, "JEWELRY - B", "b"),
		get_series_row(doc, branch_code, "NON JEWELRY", "nj"),
		get_sb_row(doc, branch_code),
	]


def get_series_row(doc, branch_code, section, suffix):
	total_field = "principal_total" + suffix
	if suffix == "a":
		total_field = "principal_totala"
	elif suffix == "b":
		total_field = "principal_totalb"
	elif suffix == "nj":
		total_field = "principal_totalnj"

	return frappe._dict({
		"branch_code": branch_code,
		"section": section,
		"date": doc.get("date"),
		"in_count": doc.get("in_count_" + suffix) or 0,
		"principal_in": doc.get("principal_in_" + suffix) or 0,
		"out_count": doc.get("out_count_" + suffix) or 0,
		"principal_out": doc.get("principal_out_" + suffix) or 0,
		"returned": doc.get("returned_" + suffix) or 0,
		"principal_ret": doc.get("principal_ret_" + suffix) or 0,
		"pulled_out": doc.get("pulled_out_" + suffix) or 0,
		"principal_po": doc.get("principal_po_" + suffix) or 0,
		"total": doc.get("total_" + suffix) or 0,
		"principal_total": doc.get(total_field) or 0,
	})


def get_sb_row(doc, branch_code):
	return frappe._dict({
		"branch_code": branch_code,
		"section": "SANGLANG BENTA",
		"date": doc.get("date"),
		"in_count": doc.get("in_count_sb") or 0,
		"principal_in": doc.get("principal_in_sb") or 0,
		"out_count": None,
		"principal_out": None,
		"returned": None,
		"principal_ret": None,
		"pulled_out": doc.get("pulled_out_sb") or 0,
		"principal_po": doc.get("principal_po_sb") or 0,
		"total": doc.get("total_sb") or 0,
		"principal_total": doc.get("principal_totalsb") or 0,
	})


def get_columns():
	return [
		{"fieldname": "section", "label": _("Section"), "fieldtype": "Data", "width": 130},
		{"fieldname": "date", "label": _("Date"), "fieldtype": "Date", "width": 110},
		{"fieldname": "in_count", "label": _("IN"), "fieldtype": "Int", "width": 80},
		{"fieldname": "principal_in", "label": _("Principal"), "fieldtype": "Currency", "width": 130},
		{"fieldname": "out_count", "label": _("OUT"), "fieldtype": "Int", "width": 80},
		{"fieldname": "principal_out", "label": _("Principal"), "fieldtype": "Currency", "width": 130},
		{"fieldname": "returned", "label": _("Returned"), "fieldtype": "Int", "width": 90},
		{"fieldname": "principal_ret", "label": _("Principal"), "fieldtype": "Currency", "width": 130},
		{"fieldname": "pulled_out", "label": _("Pulled Out"), "fieldtype": "Int", "width": 90},
		{"fieldname": "principal_po", "label": _("Principal"), "fieldtype": "Currency", "width": 130},
		{"fieldname": "total", "label": _("Total"), "fieldtype": "Int", "width": 80},
		{"fieldname": "principal_total", "label": _("Principal"), "fieldtype": "Currency", "width": 140},
	]
