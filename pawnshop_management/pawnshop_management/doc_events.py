import frappe
def validate_contact(contact, method):
    for id in contact.id_type:
        if id.is_primary:
            contact.default_id_type = id.id_type
            contact.default_expiry_date = id.expiry_date
            contact.default_id_pic_name = id.id_docs_pic_name
            break