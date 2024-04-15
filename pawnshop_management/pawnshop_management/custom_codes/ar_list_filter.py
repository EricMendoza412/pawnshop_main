import frappe
from pawnshop_management.pawnshop_management.custom_codes.get_ip import get_ip_from_settings

def filter_ar_based_on_banch(user):
    current_ip = frappe.local.request_ip
    branch_ip = get_ip_from_settings()
    if not user:
        user = frappe.session.user
    user_role = frappe.get_doc('User', user)
    if str(current_ip) == str(branch_ip['cavite_city']) and (user_role.role_profile_name == "Cashier" or user_role.role_profile_name == "Supervisor/Cashier" or user_role.role_profile_name == "Appraiser/Cashier" or user_role.role_profile_name == "Appraiser" or user_role.role_profile_name == "Supervisor" or user_role.role_profile_name == "Vault Custodian"):
        return "(`tabAcknowledgement Receipt`.branch = 'Garcia''s Pawnshop - CC')"
    elif str(current_ip) == str(branch_ip['poblacion']) and (user_role.role_profile_name == "Cashier" or user_role.role_profile_name == "Supervisor/Cashier" or user_role.role_profile_name == "Appraiser/Cashier" or user_role.role_profile_name == "Appraiser" or user_role.role_profile_name == "Supervisor" or user_role.role_profile_name == "Vault Custodian"):
        return "(`tabAcknowledgement Receipt`.branch = 'Garcia''s Pawnshop - POB')"
    elif str(current_ip) == str(branch_ip['molino']) and (user_role.role_profile_name == "Cashier" or user_role.role_profile_name == "Supervisor/Cashier" or user_role.role_profile_name == "Appraiser/Cashier" or user_role.role_profile_name == "Appraiser" or user_role.role_profile_name == "Supervisor" or user_role.role_profile_name == "Vault Custodian"):
        return "(`tabAcknowledgement Receipt`.branch = 'Garcia''s Pawnshop - MOL')"
    elif str(current_ip) == str(branch_ip['gtc']) and (user_role.role_profile_name == "Cashier" or user_role.role_profile_name == "Supervisor/Cashier" or user_role.role_profile_name == "Appraiser/Cashier" or user_role.role_profile_name == "Appraiser" or user_role.role_profile_name == "Supervisor" or user_role.role_profile_name == "Vault Custodian"):
        return "(`tabAcknowledgement Receipt`.branch = 'Garcia''s Pawnshop - GTC')"
    elif str(current_ip) == str(branch_ip['tanza']) and (user_role.role_profile_name == "Cashier" or user_role.role_profile_name == "Supervisor/Cashier" or user_role.role_profile_name == "Appraiser/Cashier" or user_role.role_profile_name == "Appraiser" or user_role.role_profile_name == "Supervisor" or user_role.role_profile_name == "Vault Custodian"):
        return "(`tabAcknowledgement Receipt`.branch = 'Garcia''s Pawnshop - TNZ')"
    elif str(current_ip) == str(branch_ip['alapan']) and (user_role.role_profile_name == "Cashier" or user_role.role_profile_name == "Supervisor/Cashier" or user_role.role_profile_name == "Appraiser/Cashier" or user_role.role_profile_name == "Appraiser" or user_role.role_profile_name == "Supervisor" or user_role.role_profile_name == "Vault Custodian"):
        return "(`tabAcknowledgement Receipt`.branch = 'Garcia''s Pawnshop - ALP')"
    elif str(current_ip) == str(branch_ip['noveleta']) and (user_role.role_profile_name == "Cashier" or user_role.role_profile_name == "Supervisor/Cashier" or user_role.role_profile_name == "Appraiser/Cashier" or user_role.role_profile_name == "Appraiser" or user_role.role_profile_name == "Supervisor" or user_role.role_profile_name == "Vault Custodian"):
        return "(`tabAcknowledgement Receipt`.branch = 'Garcia''s Pawnshop - NOV')"
    elif str(current_ip) == str(branch_ip['test']) and (user_role.role_profile_name == "Cashier" or user_role.role_profile_name == "Supervisor/Cashier" or user_role.role_profile_name == "Appraiser/Cashier" or user_role.role_profile_name == "Appraiser" or user_role.role_profile_name == "Supervisor" or user_role.role_profile_name == "Vault Custodian"):
        return "(`tabAcknowledgement Receipt`.branch = 'TEST')"
    
        