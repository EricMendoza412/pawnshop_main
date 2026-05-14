# Copyright (c) 2026, Rabie Moses Santillan and contributors
# For license information, please see license.txt

import re

import frappe
from frappe.model.document import Document
from frappe.model.naming import make_autoname


BRANCH_CODES = {
	"Garcia's Pawnshop - CC": "1",
	"Garcia's Pawnshop - POB": "3",
	"Garcia's Pawnshop - GTC": "4",
	"Garcia's Pawnshop - TNZ": "5",
	"Garcia's Pawnshop - MOL": "6",
	"Garcia's Pawnshop - BUC": "7",
	"Garcia's Pawnshop - NOV": "8",
	"Garcia's Pawnshop - PSC": "9",
	"TEST": "20",
}


def get_branch_code(branch):
	if not branch:
		return None

	branch_code = frappe.db.get_value("Branch IP Addressing", branch, "branch_code")
	if branch_code:
		return str(branch_code)

	branch_code = frappe.db.get_value("Branch", branch, "branch_code")
	if branch_code:
		return str(branch_code)

	return BRANCH_CODES.get(branch)


def get_transaction_log_name_from_cpr(cash_position_report):
	if not cash_position_report:
		return None

	match = re.match(r"^No\.?-?(\d+)-(\d+)$", cash_position_report)
	if not match:
		return None

	branch_code, series_number = match.groups()
	return f"TL{branch_code}-{series_number}"


class TransactionLog(Document):
	def autoname(self):
		name_from_cpr = get_transaction_log_name_from_cpr(self.cash_position_report)
		if name_from_cpr and not frappe.db.exists("Transaction Log", name_from_cpr):
			self.name = name_from_cpr
			return

		branch_code = get_branch_code(self.branch)
		if branch_code:
			self.name = make_autoname(f"TL{branch_code}-.######")
			return

		self.name = make_autoname("TL-.######")
