import frappe
from frappe.model.naming import make_autoname


def execute():
	logs = frappe.get_all(
		"SMART SMS Log",
		filters={"sms_purpose": "Text Blast", "name": ("not like", "TXTBLAST-SMS-%")},
		fields=["name"],
		order_by="creation asc",
	)
	for log in logs:
		new_name = make_autoname("TXTBLAST-SMS-.#####")
		frappe.rename_doc("SMART SMS Log", log.name, new_name, force=True, ignore_permissions=True)
