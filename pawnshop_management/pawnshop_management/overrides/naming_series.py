# Copyright (c) 2026, Rabie Santillan and Eric Mendoza and contributors
# For license information, please see license.txt

import frappe
from erpnext.setup.doctype.naming_series.naming_series import NamingSeries

from pawnshop_management.pawnshop_management.doctype.fund_transfer.fund_transfer import (
	_safe_series_prefix,
	get_fund_transfer_branch_code,
)


class PawnshopNamingSeries(NamingSeries):
	"""Expose branch-specific cash-control counters in ERPNext Naming Series."""

	def get_options(self, arg=None):
		doctype = arg or self.select_doc_for_series
		if doctype in {"Fund Transfer", "Vault Cash Position"}:
			return "\n".join(_get_branch_series(doctype))
		return super().get_options(arg)


def _get_branch_series(doctype):
	series = set()
	for branch in frappe.get_all("Branch", pluck="name"):
		branch_code = get_fund_transfer_branch_code(branch)
		if not branch_code:
			continue
		if doctype == "Fund Transfer":
			series.add("{0}-.######".format(_safe_series_prefix(branch_code)))
		else:
			series.add("VCP{0}-.YYYY.-.#####".format(branch_code))
	return sorted(series)
