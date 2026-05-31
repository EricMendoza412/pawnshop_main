import frappe
from frappe import _
from frappe.utils import escape_html, getdate, today
from urllib.parse import quote

from frappe.integrations.utils import (
    make_get_request
)


ID_PICTURE_BASE_URL = "https://storage.cloud.google.com/gpcustomersids.appspot.com/customerPictures/{0}.jpg"


def get_id_picture_html(id_pic_name=None, empty_message=None):
    if id_pic_name:
        image_url = ID_PICTURE_BASE_URL.format(quote(str(id_pic_name).strip()))
        return """
            <img src="{0}" style="max-width: 400px; height: auto;">
        """.format(escape_html(image_url))

    return """
        <div class="alert alert-warning">
            {0}
        </div>
    """.format(escape_html(empty_message or _("No ID picture set")))

@frappe.whitelist()
def get_contact_image(contact):
    if contact:
        default_id_pic_name = frappe.db.get_value("Contact", contact, "default_id_pic_name")

        if default_id_pic_name:
            return get_id_picture_html(default_id_pic_name)
        else:
            return get_id_picture_html(empty_message=_("No default ID set"))

    return get_id_picture_html(empty_message=_("No primary contact set"))

@frappe.whitelist()
def get_contact_image_by_customer(customer):
    primary_contact = frappe.db.get_value("Customer", customer, "customer_primary_contact")
    return get_contact_image(primary_contact)


@frappe.whitelist()
def get_contact_id_pictures_by_customer(customer):
    primary_contact = frappe.db.get_value("Customer", customer, "customer_primary_contact")
    if not primary_contact:
        return {
            "selected": None,
            "options": [],
            "all_customer_ids_expired": False,
            "html": get_id_picture_html(empty_message=_("No primary contact set"))
        }

    contact = frappe.get_doc("Contact", primary_contact)
    default_id_pic_name = contact.get("default_id_pic_name")
    options = []
    selected = None

    for row in contact.get("id_type") or []:
        id_pic_name = row.get("id_docs_pic_name")
        is_expired = is_id_expired(row.get("expiry_date"))
        option = {
            "value": row.name,
            "id_type": row.get("id_type"),
            "expiry_date": row.get("expiry_date"),
            "id_pic_name": id_pic_name,
            "is_expired": is_expired,
            "label": get_id_picture_option_label(row)
        }
        options.append(option)

        if default_id_pic_name and id_pic_name == default_id_pic_name:
            selected = option["value"]

    if not selected and options:
        selected = options[0]["value"]

    all_customer_ids_expired = bool(options) and all(
        is_id_expired(option.get("expiry_date")) for option in options
    )

    selected_option = next((option for option in options if option["value"] == selected), None)
    if selected_option:
        html = get_id_picture_html(
            selected_option.get("id_pic_name"),
            _("No ID picture set for selected ID")
        )
    else:
        html = get_id_picture_html(empty_message=_("No IDs found for this contact"))

    return {
        "selected": selected,
        "options": options,
        "all_customer_ids_expired": all_customer_ids_expired,
        "html": html
    }


def is_id_expired(expiry_date):
    if not expiry_date or str(expiry_date) == "0000-00-00":
        return False

    return getdate(expiry_date) < getdate(today())


def get_id_picture_option_label(row):
    label_parts = [row.get("id_type") or _("Unknown ID")]

    if row.get("expiry_date"):
        label_parts.append(_("Expiry: {0}").format(row.get("expiry_date")))

    if row.get("id_docs_pic_name"):
        label_parts.append(row.get("id_docs_pic_name"))

    return " | ".join(str(part) for part in label_parts)
