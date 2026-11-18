import math
import re

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime, getdate
from .selection import FILTER_TYPES, sms_metrics, registration_matches, fx_buying_trackers

from pawnshop_management.pawnshop_management.doctype.smart_sms_log.smart_sms_log import get_branch_code
from pawnshop_management.pawnshop_management.smart_a2p import (
	SmartA2PError,
	is_smart_a2p_configuration_error,
	log_failed_sms_attempt,
	send_sms,
	validate_smart_a2p_configuration,
)


TRACKER_BRANCH_RE_TEMPLATE = r"(?:^|-){0}\.[1-3]-"
DEFAULT_BATCH_SIZE = 250
DEFAULT_MAX_ATTEMPTS = 3
BATCH_JOB_TIMEOUT = 900
SUCCESSFUL_LOG_STATUSES = {"Queued", "Accepted", "Callback Received", "Delivered"}


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
				"pawnshop_management.pawnshop_management.doctype.text_blast.text_blast.initialize_text_blast_processing",
				queue="long",
				timeout=BATCH_JOB_TIMEOUT,
				enqueue_after_commit=True,
				text_blast_name=self.name,
			)

	def _set_message_length(self):
		self.message_length = _get_message_length_display(self.message, len(self.recipient_list or []))

	def _validate_recipient_source(self):
		if self.recipient_options and not frappe.db.exists("Branch", self.recipient_options):
			frappe.throw("Recipient Options must be an existing Branch.")

		if any(self.get(field) for field in ("recipient_filter", "from_date", "to_date")):
			_validate_selection(self.recipient_options, self.recipient_filter, self.from_date, self.to_date)

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
		# Database Date values are date objects; workflow requests carry ISO strings.
		# Compare calendar dates, and treat empty optional fields consistently.
		filters_changed = any(
			(previous.get(field) or "") != (self.get(field) or "")
			for field in ("recipient_options", "recipient_filter")
		) or any(
			(getdate(previous.get(field)) if previous.get(field) else None)
			!= (getdate(self.get(field)) if self.get(field) else None)
			for field in ("from_date", "to_date")
		)
		if previous.message != self.message or old_recipients != new_recipients or filters_changed:
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


def _get_message_length_display(message, recipient_count=0):
	metrics = sms_metrics(message)
	return "Encoding: {encoding} | Character count: {units}\n{segments} (SMS Segments) x {recipients} (Recipients) = {total} (Estimated total SMS Segments)".format(
		**metrics, recipients=recipient_count, total=metrics["segments"] * recipient_count)


@frappe.whitelist()
def get_recipient_options():
	return frappe.get_all("Branch", pluck="name", order_by="name asc")


@frappe.whitelist()
def get_branch_recipients(branch, recipient_filter=None, from_date=None, to_date=None):
	frappe.has_permission("Text Blast", "create", throw=True)
	start, end = _validate_selection(branch, recipient_filter, from_date, to_date)
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
	if recipient_filter == "Registered date range":
		customers = [c for c in customers if registration_matches(c.name, start, end)]
	else:
		matching = _transaction_customers(recipient_filter, start, end)
		customers = [c for c in customers if c.name in matching]
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
		mobile = str(contacts.get(contact) or "").strip()
		if not mobile or mobile in seen_mobiles:
			continue
		seen_mobiles.add(mobile)
		recipients.append({"contact_name": contact, "mobile_number": mobile})
	return recipients


def _validate_selection(branch, recipient_filter, from_date, to_date):
	if not branch or recipient_filter not in FILTER_TYPES or not from_date or not to_date:
		frappe.throw("Select a Branch, recipient filter, From Date and To Date before loading customers.")
	start, end = getdate(from_date), getdate(to_date)
	if start > end:
		frappe.throw("From Date must be on or before To Date.")
	return start, end


def _transaction_customers(recipient_filter, start, end):
	if recipient_filter == "FX buying date range":
		return _fx_buying_customers(start, end)
	sources = {
		"Subastado sales date range": [("Subastado Sales Commissions", "customer_tracker", "date_bought_or_returned", {})],
		"Agreement to sell date range": [("Agreement to Sell", "customer_tracker", "date_of_sale", {"workflow_state": ["in", ["Active", "Pulled Out"]]})],
		"Pawn ticket date range": [(doctype, "customers_tracking_no", "date_loan_granted", {"workflow_state": ["not in", ["Rejected", "Draft"]]}) for doctype in ("Pawn Ticket Jewelry", "Pawn Ticket Non Jewelry")],
		"FX selling date range": [("FX Selling", "customer", "business_date", {"docstatus": 1})],
	}
	customers = set()
	for doctype, customer_field, date_field, filters in sources[recipient_filter]:
		filters[date_field] = ["between", [start, end]]
		customers.update(frappe.get_all(doctype, filters=filters, pluck=customer_field))
	return customers


def _fx_buying_customers(start, end):
	from pawnshop_management.pawnshop_management.doctype.fx_selling.fx_selling import _sheet_service, _quote_sheet

	spreadsheet_id = "1Id-1_SYEb8ZY_-rYQqown_9msjKD15RUrCszbVJzjc8"
	try:
		service = _sheet_service(frappe.get_single("FX Selling Settings"))
		sheets = service.spreadsheets()
		metadata = sheets.get(spreadsheetId=spreadsheet_id, fields="sheets.properties").execute()
		tabs = [s["properties"] for s in metadata.get("sheets", [])
			if re.fullmatch(r"Transaction Monitoring(?: \d{4}(?: \([12]/2\))?)?", s["properties"]["title"])]
		if not tabs:
			raise ValueError("No Transaction Monitoring tabs found")
		customers = set()
		for tab in tabs:
			year = re.search(r"\b(\d{4})\b", tab["title"])
			if year and not start.year <= int(year.group(1)) <= end.year:
				continue
			quoted = _quote_sheet(tab["title"])
			header = sheets.values().get(spreadsheetId=spreadsheet_id, range=quoted + "!A1:N1").execute().get("values", [[]])[0]
			if len(header) < 14 or "date" not in header[1].lower() or "customer" not in header[3].lower() or "void" not in header[13].lower():
				raise ValueError("Unexpected Transaction Monitoring columns")
			for first in range(2, tab["gridProperties"]["rowCount"] + 1, 2000):
				last = min(first + 1999, tab["gridProperties"]["rowCount"])
				rows = sheets.values().get(spreadsheetId=spreadsheet_id,
					range="{0}!A{1}:N{2}".format(quoted, first, last), valueRenderOption="UNFORMATTED_VALUE").execute().get("values", [])
				customers.update(fx_buying_trackers(rows, start, end))
		return customers
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Text Blast FX Buying Read Failed")
		frappe.throw("Unable to read FX Buying transactions. Check spreadsheet access and column layout, then retry. No recipients have been loaded.")


@frappe.whitelist()
def retry_text_blast(text_blast_name):
	doc = frappe.get_doc("Text Blast", text_blast_name)
	doc.check_permission("read")
	if doc.workflow_state != "Sent" or not doc.approved_by:
		frappe.throw("Only an approved Text Blast can be retried.")
	if not is_authorized_text_blast_approver(frappe.session.user):
		frappe.throw("Only an authorized Text Blast approver can retry failed SMS messages.", frappe.PermissionError)
	if doc.processing_status in ("Queued", "Processing"):
		frappe.throw("Text Blast processing is already active.")
	retry_status = get_text_blast_retry_status(doc)
	eligible = retry_status["failed"] + retry_status["unsent"]
	if not eligible:
		return {"queued": False, "eligible": 0, **retry_status}

	if not frappe.db.exists("Text Blast Batch", {"text_blast": doc.name}):
		batch_size = doc.batch_size or DEFAULT_BATCH_SIZE
		_create_batches(doc.name, len(doc.recipient_list), batch_size)
	_reset_retryable_batches(doc)
	frappe.db.set_value(
		"Text Blast",
		doc.name,
		{
			"processing_status": "Queued",
			"processing_completed_at": None,
			"last_processing_error": None,
			"retry_count": (doc.retry_count or 0) + 1,
		},
		update_modified=False,
	)
	frappe.db.commit()
	enqueue_next_text_blast_batch(doc.name)
	return {"queued": True, "eligible": eligible, **retry_status}


def get_text_blast_retry_status(doc):
	if isinstance(doc, str):
		doc = frappe.get_doc("Text Blast", doc)

	logs_by_row = _get_logs_by_recipient(doc.name)
	status = {"successful": 0, "failed": 0, "exhausted": 0, "unsent": 0}
	max_attempts = doc.max_attempts or DEFAULT_MAX_ATTEMPTS
	for row in doc.recipient_list:
		row_logs = logs_by_row.get(row.idx, [])
		if _has_successful_attempt(row_logs):
			status["successful"] += 1
		elif row_logs and len(row_logs) < max_attempts:
			status["failed"] += 1
		elif row_logs:
			status["exhausted"] += 1
		else:
			status["unsent"] += 1
	return status


def initialize_text_blast_processing(text_blast_name):
	doc = frappe.get_doc("Text Blast", text_blast_name)
	if doc.workflow_state != "Sent" or not doc.approved_by:
		raise SmartA2PError("Only an approved Text Blast can send SMS messages.")

	batch_size = doc.batch_size or DEFAULT_BATCH_SIZE
	total_recipients = frappe.db.count("Recipient List", {"parent": doc.name, "parenttype": "Text Blast"})
	if not total_recipients:
		_set_campaign_failure(doc.name, "Text Blast has no recipients.")
		return

	_create_batches(doc.name, total_recipients, batch_size)
	frappe.db.set_value(
		"Text Blast",
		doc.name,
		{
			"processing_status": "Queued",
			"batch_size": batch_size,
			"max_attempts": doc.max_attempts or DEFAULT_MAX_ATTEMPTS,
			"total_recipients": total_recipients,
			"total_batches": int(math.ceil(total_recipients / float(batch_size))),
			"completed_batches": 0,
			"accepted_recipients": 0,
			"failed_recipients": 0,
			"skipped_recipients": 0,
			"unsent_recipients": total_recipients,
			"processing_progress": 0,
			"processing_started_at": now_datetime(),
			"processing_completed_at": None,
			"last_processing_error": None,
		},
		update_modified=False,
	)
	frappe.db.commit()

	try:
		validate_smart_a2p_configuration()
	except Exception as exc:
		_pause_campaign(doc.name, None, exc)
		return

	enqueue_next_text_blast_batch(doc.name)


def _create_batches(text_blast_name, total_recipients, batch_size):
	if frappe.db.exists("Text Blast Batch", {"text_blast": text_blast_name}):
		return

	for batch_number, start_index, end_index in _get_batch_ranges(total_recipients, batch_size):
		frappe.get_doc(
			{
				"doctype": "Text Blast Batch",
				"batch_key": "{0}-BATCH-{1:04d}".format(text_blast_name, batch_number),
				"text_blast": text_blast_name,
				"batch_number": batch_number,
				"status": "Pending",
				"start_index": start_index,
				"end_index": end_index,
				"recipient_count": end_index - start_index + 1,
			}
		).insert(ignore_permissions=True)


def _get_batch_ranges(total_recipients, batch_size):
	total_batches = int(math.ceil(total_recipients / float(batch_size)))
	return [
		(
			batch_number,
			((batch_number - 1) * batch_size) + 1,
			min(batch_number * batch_size, total_recipients),
		)
		for batch_number in range(1, total_batches + 1)
	]


def enqueue_next_text_blast_batch(text_blast_name):
	batch_name = frappe.db.get_value(
		"Text Blast Batch",
		{"text_blast": text_blast_name, "status": "Pending"},
		"name",
		order_by="batch_number asc",
	)
	if not batch_name:
		_update_campaign_progress(text_blast_name, finalize=True)
		return

	frappe.db.set_value(
		"Text Blast Batch",
		batch_name,
		{"status": "Queued", "queued_at": now_datetime()},
		update_modified=False,
	)
	frappe.db.set_value("Text Blast", text_blast_name, "processing_status", "Processing", update_modified=False)
	frappe.db.commit()
	frappe.enqueue(
		"pawnshop_management.pawnshop_management.doctype.text_blast.text_blast.process_text_blast_batch",
		queue="long",
		timeout=BATCH_JOB_TIMEOUT,
		job_name="text-blast:{0}:batch:{1}".format(text_blast_name, batch_name),
		batch_name=batch_name,
	)


def process_text_blast_batch(batch_name):
	try:
		return _process_text_blast_batch(batch_name)
	except Exception as exc:
		batch = frappe.get_doc("Text Blast Batch", batch_name)
		_set_campaign_failure(batch.text_blast, exc, batch.name)
		frappe.log_error(frappe.get_traceback(), "Text Blast batch failed: {0}".format(batch.name))
		raise


def _process_text_blast_batch(batch_name):
	batch = frappe.get_doc("Text Blast Batch", batch_name)
	if batch.status in ("Completed", "Partially Failed"):
		return

	doc = frappe.get_doc("Text Blast", batch.text_blast)
	if doc.workflow_state != "Sent" or not doc.approved_by:
		_set_campaign_failure(doc.name, "Only an approved Text Blast can send SMS messages.", batch.name)
		return

	try:
		validate_smart_a2p_configuration()
	except Exception as exc:
		_pause_campaign(doc.name, batch.name, exc)
		return

	frappe.db.set_value(
		"Text Blast Batch",
		batch.name,
		{
			"status": "Processing",
			"started_at": now_datetime(),
			"attempt_count": (batch.attempt_count or 0) + 1,
			"last_error": None,
		},
		update_modified=False,
	)
	frappe.db.commit()

	rows = frappe.get_all(
		"Recipient List",
		filters=[
			["parent", "=", doc.name],
			["parenttype", "=", "Text Blast"],
			["idx", ">=", batch.start_index],
			["idx", "<=", batch.end_index],
		],
		fields=["idx", "contact_name", "mobile_number"],
		order_by="idx asc",
	)
	logs_by_row = _get_logs_by_recipient(doc.name)
	results = {"accepted": 0, "failed": 0, "skipped": 0}
	max_attempts = doc.max_attempts or DEFAULT_MAX_ATTEMPTS

	for row in rows:
		row_logs = logs_by_row.get(row.idx, [])
		if _has_successful_attempt(row_logs) or len(row_logs) >= max_attempts:
			results["skipped"] += 1
			continue

		client_message_id = _get_next_client_message_id(doc.name, row.idx, len(row_logs) + 1)
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
			if is_smart_a2p_configuration_error(exc):
				_pause_campaign(doc.name, batch.name, exc)
				return
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

	batch_status = "Partially Failed" if results["failed"] else "Completed"
	frappe.db.set_value(
		"Text Blast Batch",
		batch.name,
		{
			"status": batch_status,
			"accepted_count": results["accepted"],
			"failed_count": results["failed"],
			"skipped_count": results["skipped"],
			"completed_at": now_datetime(),
		},
		update_modified=False,
	)
	frappe.db.commit()
	_update_campaign_progress(doc.name)
	enqueue_next_text_blast_batch(doc.name)


def _get_logs_by_recipient(text_blast_name):
	logs = frappe.get_all(
		"SMART SMS Log",
		filters={"reference_doctype": "Text Blast", "reference_name": text_blast_name},
		fields=["client_message_id", "status"],
		order_by="creation asc",
	)
	pattern = re.compile(r"^TEXT-BLAST-{0}-(\d+)(?:-R\d+)?$".format(re.escape(text_blast_name)))
	by_row = {}
	for log in logs:
		match = pattern.match(log.client_message_id or "")
		if match:
			by_row.setdefault(int(match.group(1)), []).append(log)
	return by_row


def _has_successful_attempt(logs):
	return any(log.status in SUCCESSFUL_LOG_STATUSES for log in logs)


def _get_next_client_message_id(text_blast_name, row_index, attempt_number):
	base = "TEXT-BLAST-{0}-{1}".format(text_blast_name, row_index)
	return base[:128] if attempt_number == 1 else "{0}-R{1}".format(base, attempt_number)[:128]


def _reset_retryable_batches(doc):
	logs_by_row = _get_logs_by_recipient(doc.name)
	max_attempts = doc.max_attempts or DEFAULT_MAX_ATTEMPTS
	batch_size = doc.batch_size or DEFAULT_BATCH_SIZE
	batch_numbers = set()
	for row in doc.recipient_list:
		row_logs = logs_by_row.get(row.idx, [])
		if not _has_successful_attempt(row_logs) and len(row_logs) < max_attempts:
			batch_numbers.add(int(math.ceil(row.idx / float(batch_size))))
	for batch_number in batch_numbers:
		frappe.db.set_value(
			"Text Blast Batch",
			{"text_blast": doc.name, "batch_number": batch_number},
			{
				"status": "Pending",
				"accepted_count": 0,
				"failed_count": 0,
				"skipped_count": 0,
				"completed_at": None,
				"last_error": None,
			},
			update_modified=False,
		)


def _update_campaign_progress(text_blast_name, finalize=False):
	doc = frappe.get_doc("Text Blast", text_blast_name)
	logs_by_row = _get_logs_by_recipient(doc.name)
	max_attempts = doc.max_attempts or DEFAULT_MAX_ATTEMPTS
	accepted = failed = unsent = 0
	for row in doc.recipient_list:
		row_logs = logs_by_row.get(row.idx, [])
		if _has_successful_attempt(row_logs):
			accepted += 1
		elif row_logs:
			failed += 1
		else:
			unsent += 1

	total = len(doc.recipient_list)
	completed_batches = frappe.db.count(
		"Text Blast Batch",
		{"text_blast": doc.name, "status": ("in", ["Completed", "Partially Failed", "Failed"])},
	)
	total_batches = frappe.db.count("Text Blast Batch", {"text_blast": doc.name})
	skipped = sum(
		row.skipped_count or 0
		for row in frappe.get_all(
			"Text Blast Batch", filters={"text_blast": doc.name}, fields=["skipped_count"]
		)
	)
	values = {
		"total_recipients": total,
		"total_batches": total_batches,
		"completed_batches": completed_batches,
		"accepted_recipients": accepted,
		"failed_recipients": failed,
		"skipped_recipients": skipped,
		"unsent_recipients": unsent,
		"processing_progress": ((accepted + failed) * 100.0 / total) if total else 0,
	}
	if finalize or (total_batches and completed_batches == total_batches):
		values["processing_status"] = "Completed" if not failed and not unsent else "Partially Failed"
		values["processing_completed_at"] = now_datetime()
	frappe.db.set_value("Text Blast", doc.name, values, update_modified=False)
	frappe.db.commit()


def _pause_campaign(text_blast_name, batch_name, exc):
	error = str(exc)
	frappe.db.set_value(
		"Text Blast",
		text_blast_name,
		{"processing_status": "Paused", "last_processing_error": error},
		update_modified=False,
	)
	if batch_name:
		frappe.db.set_value(
			"Text Blast Batch",
			batch_name,
			{"status": "Paused", "last_error": error},
			update_modified=False,
		)
	frappe.log_error(frappe.get_traceback(), "Text Blast paused: {0}".format(text_blast_name))
	frappe.db.commit()


def _set_campaign_failure(text_blast_name, error, batch_name=None):
	frappe.db.set_value(
		"Text Blast",
		text_blast_name,
		{
			"processing_status": "Failed",
			"last_processing_error": str(error),
			"processing_completed_at": now_datetime(),
		},
		update_modified=False,
	)
	if batch_name:
		frappe.db.set_value(
			"Text Blast Batch",
			batch_name,
			{"status": "Failed", "last_error": str(error), "completed_at": now_datetime()},
			update_modified=False,
		)
	frappe.db.commit()
