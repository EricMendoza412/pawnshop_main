from pawnshop_management.operations_access_control.access_control import get_branch_filter_condition


def filter_cpr_based_on_banch(user):
	return get_branch_filter_condition("Cash Position Report", user)
