# Copyright (c) 2026, Rabie Santillan and Eric Mendoza and contributors
# For license information, please see license.txt

import json

import frappe
from frappe.model.document import Document


class FundTransferSettings(Document):
	def validate(self):
		if self.enable_usd_validation or self.enable_google_uat_sync:
			if not self.get_password("google_service_account_json"):
				frappe.throw("Google Service Account JSON is required when a Google integration is enabled.")

		if self.enable_usd_validation:
			if not self.fx_spreadsheet_id or not self.fx_transaction_sheet:
				frappe.throw("FX Spreadsheet ID and Transaction Sheet are required for USD validation.")

		if self.enable_google_uat_sync:
			if not self.uat_spreadsheet_id or not self.php_uat_sheet or not self.usd_uat_sheet:
				frappe.throw("UAT Spreadsheet ID and both UAT sheet names are required for Google UAT sync.")

		credentials = self.get_password("google_service_account_json")
		if credentials:
			try:
				payload = json.loads(credentials)
			except (TypeError, ValueError):
				frappe.throw("Google Service Account JSON must contain valid JSON.")
			if payload.get("type") != "service_account" or not payload.get("client_email") or not payload.get("private_key"):
				frappe.throw("Google Service Account JSON is missing required service-account fields.")
