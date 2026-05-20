import json
import re
from urllib.parse import urljoin

import frappe
import requests
from frappe.utils import now_datetime


DEFAULT_BASE_URL = "https://enterprise.messagingsuite.smart.com.ph/cgpapi/"
SMS_MESSAGE_TYPE = "sms"
E164_RE = re.compile(r"^\d{1,15}$")
TEST_DESTINATION = "639178400153"
TEST_MESSAGE = "Hello There"


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


def _new_log(payload, reference_doctype=None, reference_name=None):
	log = frappe.new_doc("SMART SMS Log")
	log.destination = payload.get("destination")
	log.message_type = SMS_MESSAGE_TYPE
	log.source = payload.get("source")
	log.client_message_id = payload.get("clientMessageId")
	log.reference_doctype = reference_doctype
	log.reference_name = reference_name
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

	log = _new_log(payload, reference_doctype=reference_doctype, reference_name=reference_name)
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
	if frappe.session.user != "Administrator":
		frappe.throw("Only Administrator can send the SMART A2P test SMS.", frappe.PermissionError)

	return send_sms(
		destination=TEST_DESTINATION,
		text=TEST_MESSAGE,
		client_message_id="SMART-A2P-TEST-{0}".format(frappe.generate_hash(length=16)),
		reference_doctype=reference_doctype,
		reference_name=reference_name,
	)


def send_daily_administrator_test_sms():
	return send_sms(
		destination=TEST_DESTINATION,
		text=TEST_MESSAGE,
		client_message_id="SMART-A2P-DAILY-TEST-{0}".format(frappe.generate_hash(length=16)),
		reference_doctype="Scheduled Job",
		reference_name="Daily SMART A2P Test SMS",
	)


def _find_log(params):
	client_message_id = params.get("clientMessageId")
	if client_message_id:
		name = frappe.db.get_value("SMART SMS Log", {"client_message_id": client_message_id})
		if name:
			return frappe.get_doc("SMART SMS Log", name)

	mt_message_id = params.get("mtMessageId")
	if mt_message_id:
		name = frappe.db.get_value("SMART SMS Log", {"provider_message_id": mt_message_id})
		if name:
			return frappe.get_doc("SMART SMS Log", name)

	return None


@frappe.whitelist(allow_guest=True)
def smart_a2p_callback(**kwargs):
	"""Receive SMART Connect API GET callbacks for replies and delivery reports."""
	params = dict(kwargs or frappe.local.form_dict or {})
	params.pop("cmd", None)

	log = _find_log(params)
	if log:
		status = params.get("mtStatus")
		if status:
			log.provider_status = status
			log.status = "Delivered" if status == "DELIVERED" else "Callback Received"
			log.delivered_at = params.get("mtDoneDate") if status == "DELIVERED" else log.delivered_at

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
