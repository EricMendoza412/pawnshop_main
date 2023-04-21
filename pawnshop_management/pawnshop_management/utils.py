import frappe
from frappe import _

from frappe.integrations.utils import (
    make_get_request
)

@frappe.whitelist()
def get_contact_image(contact):
    image_html = """
        <div class="alert alert-warning">
            No primary contact set
        </div>
    """
    if contact:
        default_id_pic_name = frappe.db.get_value("Contact", contact, "default_id_pic_name")

        if default_id_pic_name:
            image_url = """
                https://storage.cloud.google.com/gpcustomersids.appspot.com/customerPictures/{0}.jpg
            """.format(default_id_pic_name)

            image_html = """
                <img src="{0}" style="max-width: 400px; height: auto;">
            """.format(image_url)
        else:
            image_html = """
                <div class="alert alert-warning">
                    No default ID set
                </div>
            """

    return image_html

@frappe.whitelist()
def get_contact_image_by_customer(customer):
    primary_contact = frappe.db.get_value("Customer", customer, "customer_primary_contact")
    return get_contact_image(primary_contact)