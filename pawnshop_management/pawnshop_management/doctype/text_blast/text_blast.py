import math
import re

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime

from pawnshop_management.pawnshop_management.doctype.smart_sms_log.smart_sms_log import get_branch_code
from pawnshop_management.pawnshop_management.smart_a2p import (
	SmartA2PError,
	log_failed_sms_attempt,
	send_sms,
)


TRACKER_BRANCH_RE_TEMPLATE = r"(?:^|-){0}\.[1-3]-"


class TextBlast(Document):
	def validate(self):
		self._set_message_length()
		self._validate_recipient_source()
		self._validate_recipients()
		self._set_approval_audit_fields()
		self._prevent_approved_content_changes()

	def on_update(self):
		previous = self.get_doc_before_save()
		if self.workflow_state == "Sent" and previous and previous.workflow_state != "Sent":
			frappe.enqueue(
				"pawnshop_management.pawnshop_management.doctype.text_blast.text_blast.send_text_blast",
				queue="long",
				enqueue_after_commit=True,
				text_blast_name=self.name,
			)

	def _set_message_length(self):
		characters = len(self.message or "")
		segments = max(1, int(math.ceil(characters / 160.0)))
		self.message_length = "Characters: {0} / {1}\nSMS Segments: {2}".format(
			characters, segments * 160, segments
		)

	def _validate_recipient_source(self):
		if self.recipient_options and not frappe.db.exists("Branch", self.recipient_options):
			frappe.throw("Recipient Options must be an existing Branch.")

	def _validate_recipients(self):
		if not self.recipient_list:
			frappe.throw("Recipient List must contain at least one recipient.")

		seen = set()
		for row in self.recipient_list:
			if not row.contact_name or not frappe.db.exists("Contact", row.contact_name):
				frappe.throw("A valid Contact is required on recipient row {0}.".format(row.idx))

			mobile = str(frappe.db.get_value("Contact", row.contact_name, "mobile_no") or "").strip()
			if not mobile:
				frappe.throw("Contact {0} has no mobile number.".format(row.contact_name))
			row.mobile_number = mobile
			if mobile in seen:
				frappe.throw("Duplicate Mobile Number {0} in Recipient List.".format(mobile))
			seen.add(mobile)

	def _set_approval_audit_fields(self):
		previous = self.get_doc_before_save()
		previous_state = previous.workflow_state if previous else None

		if self.workflow_state == "For Approval" and previous_state != "For Approval":
			self.requested_by = frappe.session.user
			self.date_created = now_datetime()

		if self.workflow_state == "Sent" and previous_state != "Sent":
			if previous_state != "For Approval":
				frappe.throw("Text Blast must be For Approval before it can be sent.")
			if not is_authorized_text_blast_approver(frappe.session.user):
				frappe.throw(
					"Only Administrator or a user whose Role Profile includes Operations Manager can approve a Text Blast.",
					frappe.PermissionError,
				)
			if previous.requested_by == frappe.session.user and frappe.session.user != "Administrator":
				frappe.throw("The requester cannot approve their own Text Blast.")
			self.approved_by = frappe.session.user

	def _prevent_approved_content_changes(self):
		previous = self.get_doc_before_save()
		if not previous or previous.workflow_state not in ("For Approval", "Sent"):
			return

		old_recipients = [(row.contact_name, row.mobile_number) for row in previous.recipient_list]
		new_recipients = [(row.contact_name, row.mobile_number) for row in self.recipient_list]
		if previous.message != self.message or previous.recipient_options != self.recipient_options or old_recipients != new_recipients:
			frappe.throw("Message and recipients cannot be changed after submission for approval.")


def is_authorized_text_blast_approver(user):
	if user == "Administrator":
		return True

	role_profile = frappe.db.get_value("User", user, "role_profile_name")
	if not role_profile:
		return False

	return bool(
		frappe.db.exists(
			"Has Role",
			{
				"parenttype": "Role Profile",
				"parent": role_profile,
				"role": "Operations Manager",
			},
		)
	)


@frappe.whitelist()
def get_recipient_options():
	return frappe.get_all("Branch", pluck="name", order_by="name asc")


@frappe.whitelist()
def get_branch_recipients(branch):
	if not frappe.db.exists("Branch", branch):
		frappe.throw("Branch {0} was not found.".format(branch))

	branch_code = frappe.db.get_value("Branch IP Addressing", branch, "branch_code") or get_branch_code(branch)
	plain_branch_code = str(branch_code)
	branch_code = re.escape(plain_branch_code)
	tracker_pattern = re.compile(TRACKER_BRANCH_RE_TEMPLATE.format(branch_code), re.IGNORECASE)
	customers = frappe.get_all(
		"Customer",
		fields=["name", "customer_name", "customer_primary_contact"],
		or_filters=[
			["name", "like", "{0}.%".format(plain_branch_code)],
			["name", "like", "%-{0}.%".format(plain_branch_code)],
		],
	)
	customers = [customer for customer in customers if tracker_pattern.search(customer.name or "")]
	if not customers:
		return []

	customer_names = [customer.name for customer in customers]
	dynamic_links = frappe.get_all(
		"Dynamic Link",
		filters={"link_doctype": "Customer", "link_name": ("in", customer_names), "parenttype": "Contact"},
		fields=["link_name", "parent"],
	)
	linked_contacts = {row.link_name: row.parent for row in dynamic_links}
	contact_names = {
		customer.customer_primary_contact or linked_contacts.get(customer.name)
		for customer in customers
	}
	contact_names.discard(None)
	contacts = {
		row.name: row.mobile_no
		for row in frappe.get_all(
			"Contact", filters={"name": ("in", list(contact_names))}, fields=["name", "mobile_no"]
		)
	}

	recipients = []
	seen_mobiles = set()
	for customer in customers:
		contact = customer.customer_primary_contact or linked_contacts.get(customer.name)
		mobile = contacts.get(contact)
		if not mobile or mobile in seen_mobiles:
			continue
		seen_mobiles.add(mobile)
		recipients.append({"contact_name": contact, "mobile_number": mobile})
	return recipients


@frappe.whitelist()
def retry_text_blast(text_blast_name):
	doc = frappe.get_doc("Text Blast", text_blast_name)
	doc.check_permission("read")
	if doc.workflow_state != "Sent" or not doc.approved_by:
		frappe.throw("Only an approved Text Blast can be retried.")
	if not is_authorized_text_blast_approver(frappe.session.user):
		frappe.throw("Only an authorized Text Blast approver can retry failed SMS messages.", frappe.PermissionError)
	retry_status = get_text_blast_retry_status(doc)
	eligible = retry_status["failed"] + retry_status["unsent"]
	if not eligible:
		return {"queued": False, "eligible": 0, **retry_status}

	frappe.enqueue(
		"pawnshop_management.pawnshop_management.doctype.text_blast.text_blast.send_text_blast",
		queue="long",
		timeout=3600,
		text_blast_name=doc.name,
	)
	return {"queued": True, "eligible": eligible, **retry_status}


def get_text_blast_retry_status(doc):
	if isinstance(doc, str):
		doc = frappe.get_doc("Text Blast", doc)

	logs = frappe.get_all(
		"SMART SMS Log",
		filters={"reference_doctype": "Text Blast", "reference_name": doc.name},
		fields=["client_message_id", "status"],
	)
	status = {"successful": 0, "failed": 0, "unsent": 0}
	for row in doc.recipient_list:
		prefix = "TEXT-BLAST-{0}-{1}".format(doc.name, row.idx)
		row_statuses = [
			log.status
			for log in logs
			if log.client_message_id == prefix or (log.client_message_id or "").startswith(prefix + "-R")
		]
		if any(log_status != "Failed" for log_status in row_statuses):
			status["successful"] += 1
		elif row_statuses:
			status["failed"] += 1
		else:
			status["unsent"] += 1
	return status


def send_text_blast(text_blast_name):
	doc = frappe.get_doc("Text Blast", text_blast_name)
	if doc.workflow_state != "Sent" or not doc.approved_by:
		raise SmartA2PError("Only an approved Text Blast can send SMS messages.")

	results = {"accepted": 0, "failed": 0, "skipped": 0}
	for row in doc.recipient_list:
		base_client_message_id = "TEXT-BLAST-{0}-{1}".format(doc.name, row.idx)[:128]
		client_message_id = base_client_message_id
		existing_status = frappe.db.get_value(
			"SMART SMS Log", {"client_message_id": client_message_id}, "status"
		)
		if existing_status and existing_status != "Failed":
			results["skipped"] += 1
			continue
		if existing_status == "Failed":
			retry_number = 2
			while frappe.db.exists(
				"SMART SMS Log", {"client_message_id": "{0}-R{1}".format(base_client_message_id, retry_number)[:128]}
			):
				retry_number += 1
			client_message_id = "{0}-R{1}".format(base_client_message_id, retry_number)[:128]

		try:
			send_sms(
				destination=row.mobile_number,
				text=doc.message,
				client_message_id=client_message_id,
				reference_doctype="Text Blast",
				reference_name=doc.name,
				sms_purpose="Text Blast",
			)
			results["accepted"] += 1
		except Exception as exc:
			results["failed"] += 1
			if not frappe.db.exists("SMART SMS Log", {"client_message_id": client_message_id}):
				log_failed_sms_attempt(
					destination=row.mobile_number,
					text=doc.message,
					client_message_id=client_message_id,
					error_message=exc,
					reference_doctype="Text Blast",
					reference_name=doc.name,
					sms_purpose="Text Blast",
				)
			frappe.log_error(frappe.get_traceback(), "Text Blast SMS failed: {0} row {1}".format(doc.name, row.idx))
		frappe.db.commit()
	return results
