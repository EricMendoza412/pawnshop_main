import json
import re
from urllib.parse import urljoin

import frappe
import requests
from frappe.utils import formatdate, now_datetime, today

from pawnshop_management.operations_access_control.vault_custodian import require_vault_custodian_access
from pawnshop_management.pawnshop_management.doctype.smart_sms_log.smart_sms_log import get_reference_branch


DEFAULT_BASE_URL = "https://enterprise.messagingsuite.smart.com.ph/cgpapi/"
SMS_MESSAGE_TYPE = "sms"
E164_RE = re.compile(r"^\d{1,15}$")
TEST_DESTINATION = "639178400153"
TEST_MESSAGE = "Hello There"
DAILY_0900_TEST_CLIENT_MESSAGE_ID_PREFIX = "SMART-A2P-DAILY-TEST-0900"
DAILY_TEXT_BLAST_STATUS_MESSAGE_TEMPLATE = "ERPNEXT text blast - total SMS requests: {0}"
DELIVERED_PROVIDER_STATUSES = {"DELIVERED", "DELIVRD"}
PAWN_TICKET_DOCTYPES = {"Pawn Ticket Jewelry", "Pawn Ticket Non Jewelry"}
PAWN_TICKET_SMS_WORKFLOW_STATES = {"Active", "Expired"}


class SmartA2PError(frappe.ValidationError):
	pass


def _get_settings():
	settings = frappe.get_single("SMART A2P Settings")
	if not settings.enabled:
		frappe.throw("SMART A2P SMS sending is disabled.", SmartA2PError)

	if not settings.api_id:
		frappe.throw("SMART A2P API ID is required.", SmartA2PError)

	api_key = settings.get_password("api_key")
	if not api_key:
		frappe.throw("SMART A2P API Key is required.", SmartA2PError)

	return settings, api_key


def _get_base_url(settings):
	base_url = (settings.base_url or DEFAULT_BASE_URL).strip()
	if not base_url.endswith("/"):
		base_url += "/"
	return base_url


def _headers(settings, api_key):
	return {
		"X-MEMS-API-ID": settings.api_id,
		"X-MEMS-API-KEY": api_key,
		"Content-Type": "application/json;charset=UTF-8",
		"Accept": "application/json",
	}


def _normalize_destination(destination):
	destination = re.sub(r"[\s()+-]", "", str(destination or ""))
	if destination.startswith("00"):
		destination = destination[2:]

	if not E164_RE.match(destination):
		frappe.throw(
			"Destination must be an international MSISDN with digits only, max 15 digits.",
			SmartA2PError,
		)

	return destination


def _build_payload(
	destination,
	text=None,
	template_name=None,
	client_message_id=None,
	source=None,
	cost_centre=None,
	reply_to=None,
	registered=None,
	key_values=None,
	extra=None,
):
	if not text and not template_name:
		frappe.throw("Either text or template_name is required.", SmartA2PError)

	payload = {
		"messageType": SMS_MESSAGE_TYPE,
		"destination": _normalize_destination(destination),
	}

	if text:
		if len(text) > 1400:
			frappe.throw("SMART SMS text must not exceed 1400 characters.", SmartA2PError)
		payload["text"] = text

	if template_name:
		payload["templateName"] = template_name

	if client_message_id:
		payload["clientMessageId"] = str(client_message_id)[:128]

	if source:
		payload["source"] = str(source)[:50]

	if cost_centre:
		payload["costCentre"] = str(cost_centre)[:100]

	if key_values:
		payload["keyValues"] = str(key_values)[:2000]

	if registered is not None:
		payload["registered"] = int(registered)

	if reply_to:
		payload["replyToTON"] = 10
		payload["replyTo"] = reply_to

	if extra:
		payload.update(extra)

	return payload


def _new_log(payload, reference_doctype=None, reference_name=None, sms_purpose=None):
	log = frappe.new_doc("SMART SMS Log")
	log.destination = payload.get("destination")
	log.message_type = SMS_MESSAGE_TYPE
	log.source = payload.get("source")
	log.client_message_id = payload.get("clientMessageId")
	log.reference_doctype = reference_doctype
	log.reference_name = reference_name
	log.branch = get_reference_branch(reference_doctype, reference_name)
	log.sms_purpose = sms_purpose
	log.text = payload.get("text")
	log.template_name = payload.get("templateName")
	log.request_payload = json.dumps(payload, indent=2, sort_keys=True)
	log.status = "Queued"
	log.insert(ignore_permissions=True)
	return log


def _response_body(response):
	try:
		return json.dumps(response.json(), indent=2, sort_keys=True)
	except ValueError:
		return response.text


def _message_id_from_location(location):
	if not location:
		return None
	return location.rstrip("/").split("/")[-1]


@frappe.whitelist()
def send_sms(
	destination,
	text=None,
	template_name=None,
	client_message_id=None,
	source=None,
	cost_centre=None,
	reference_doctype=None,
	reference_name=None,
	sms_purpose=None,
	key_values=None,
	extra=None,
):
	"""Send an SMS through SMART Connect API and persist a SMART SMS Log."""
	settings, api_key = _get_settings()
	extra = frappe.parse_json(extra) if isinstance(extra, str) and extra else extra

	client_message_id = client_message_id or frappe.generate_hash(length=20)
	reply_to = settings.callback_url if settings.enable_delivery_callback else None
	registered = settings.registered if settings.registered is not None else None

	payload = _build_payload(
		destination=destination,
		text=text,
		template_name=template_name,
		client_message_id=client_message_id,
		source=source or settings.default_source,
		cost_centre=cost_centre or settings.default_cost_centre,
		reply_to=reply_to,
		registered=registered,
		key_values=key_values,
		extra=extra,
	)

	log = _new_log(
		payload,
		reference_doctype=reference_doctype,
		reference_name=reference_name,
		sms_purpose=sms_purpose,
	)
	url = urljoin(_get_base_url(settings), "messages/sms")

	try:
		response = requests.post(
			url,
			headers=_headers(settings, api_key),
			data=json.dumps(payload),
			timeout=settings.request_timeout or 30,
		)
	except requests.RequestException as exc:
		log.status = "Failed"
		log.error_message = str(exc)
		log.save(ignore_permissions=True)
		frappe.throw("SMART A2P request failed: {0}".format(exc), SmartA2PError)

	log.http_status_code = response.status_code
	log.response_body = _response_body(response)
	log.provider_message_id = _message_id_from_location(response.headers.get("Location"))

	if 200 <= response.status_code < 300:
		log.status = "Accepted"
		log.provider_status = "ACCEPTED"
		log.save(ignore_permissions=True)
		return {
			"log": log.name,
			"status": log.status,
			"destination": log.destination,
			"text": log.text,
			"provider_message_id": log.provider_message_id,
			"client_message_id": log.client_message_id,
			"http_status_code": response.status_code,
		}

	log.status = "Failed"
	log.error_message = log.response_body or response.reason
	log.save(ignore_permissions=True)
	frappe.throw(
		"SMART A2P returned HTTP {0}: {1}".format(response.status_code, log.error_message),
		SmartA2PError,
	)


@frappe.whitelist()
def send_administrator_test_sms(reference_doctype=None, reference_name=None):
	require_vault_custodian_access(branch=get_reference_branch(reference_doctype, reference_name))

	destination = TEST_DESTINATION
	text = TEST_MESSAGE
	if reference_doctype == "Pawn Ticket Jewelry" and reference_name:
		_validate_pawn_ticket_sms_workflow_state(reference_doctype, reference_name)
		destination, text = _get_pawn_ticket_customer_sms_details(reference_doctype, reference_name, "Maturity")

	return _send_administrator_test_sms(
		client_message_id_prefix="SMART-A2P-TEST",
		reference_doctype=reference_doctype,
		reference_name=reference_name,
		destination=destination,
		text=text,
		sms_purpose="Maturity" if reference_doctype == "Pawn Ticket Jewelry" else None,
	)


@frappe.whitelist()
def send_expiry_date_sms(reference_doctype=None, reference_name=None):
	require_vault_custodian_access(branch=get_reference_branch(reference_doctype, reference_name))

	if reference_doctype not in PAWN_TICKET_DOCTYPES or not reference_name:
		frappe.throw("Expiry Date SMS requires a Pawn Ticket reference.", SmartA2PError)

	_validate_pawn_ticket_sms_workflow_state(reference_doctype, reference_name)
	destination, text = _get_pawn_ticket_customer_sms_details(reference_doctype, reference_name, "Expiry")

	return _send_administrator_test_sms(
		client_message_id_prefix="SMART-A2P-EXPIRY",
		reference_doctype=reference_doctype,
		reference_name=reference_name,
		destination=destination,
		text=text,
		sms_purpose="Expiry",
	)


def _send_administrator_test_sms(
	client_message_id_prefix,
	reference_doctype=None,
	reference_name=None,
	destination=TEST_DESTINATION,
	text=TEST_MESSAGE,
	sms_purpose=None,
):
	return send_sms(
		destination=destination,
		text=text,
		client_message_id="{0}-{1}".format(client_message_id_prefix, frappe.generate_hash(length=16)),
		reference_doctype=reference_doctype,
		reference_name=reference_name,
		sms_purpose=sms_purpose,
	)


def _get_pawn_ticket_customer_sms_details(pawn_ticket_doctype, pawn_ticket_name, sms_purpose):
	pawn_ticket = frappe.db.get_value(
		pawn_ticket_doctype,
		pawn_ticket_name,
		[
			"name",
			"customers_tracking_no",
			"customers_full_name",
			"branch",
			"pawn_ticket",
			"maturity_date",
			"expiry_date",
		],
		as_dict=True,
	)
	if not pawn_ticket:
		frappe.throw("{0} {1} was not found.".format(pawn_ticket_doctype, pawn_ticket_name), SmartA2PError)

	customer = pawn_ticket.customers_tracking_no
	if not customer:
		frappe.throw("{0} has no customer tracking number.".format(pawn_ticket_doctype), SmartA2PError)

	contact = frappe.db.get_value("Customer", customer, "customer_primary_contact")
	if not contact:
		contact = frappe.db.get_value(
			"Dynamic Link",
			{
				"link_doctype": "Customer",
				"link_name": customer,
				"parenttype": "Contact",
			},
			"parent",
		)

	if not contact:
		frappe.throw("No Contact is linked to customer {0}.".format(customer), SmartA2PError)

	mobile_no = frappe.db.get_value("Contact", contact, "mobile_no")
	if not mobile_no:
		frappe.throw("Contact {0} has no mobile number.".format(contact), SmartA2PError)

	return mobile_no, _build_pawn_ticket_message(pawn_ticket, sms_purpose)


def _validate_pawn_ticket_sms_workflow_state(pawn_ticket_doctype, pawn_ticket_name):
	workflow_state = frappe.db.get_value(pawn_ticket_doctype, pawn_ticket_name, "workflow_state")
	if workflow_state not in PAWN_TICKET_SMS_WORKFLOW_STATES:
		frappe.throw(
			"{0} {1} must be Active or Expired before sending SMS.".format(
				pawn_ticket_doctype,
				pawn_ticket_name,
			),
			SmartA2PError,
		)


def _build_pawn_ticket_jewelry_maturity_message(pawn_ticket):
	return _build_pawn_ticket_message(pawn_ticket, "Maturity")


def _build_pawn_ticket_message(pawn_ticket, sms_purpose):
	if sms_purpose == "Expiry":
		status_phrase = "expired"
		status_date = formatdate(pawn_ticket.expiry_date) if pawn_ticket.expiry_date else ""
	else:
		status_phrase = "matured"
		status_date = formatdate(pawn_ticket.maturity_date) if pawn_ticket.maturity_date else ""

	branch_contact = _get_branch_sms_contact_details(pawn_ticket.branch)
	return (
		"Good Day Ma'am/Sir {0}!\n"
		"Ito po ang {1} branch, ipinapaalam po namin na ang inyong Pawn Ticket: {2} "
		"ay {3} na sa {4}. Mainam po na ito ay matubuan/renew upang maging updated "
		"ang inyong sangla. Puwede niyo po kami macontact sa FB: {5} at sa phone: {6}. "
		"Maraming salamat po."
	).format(
		pawn_ticket.customers_full_name or "",
		pawn_ticket.branch or "",
		pawn_ticket.pawn_ticket or pawn_ticket.name,
		status_phrase,
		status_date,
		branch_contact.facebook_account,
		branch_contact.contact_number,
	)


def _get_branch_sms_contact_details(branch):
	if not branch:
		frappe.throw("Pawn Ticket has no branch.", SmartA2PError)

	branch_contact = frappe.db.get_value(
		"Branch",
		branch,
		["facebook_account", "contact_number"],
		as_dict=True,
	)
	if not branch_contact:
		frappe.throw("Branch {0} was not found.".format(branch), SmartA2PError)

	if not branch_contact.facebook_account:
		frappe.throw("Branch {0} has no Facebook Account.".format(branch), SmartA2PError)

	if not branch_contact.contact_number:
		frappe.throw("Branch {0} has no Contact Number.".format(branch), SmartA2PError)

	return branch_contact


def send_daily_administrator_test_sms():
	return _send_administrator_test_sms(
		client_message_id_prefix="SMART-A2P-DAILY-TEST",
	)


def send_daily_administrator_test_sms_at_1145():
	return _send_administrator_test_sms(
		client_message_id_prefix="SMART-A2P-DAILY-TEST-1145",
	)


def send_daily_administrator_test_sms_at_1200():
	return _send_administrator_test_sms(
		client_message_id_prefix="SMART-A2P-DAILY-TEST-1200",
	)


def send_daily_administrator_test_sms_at_1210():
	return _send_administrator_test_sms(
		client_message_id_prefix="SMART-A2P-DAILY-TEST-1210",
	)


def send_daily_administrator_test_sms_at_0900():
	return _send_administrator_test_sms(
		client_message_id_prefix=DAILY_0900_TEST_CLIENT_MESSAGE_ID_PREFIX,
	)


def send_daily_pawn_ticket_sms_notifications():
	current_user = frappe.session.user
	summary = {
		"maturity_sent": 0,
		"expiry_sent": 0,
		"failed": [],
		"status_sms_sent": False,
	}

	frappe.set_user("Administrator")
	try:
		for pawn_ticket in _get_pawn_tickets_for_daily_sms(
			"Pawn Ticket Jewelry",
			"maturity_date",
			"texted_upon_maturity",
		):
			if _send_daily_pawn_ticket_sms(
				send_administrator_test_sms,
				"Pawn Ticket Jewelry",
				pawn_ticket.name,
				summary,
				"Maturity",
			):
				summary["maturity_sent"] += 1

		for doctype in PAWN_TICKET_DOCTYPES:
			for pawn_ticket in _get_pawn_tickets_for_daily_sms(
				doctype,
				"expiry_date",
				"texted_upon_expiry",
			):
				if _send_daily_pawn_ticket_sms(
					send_expiry_date_sms,
					doctype,
					pawn_ticket.name,
					summary,
					"Expiry",
				):
					summary["expiry_sent"] += 1

		summary["status_sms_sent"] = _send_daily_text_blast_status_sms(summary)
	finally:
		frappe.set_user(current_user)

	return summary


def _get_pawn_tickets_for_daily_sms(doctype, date_field, texted_field):
	return frappe.get_all(
		doctype,
		filters={
			date_field: today(),
			texted_field: 0,
			"workflow_state": ["in", list(PAWN_TICKET_SMS_WORKFLOW_STATES)],
		},
		fields=["name"],
		order_by="name asc",
	)


def _send_daily_pawn_ticket_sms(send_method, reference_doctype, reference_name, summary, sms_purpose):
	try:
		send_method(reference_doctype=reference_doctype, reference_name=reference_name)
	except Exception:
		summary["failed"].append(
			{
				"reference_doctype": reference_doctype,
				"reference_name": reference_name,
				"sms_purpose": sms_purpose,
			}
		)
		frappe.log_error(
			frappe.get_traceback(),
			"Daily {0} SMS failed for {1} {2}".format(
				sms_purpose,
				reference_doctype,
				reference_name,
			),
		)
		return False

	return True


def _send_daily_text_blast_status_sms(summary):
	total_sms_requests = summary["maturity_sent"] + summary["expiry_sent"]
	text = DAILY_TEXT_BLAST_STATUS_MESSAGE_TEMPLATE.format(total_sms_requests)

	try:
		_send_administrator_test_sms(
			client_message_id_prefix=DAILY_0900_TEST_CLIENT_MESSAGE_ID_PREFIX,
			text=text,
		)
	except Exception:
		frappe.log_error(
			frappe.get_traceback(),
			"Daily text blast status SMS failed",
		)
		return False

	return True


def _first_param(params, keys):
	for key in keys:
		value = params.get(key)
		if value:
			return str(value).strip()
	return None


def _delivery_receipt_value(text, key):
	match = re.search(r"(?:^|\s){0}:([^\s]+)".format(re.escape(key)), str(text or ""), re.IGNORECASE)
	return match.group(1).strip() if match else None


def _delivery_receipt_status(params):
	status = _first_param(params, ("mtStatus", "status", "stat"))
	if status:
		return status

	return _delivery_receipt_value(params.get("text"), "stat")


def _find_log(params):
	client_message_id = _first_param(params, ("clientMessageId", "client_message_id"))
	if client_message_id:
		name = frappe.db.get_value("SMART SMS Log", {"client_message_id": client_message_id})
		if name:
			return frappe.get_doc("SMART SMS Log", name)

	message_ids = [
		_first_param(params, ("mtMessageId", "messageId", "message_id")),
		_delivery_receipt_value(params.get("text"), "id"),
	]
	for message_id in filter(None, message_ids):
		name = frappe.db.get_value("SMART SMS Log", {"provider_message_id": message_id})
		if name:
			return frappe.get_doc("SMART SMS Log", name)

	return None


def _mark_pawn_ticket_texted_if_delivered(log):
	if log.reference_doctype not in PAWN_TICKET_DOCTYPES or not log.reference_name:
		return

	if not frappe.db.exists(log.reference_doctype, log.reference_name):
		return

	fieldname = "texted_upon_expiry" if log.get("sms_purpose") == "Expiry" else "texted_upon_maturity"
	frappe.db.set_value(
		log.reference_doctype,
		log.reference_name,
		fieldname,
		1,
		update_modified=False,
	)


@frappe.whitelist(allow_guest=True)
def smart_a2p_callback(**kwargs):
	"""Receive SMART Connect API GET callbacks for replies and delivery reports."""
	params = dict(kwargs or frappe.local.form_dict or {})
	params.pop("cmd", None)

	log = _find_log(params)
	if log:
		status = _delivery_receipt_status(params)
		if status:
			normalized_status = status.upper()
			log.provider_status = status
			if normalized_status in DELIVERED_PROVIDER_STATUSES:
				log.status = "Delivered"
				log.delivered_at = now_datetime()
				_mark_pawn_ticket_texted_if_delivered(log)
			else:
				log.status = "Callback Received"

		if params.get("messageId"):
			log.last_callback_message_id = params.get("messageId")

		if params.get("text"):
			log.last_callback_text = params.get("text")

		log.last_callback_at = now_datetime()
		log.last_callback_payload = json.dumps(params, indent=2, sort_keys=True)
		log.save(ignore_permissions=True)
	else:
		frappe.log_error(
			json.dumps(params, indent=2, sort_keys=True),
			"SMART A2P callback without matching SMS log",
		)

	frappe.local.response["type"] = "json"
	return {"ok": True}
