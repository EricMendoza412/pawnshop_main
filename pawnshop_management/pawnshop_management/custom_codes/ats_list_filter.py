from pawnshop_management.operations_access_control.access_control import (
	form_filter_has_value,
	get_branch_filter_condition,
)


def filter_ats_based_on_banch(user):
	if form_filter_has_value("customer_name"):
		return ""

	return get_branch_filter_condition("Agreement to Sell", user)
