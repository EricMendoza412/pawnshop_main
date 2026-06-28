import frappe
from pawnshop_management.pawnshop_management.custom_codes.get_ip import get_ip_from_settings
import json

def filter_ats_based_on_banch(user):
    filters = frappe.form_dict.get('filters')
    if filters:
        try:
            filters = json.loads(filters)
            if isinstance(filters, list):
                for filter_item in filters:
                    if isinstance(filter_item, list) and len(filter_item) > 3:
                        key, value = filter_item[1], filter_item[3]
                        if key == "customer_name" and value:
                            return ""
        except json.JSONDecodeError:
            pass

    current_ip = frappe.local.request_ip
    branch_ip = get_ip_from_settings()
    if not user:
        user = frappe.session.user
    user_role = frappe.get_doc('User', user)
    if str(current_ip) == str(branch_ip['cavite_city']) and (user_role.role_profile_name == "Cashier" or user_role.role_profile_name == "Operations Supervisor/Cashier" or user_role.role_profile_name == "Appraiser/Cashier" or user_role.role_profile_name == "Senior Appraiser" or user_role.role_profile_name == "Junior Appraiser" or user_role.role_profile_name == "Appraiser" or user_role.role_profile_name == "Operations Supervisor" or user_role.role_profile_name == "Vault Custodian"):
        return "(`tabAgreement to Sell`.branch = 'Garcia''s Pawnshop - CC')"
    elif str(current_ip) == str(branch_ip['poblacion']) and (user_role.role_profile_name == "Cashier" or user_role.role_profile_name == "Operations Supervisor/Cashier" or user_role.role_profile_name == "Appraiser/Cashier" or user_role.role_profile_name == "Senior Appraiser" or user_role.role_profile_name == "Junior Appraiser" or user_role.role_profile_name == "Appraiser" or user_role.role_profile_name == "Operations Supervisor" or user_role.role_profile_name == "Vault Custodian"):
        return "(`tabAgreement to Sell`.branch = 'Garcia''s Pawnshop - POB')"
    elif str(current_ip) == str(branch_ip['molino']) and (user_role.role_profile_name == "Cashier" or user_role.role_profile_name == "Operations Supervisor/Cashier" or user_role.role_profile_name == "Appraiser/Cashier" or user_role.role_profile_name == "Senior Appraiser" or user_role.role_profile_name == "Junior Appraiser" or user_role.role_profile_name == "Appraiser" or user_role.role_profile_name == "Operations Supervisor" or user_role.role_profile_name == "Vault Custodian"):
        return "(`tabAgreement to Sell`.branch = 'Garcia''s Pawnshop - MOL')"
    elif str(current_ip) == str(branch_ip['gtc']) and (user_role.role_profile_name == "Cashier" or user_role.role_profile_name == "Operations Supervisor/Cashier" or user_role.role_profile_name == "Appraiser/Cashier" or user_role.role_profile_name == "Senior Appraiser" or user_role.role_profile_name == "Junior Appraiser" or user_role.role_profile_name == "Appraiser" or user_role.role_profile_name == "Operations Supervisor" or user_role.role_profile_name == "Vault Custodian"):
        return "(`tabAgreement to Sell`.branch = 'Garcia''s Pawnshop - GTC')"
    elif str(current_ip) == str(branch_ip['tanza']) and (user_role.role_profile_name == "Cashier" or user_role.role_profile_name == "Operations Supervisor/Cashier" or user_role.role_profile_name == "Appraiser/Cashier" or user_role.role_profile_name == "Senior Appraiser" or user_role.role_profile_name == "Junior Appraiser" or user_role.role_profile_name == "Appraiser" or user_role.role_profile_name == "Operations Supervisor" or user_role.role_profile_name == "Vault Custodian"):
        return "(`tabAgreement to Sell`.branch = 'Garcia''s Pawnshop - TNZ')"
    elif str(current_ip) == str(branch_ip['alapan']) and (user_role.role_profile_name == "Cashier" or user_role.role_profile_name == "Operations Supervisor/Cashier" or user_role.role_profile_name == "Appraiser/Cashier" or user_role.role_profile_name == "Senior Appraiser" or user_role.role_profile_name == "Junior Appraiser" or user_role.role_profile_name == "Appraiser" or user_role.role_profile_name == "Operations Supervisor" or user_role.role_profile_name == "Vault Custodian"):
        return "(`tabAgreement to Sell`.branch = 'Garcia''s Pawnshop - BUC')"
    elif str(current_ip) == str(branch_ip['noveleta']) and (user_role.role_profile_name == "Cashier" or user_role.role_profile_name == "Operations Supervisor/Cashier" or user_role.role_profile_name == "Appraiser/Cashier" or user_role.role_profile_name == "Senior Appraiser" or user_role.role_profile_name == "Junior Appraiser" or user_role.role_profile_name == "Appraiser" or user_role.role_profile_name == "Operations Supervisor" or user_role.role_profile_name == "Vault Custodian"):
        return "(`tabAgreement to Sell`.branch = 'Garcia''s Pawnshop - NOV')"
    elif str(current_ip) == str(branch_ip['pascam']) and (user_role.role_profile_name == "Cashier" or user_role.role_profile_name == "Operations Supervisor/Cashier" or user_role.role_profile_name == "Appraiser/Cashier" or user_role.role_profile_name == "Senior Appraiser" or user_role.role_profile_name == "Junior Appraiser" or user_role.role_profile_name == "Appraiser" or user_role.role_profile_name == "Operations Supervisor" or user_role.role_profile_name == "Vault Custodian"):
        return "(`tabAgreement to Sell`.branch = 'Garcia''s Pawnshop - PSC')"
    elif str(current_ip) == str(branch_ip['test']) and (user_role.role_profile_name == "Cashier" or user_role.role_profile_name == "Operations Supervisor/Cashier" or user_role.role_profile_name == "Appraiser/Cashier" or user_role.role_profile_name == "Senior Appraiser" or user_role.role_profile_name == "Junior Appraiser" or user_role.role_profile_name == "Appraiser" or user_role.role_profile_name == "Operations Supervisor" or user_role.role_profile_name == "Vault Custodian"):
        return "(`tabAgreement to Sell`.branch = 'TEST')"    
