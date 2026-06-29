from pawnshop_management.operations_access_control.access_control import (
	form_filter_has_value,
	get_branch_filter_condition,
)


def filter_j_based_on_banch(user):
	if form_filter_has_value("customers_full_name"):
		return ""

	return get_branch_filter_condition("Pawn Ticket Jewelry", user)
