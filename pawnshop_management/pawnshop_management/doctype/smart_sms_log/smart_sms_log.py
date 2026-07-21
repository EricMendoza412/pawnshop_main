import re

import frappe
from frappe.model.document import Document
from frappe.model.naming import make_autoname


class SMARTSMSLog(Document):
	def autoname(self):
		if self.sms_purpose == "Text Blast":
			self.name = make_autoname("TXTBLAST-SMS-.#####")
			return

		branch_code = get_branch_code(self.branch) if self.branch else "SMART"
		self.name = make_autoname("{0}-SMS-.#####".format(branch_code))


def get_reference_branch(reference_doctype, reference_name):
	if not reference_doctype or not reference_name:
		return None

	meta = frappe.get_meta(reference_doctype)
	if reference_doctype == "Text Blast" and meta.has_field("recipient_options"):
		return frappe.db.get_value(reference_doctype, reference_name, "recipient_options")

	if not meta.has_field("branch"):
		return None

	return frappe.db.get_value(reference_doctype, reference_name, "branch")


def get_branch_code(branch):
	if not branch:
		return "SMART"

	branch_code = None
	if frappe.get_meta("Branch").has_field("branch_code"):
		branch_code = frappe.db.get_value("Branch", branch, "branch_code")

	if not branch_code and " - " in branch:
		branch_code = branch.rsplit(" - ", 1)[-1]

	if not branch_code:
		branch_code = frappe.db.get_value("Branch IP Addressing", branch, "branch_code")

	branch_code = str(branch_code or branch or "SMART").strip().upper()
	branch_code = re.sub(r"[^A-Z0-9]+", "-", branch_code).strip("-")
	return branch_code or "SMART"
