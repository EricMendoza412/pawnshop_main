import frappe
from frappe.model.document import Document

from pawnshop_management.pawnshop_management.smart_a2p import DEFAULT_BASE_URL


class SMARTA2PSettings(Document):
	def validate(self):
		if not self.base_url:
			self.base_url = DEFAULT_BASE_URL

		if self.enabled and not self.api_id:
			frappe.throw("API ID is required when SMART A2P is enabled.")

		if self.enabled and not self.get_password("api_key"):
			frappe.throw("API Key is required when SMART A2P is enabled.")

		if self.enable_delivery_callback and not self.callback_url:
			frappe.throw("Callback URL is required when delivery callback is enabled.")
