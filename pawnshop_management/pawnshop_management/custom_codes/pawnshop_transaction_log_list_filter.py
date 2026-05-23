import frappe
from pawnshop_management.pawnshop_management.custom_codes.get_ip import get_ip_from_settings


ALLOWED_BRANCH_ROLES = {
    "Cashier",
    "Operations Supervisor/Cashier",
    "Appraiser/Cashier",
    "Appraiser",
    "Operations Supervisor",
    "Vault Custodian",
}


BRANCH_BY_IP_KEY = {
    "cavite_city": "Garcia''s Pawnshop - CC",
    "poblacion": "Garcia''s Pawnshop - POB",
    "molino": "Garcia''s Pawnshop - MOL",
    "gtc": "Garcia''s Pawnshop - GTC",
    "tanza": "Garcia''s Pawnshop - TNZ",
    "alapan": "Garcia''s Pawnshop - BUC",
    "noveleta": "Garcia''s Pawnshop - NOV",
    "pascam": "Garcia''s Pawnshop - PSC",
    "test": "TEST",
}


def filter_transaction_log_based_on_banch(user):
    current_ip = frappe.local.request_ip
    branch_ip = get_ip_from_settings()

    if not user:
        user = frappe.session.user

    user_role = frappe.get_doc("User", user)
    if user_role.role_profile_name not in ALLOWED_BRANCH_ROLES:
        return

    for ip_key, branch in BRANCH_BY_IP_KEY.items():
        if str(current_ip) == str(branch_ip[ip_key]):
            return f"(`tabPawnshop Transaction Log`.branch = '{branch}')"
