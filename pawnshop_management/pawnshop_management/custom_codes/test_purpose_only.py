from datetime import datetime
import re # from python std library
from frappe.utils import add_to_date
import frappe

@frappe.whitelist()
def get_child():
    doc = frappe.get_doc('Pawn Ticket Non Jewelry', '20-86B')
    for child_doc in doc.get_children():
        print(child_doc.name)