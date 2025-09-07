import frappe
from frappe.utils import today





@frappe.whitelist()
def update_pawn_tickets():
    non_jewelry = frappe.db.get_all('Pawn Ticket Non Jewelry', 
        filters={
            'workflow_state': 'Active'
        },
        pluck='name')
    for i in range(len(non_jewelry)):
        pawn_ticket=frappe.get_doc('Pawn Ticket Non Jewelry', non_jewelry[i])
        print(type(pawn_ticket.expiry_date))
        # if pawn_ticket.expiry_date) < str(today()):
        #     print("True")

@frappe.whitelist()
def change_pawn_ticket_nj_status_to_expire():
    expired_pt = frappe.db.get_all('Pawn Ticket Non Jewelry', 
        filters={
            'expiry_date': today(),
            'workflow_state': "Active"
        },
        fields=['name']
    )
    for i in range(len(expired_pt)):
        frappe.db.set_value('Pawn Ticket Non Jewelry', expired_pt[i].name, 'workflow_state', 'Expired')
        frappe.db.commit()
        change_pt_inventory_batch_and_items('Pawn Ticket Non Jewelry', expired_pt[i].name)

@frappe.whitelist()
def change_pawn_ticket_j_status_to_expire():
    expired_pt = frappe.db.get_all('Pawn Ticket Jewelry', 
        filters={
            'expiry_date': today(),
            'workflow_state': "Active"
        },
        fields=['name']
    )
    for i in range(len(expired_pt)):
        frappe.db.set_value('Pawn Ticket Jewelry', expired_pt[i].name, 'workflow_state', 'Expired')
        frappe.db.commit()
        change_pt_inventory_batch_and_items('Pawn Ticket Jewelry', expired_pt[i].name)
        

def change_pt_inventory_batch_and_items(pawn_ticket_type, pawn_ticket):
    doc = frappe.get_doc(pawn_ticket_type, pawn_ticket)
    if pawn_ticket_type == 'Pawn Ticket Non Jewelry':
        for items in doc.get('non_jewelry_items'):
            frappe.db.set_value('Non Jewelry Items', items.item_no, 'workflow_state', 'Collected')
            frappe.db.commit()
        frappe.db.set_value('Non Jewelry Batch', doc.inventory_tracking_no, 'workflow_state', 'Expired')
        frappe.db.commit()
    elif pawn_ticket_type == 'Pawn Ticket Jewelry':
        for items in doc.get('jewelry_items'):
            frappe.db.set_value('Jewelry Items', items.item_no, 'workflow_state', 'Collected')
            frappe.db.commit()
        frappe.db.set_value('Jewelry Batch', doc.inventory_tracking_no, 'workflow_state', 'Expired')
        frappe.db.commit()

@frappe.whitelist()
def update_fields_after_status_change_collect_pawn_ticket(pawn_ticket_type, inventory_tracking_no, pawn_ticket_no):
    frappe.db.set_value(pawn_ticket_type, pawn_ticket_no, 'change_status_date', today())

    doc = frappe.get_doc(pawn_ticket_type, pawn_ticket_no)
    if pawn_ticket_type == 'Pawn Ticket Non Jewelry':
        for items in doc.get('non_jewelry_items'):
            frappe.db.set_value('Non Jewelry Items', items.item_no, 'workflow_state', 'Collected')
        frappe.db.set_value('Non Jewelry Batch', inventory_tracking_no, 'workflow_state', 'Expired')

    elif pawn_ticket_type == 'Pawn Ticket Jewelry':
        for items in doc.get('jewelry_items'):
            frappe.db.set_value('Jewelry Items', items.item_no, 'workflow_state', 'Collected')

        frappe.db.set_value('Jewelry Batch', inventory_tracking_no, 'workflow_state', 'Expired')


@frappe.whitelist()
def update_fields_after_status_change_return_pawn_ticket(pawn_ticket_type, inventory_tracking_no, pawn_ticket_no):
    frappe.db.set_value(pawn_ticket_type, pawn_ticket_no, 'change_status_date', today())

    doc = frappe.get_doc(pawn_ticket_type, pawn_ticket_no)
    if pawn_ticket_type == 'Pawn Ticket Non Jewelry':
        for items in doc.get('non_jewelry_items'):
            frappe.db.set_value('Non Jewelry Items', items.item_no, 'workflow_state', 'Returned')
        frappe.db.set_value('Non Jewelry Batch', inventory_tracking_no, 'workflow_state', 'Returned')
    elif pawn_ticket_type == 'Pawn Ticket Jewelry':
        for items in doc.get('jewelry_items'):
            frappe.db.set_value('Jewelry Items', items.item_no, 'workflow_state', 'Returned')
        frappe.db.set_value('Jewelry Batch', inventory_tracking_no, 'workflow_state', 'Returned')

@frappe.whitelist()
def update_fields_after_status_change_redeem_pawn_ticket(pawn_ticket_type, inventory_tracking_no, pawn_ticket_no):
    frappe.db.set_value(pawn_ticket_type, pawn_ticket_no, 'change_status_date', today())

    doc = frappe.get_doc(pawn_ticket_type, pawn_ticket_no)
    if pawn_ticket_type == 'Pawn Ticket Non Jewelry':
        for items in doc.get('non_jewelry_items'):
            frappe.db.set_value('Non Jewelry Items', items.item_no, 'workflow_state', 'Redeemed')
        frappe.db.set_value('Non Jewelry Batch', inventory_tracking_no, 'workflow_state', 'Redeemed')
    elif pawn_ticket_type == 'Pawn Ticket Jewelry':
        for items in doc.get('jewelry_items'):
            frappe.db.set_value('Jewelry Items', items.item_no, 'workflow_state', 'Redeemed')
        frappe.db.set_value('Jewelry Batch', inventory_tracking_no, 'workflow_state', 'Redeemed')

@frappe.whitelist()
def update_fields_after_status_change_reject_pawn_ticket(pawn_ticket_type, inventory_tracking_no, pawn_ticket_no):
    frappe.db.set_value(pawn_ticket_type, pawn_ticket_no, 'change_status_date', today())

@frappe.whitelist()
def update_fields_after_status_change_renew_pawn_ticket(pawn_ticket_type, inventory_tracking_no, pawn_ticket_no):
    frappe.db.set_value(pawn_ticket_type, pawn_ticket_no, 'change_status_date', today())

    doc = frappe.get_doc(pawn_ticket_type, pawn_ticket_no)
    if pawn_ticket_type == 'Pawn Ticket Non Jewelry':
        for items in doc.get('non_jewelry_items'):
            frappe.db.set_value('Non Jewelry Items', items.item_no, 'workflow_state', 'Renewed')
        frappe.db.set_value('Non Jewelry Batch', inventory_tracking_no, 'workflow_state', 'Renewed')
    elif pawn_ticket_type == 'Pawn Ticket Jewelry':
        for items in doc.get('jewelry_items'):
            frappe.db.set_value('Jewelry Items', items.item_no, 'workflow_state', 'Renewed')
        frappe.db.set_value('Jewelry Batch', inventory_tracking_no, 'workflow_state', 'Renewed')


@frappe.whitelist()
def update_fields_after_status_change_pull_out_pawn_ticket(pawn_ticket_type, inventory_tracking_no, pawn_ticket_no):
    frappe.db.set_value(pawn_ticket_type, pawn_ticket_no, 'change_status_date', today())

    doc = frappe.get_doc(pawn_ticket_type, pawn_ticket_no)
    if pawn_ticket_type == 'Pawn Ticket Non Jewelry':
        #get desired_principal from pawn ticket and put in the pt_principal field of non jewelry items
        po_principal = frappe.get_value(pawn_ticket_type, pawn_ticket_no, 'desired_principal')
        # for items in doc.get('non_jewelry_items'):
        #     frappe.db.set_value('Non Jewelry Items', items.item_no, 'workflow_state', 'Pulled Out')
        #     frappe.db.set_value('Non Jewelry Items', items.item_no, 'pt_principal', po_principal)
        frappe.db.set_value('Non Jewelry Batch', inventory_tracking_no, 'workflow_state', 'Pulled Out')
    elif pawn_ticket_type == 'Pawn Ticket Jewelry':
        for items in doc.get('jewelry_items'):
            frappe.db.set_value('Jewelry Items', items.item_no, 'workflow_state', 'Pulled Out')
        frappe.db.set_value('Jewelry Batch', inventory_tracking_no, 'workflow_state', 'Pulled Out')


@frappe.whitelist()
def increment_b_series(branch):
    if branch == "Rabie's House":
        doc = frappe.get_doc("Pawnshop Naming Series", "Rabie's House")
        doc.b_series += 1
        doc.save(ignore_permissions=True)
    elif branch == "Garcia's Pawnshop - CC":
        doc = frappe.get_doc("Pawnshop Naming Series", "Garcia's Pawnshop - CC")
        doc.b_series += 1
        doc.save(ignore_permissions=True)
    elif branch == "Garcia's Pawnshop - MOL":
        doc = frappe.get_doc("Pawnshop Naming Series", "Garcia's Pawnshop - MOL")
        doc.b_series += 1
        doc.save(ignore_permissions=True)
    elif branch == "Garcia's Pawnshop - POB":
        doc = frappe.get_doc("Pawnshop Naming Series", "Garcia's Pawnshop - POB")
        doc.b_series += 1
        doc.save(ignore_permissions=True)
    elif branch == "Garcia's Pawnshop - GTC":
        doc = frappe.get_doc("Pawnshop Naming Series", "Garcia's Pawnshop - GTC")
        doc.b_series += 1
        doc.save(ignore_permissions=True)
    elif branch == "Garcia's Pawnshop - TNZ":
        doc = frappe.get_doc("Pawnshop Naming Series", "Garcia's Pawnshop - TNZ")
        doc.b_series += 1
        doc.save(ignore_permissions=True)