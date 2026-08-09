import frappe


def execute():
	report = frappe.get_doc("Report", "Gadgets For Sale")

	server_old = "clauses.append(\"AND current_location != 'Subastado NJ'\")"
	server_new = "clauses.append(\"AND current_location NOT IN ('Subastado NJ', 'Bulk NJ')\")"
	client_old = '["current_location", "!=", "Subastado NJ"],'
	client_new = '["current_location", "not in", ["Subastado NJ", "Bulk NJ"]],'

	updated_script = (report.report_script or "").replace(server_old, server_new)
	updated_javascript = (report.javascript or "").replace(client_old, client_new)

	if updated_script == report.report_script and server_new not in updated_script:
		frappe.throw("Could not find the Gadgets For Sale server-side location exclusion")

	if updated_javascript == report.javascript and client_new not in updated_javascript:
		frappe.throw("Could not find the Gadgets For Sale location-filter exclusion")

	if updated_script != report.report_script or updated_javascript != report.javascript:
		report.report_script = updated_script
		report.javascript = updated_javascript
		report.save(ignore_permissions=True)

