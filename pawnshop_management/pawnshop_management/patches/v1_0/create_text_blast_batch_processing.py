import frappe


def execute():
	frappe.reload_doc("pawnshop_management", "doctype", "text_blast_batch")
	frappe.reload_doc("pawnshop_management", "doctype", "text_blast")

	for text_blast in frappe.get_all(
		"Text Blast",
		filters={"workflow_state": "Sent"},
		fields=["name"],
	):
		total = frappe.db.count("Recipient List", {"parent": text_blast.name, "parenttype": "Text Blast"})
		accepted = frappe.db.count(
			"SMART SMS Log",
			{
				"reference_doctype": "Text Blast",
				"reference_name": text_blast.name,
				"status": ("in", ["Queued", "Accepted", "Callback Received", "Delivered"]),
			},
		)
		frappe.db.set_value(
			"Text Blast",
			text_blast.name,
			{
				"batch_size": 250,
				"max_attempts": 3,
				"total_recipients": total,
				"accepted_recipients": min(accepted, total),
				"unsent_recipients": max(total - accepted, 0),
				"processing_progress": (min(accepted, total) * 100.0 / total) if total else 0,
				"processing_status": "Completed" if total and accepted >= total else "Partially Failed",
			},
			update_modified=False,
		)
