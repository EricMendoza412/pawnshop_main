import frappe
from frappe.utils import today


@frappe.whitelist()
def update_fields_after_status_change_review_nj_batch(inventory_tracing_no):
    doc = frappe.get_doc("Non Jewelry Batch", inventory_tracing_no)
    for items in doc.get('items'):
        frappe.db.set_value('Non Jewelry Items', items.item_no, 'workflow_state', 'Returned')
        frappe.db.commit()

@frappe.whitelist()
def update_fields_after_status_change_collect_nj_batch(inventory_tracing_no):
    doc = frappe.get_doc("Non Jewelry Batch", inventory_tracing_no)
    for items in doc.get('items'):
        frappe.db.set_value('Non Jewelry Items', items.item_no, 'workflow_state', 'Collected')
        frappe.db.commit()

@frappe.whitelist()
def update_fields_after_status_change_redeem_nj_batch(inventory_tracing_no):
    doc = frappe.get_doc("Non Jewelry Batch", inventory_tracing_no)
    for items in doc.get('items'):
        frappe.db.set_value('Non Jewelry Items', items.item_no, 'workflow_state', 'Redeemed')
        frappe.db.commit()

@frappe.whitelist()
def update_fields_after_status_change_renew_nj_batch(inventory_tracing_no):
    doc = frappe.get_doc("Non Jewelry Batch", inventory_tracing_no)
    for items in doc.get('items'):
        frappe.db.set_value('Non Jewelry Items', items.item_no, 'workflow_state', 'Renewed')
        frappe.db.commit()

@frappe.whitelist()
def update_fields_after_status_change_close_installment_agreement_form(installment_agreement_no: str):
    if not installment_agreement_no:
        frappe.throw("Installment Agreement item number is required to update the status.")

    if not frappe.db.exists('Non Jewelry Items', installment_agreement_no):
        frappe.throw(f"Non Jewelry Item {installment_agreement_no} does not exist.")

    frappe.db.set_value('Non Jewelry Items', installment_agreement_no, 'workflow_state', 'For Sale')
    frappe.db.commit()
