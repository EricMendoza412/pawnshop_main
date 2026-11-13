from decimal import Decimal, ROUND_CEILING

import frappe
from frappe.model.document import Document
from frappe.utils import cstr, now_datetime, today

ROLE = "Subastado member NJ"
INPUTS = ("new_max_sell_price", "new_max_av_percent")
OUTPUTS = ("new_maximum", "new_minimum", "new_defective", "maximum_difference")
CURRENT = ("max_sell_price", "max_av_percent", "maximum", "minimum", "defective")
CONTROLLED = CURRENT + (
    "pending_price_change_approval", "has_approved_pricing", "proposed_by", "proposed_on",
    "approved_by", "approved_on", "last_srp_update",
)
# Only server-created instances may carry this capability; request flags cannot forge it.
_PRICE_ACTION = object()


def check_price_role():
    if frappe.session.user != "Administrator" and ROLE not in frappe.get_roles():
        frappe.throw("Only Subastado member NJ users can manage price proposals.", frappe.PermissionError)


def calculate_prices(price, percent):
    try:
        price, percent = Decimal(str(price)), Decimal(str(percent))
    except Exception:
        frappe.throw("Enter a valid selling price and Max AV percentage.")
    if not price.is_finite() or price < 0:
        frappe.throw("Selling price must be zero or greater.")
    if not percent.is_finite() or not 0 < percent <= 100:
        frappe.throw("Max AV percentage must be greater than 0 and at most 100.")
    def rounded(value):
        return float((value / 100).to_integral_value(rounding=ROUND_CEILING) * 100)
    maximum = rounded(price * percent / 100)
    return maximum, rounded(Decimal(str(maximum)) * Decimal('.8')), rounded(Decimal(str(maximum)) * Decimal('.6'))


class Models(Document):
    def validate(self):
        if getattr(self, "_price_action", None) is _PRICE_ACTION:
            return
        old = self.get_doc_before_save()
        for field in CONTROLLED:
            previous = old.get(field) if old else None
            current = self.get(field)
            # Browser JSON carries dates as strings; database documents carry
            # date/datetime objects. Compare their serialized values, not types.
            if field in ("last_srp_update", "proposed_on", "approved_on"):
                current, previous = cstr(current or ""), cstr(previous or "")
            if (current or 0) != (previous or 0):
                frappe.throw("Approved prices and proposal audit fields can only be changed through price approval actions.")
        if not old:
            for field in CURRENT:
                self.set(field, 0)
        changed = any((self.get(f) or 0) != ((old.get(f) if old else None) or 0) for f in INPUTS)
        if not changed:
            for field in OUTPUTS:
                self.set(field, old.get(field) if old else None)
            return
        check_price_role()
        if old and old.pending_price_change_approval and old.proposed_by != frappe.session.user:
            frappe.throw("Only the proposer can revise this pending proposal.", frappe.PermissionError)
        maximum, minimum, defective = calculate_prices(self.new_max_sell_price, self.new_max_av_percent)
        self.new_maximum, self.new_minimum, self.new_defective = maximum, minimum, defective
        self.maximum_difference = maximum - (self.maximum or 0)
        self.pending_price_change_approval = 1
        self.proposed_by = frappe.session.user
        self.proposed_on = now_datetime()


def locked_proposal(name, modified):
    check_price_role()
    doc = frappe.get_doc("Models", name, for_update=True)
    doc.check_permission("write")
    if str(doc.modified) != str(modified):
        frappe.throw("This model changed after review. Reload and review it again.")
    if not doc.pending_price_change_approval:
        frappe.throw("This model has no pending price proposal.")
    return doc


def clear_proposal(doc):
    for field in INPUTS + OUTPUTS:
        doc.set(field, None)
    doc.pending_price_change_approval = 0


@frappe.whitelist()
def approve_price_change(name, modified):
    doc = locked_proposal(name, modified)
    if doc.proposed_by == frappe.session.user and frappe.session.user != "Administrator":
        frappe.throw("You cannot approve your own price proposal.", frappe.PermissionError)
    values = calculate_prices(doc.new_max_sell_price, doc.new_max_av_percent)
    if doc.max_sell_price != doc.new_max_sell_price or not doc.has_approved_pricing:
        doc.last_srp_update = today()
    doc.max_sell_price, doc.max_av_percent = doc.new_max_sell_price, doc.new_max_av_percent
    doc.maximum, doc.minimum, doc.defective = values
    doc.has_approved_pricing = 1
    doc.approved_by, doc.approved_on = frappe.session.user, now_datetime()
    clear_proposal(doc)
    doc._price_action = _PRICE_ACTION
    doc.save()
    return doc.name


@frappe.whitelist()
def withdraw_price_change(name, modified):
    doc = locked_proposal(name, modified)
    if doc.proposed_by != frappe.session.user:
        frappe.throw("Only the proposer can withdraw this proposal.", frappe.PermissionError)
    clear_proposal(doc)
    doc.proposed_by = doc.proposed_on = None
    doc._price_action = _PRICE_ACTION
    doc.save()


@frappe.whitelist()
def pending_price_changes():
    check_price_role()
    return frappe.get_list("Models", filters={"pending_price_change_approval": 1},
        fields=["name", "modified", "proposed_by", "proposed_on"] + list(CURRENT + INPUTS + OUTPUTS),
        order_by="proposed_on asc", limit_page_length=0)


@frappe.whitelist()
def approve_price_changes(proposals):
    check_price_role()
    proposals = frappe.parse_json(proposals)
    if not isinstance(proposals, list) or not 1 <= len(proposals) <= 100:
        frappe.throw("Select between 1 and 100 proposals.")
    results = []
    for row in sorted(proposals, key=lambda row: row["name"]):
        frappe.db.savepoint("price_approval")
        try:
            approve_price_change(row["name"], row["modified"])
            results.append({"name": row["name"], "approved": True})
        except (frappe.ValidationError, frappe.PermissionError, frappe.DoesNotExistError) as exc:
            frappe.db.rollback(save_point="price_approval")
            results.append({"name": row["name"], "approved": False, "reason": str(exc)})
    return results
