import re
import frappe
import frappe.permissions 
from frappe import _
from frappe.sessions import delete_session

@frappe.whitelist()
def show_ip():
    ip = frappe.local.request_ip
    return ip

def login_feed(login_manager):
    ip = frappe.local.request_ip
    user = frappe.get_doc('User', login_manager.user)
    branch_address = frappe.get_all('Branch IP Addressing', filters={'ip_address': ip}, fields=['name', 'ip_address'])

    roles = {"Cashier", "Appraiser", "Vault Custodian", "Supervisor/Cashier", "Appraiser/Cashier", "Supervisor"}

    if user.role_profile_name in roles:
        if branch_address:
            branch_name = branch_address[0]['name']
            frappe.msgprint(
                msg='Welcome, ' + user.full_name + ' (' + user.role_profile_name + ')',
                title='Welcome to ' + branch_name
            )
        else:
            frappe.throw(
                title='Log In Restricted',
                msg='You are not authorized to log in at this station',
                exc=RuntimeError
            )
    else:
        if user.role_profile_name:
            frappe.msgprint(
                msg='Welcome, ' + user.full_name + ' (' + user.role_profile_name + ')',
            )


def post_login(login_manager):
    if login_feed(login_manager) == 0:
        delete_session()
