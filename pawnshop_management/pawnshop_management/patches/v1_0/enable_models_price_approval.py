import frappe
from frappe.permissions import add_permission, update_permission_property


def execute():
    frappe.reload_doc('pawnshop_management', 'doctype', 'models')
    # One-time baseline only: later unapproved models must never be grandfathered.
    frappe.db.sql('UPDATE `tabModels` SET has_approved_pricing=1, new_max_av_percent=0')
    add_permission('Models', 'Subastado member NJ', 0)
    for permission in ('read', 'write', 'create', 'report'):
        update_permission_property('Models', 'Subastado member NJ', 0, permission, 1)
    frappe.clear_cache(doctype='Models')
