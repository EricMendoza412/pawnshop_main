from pawnshop_management.operations_access_control.access_control import get_branch_filter_condition


def filter_pr_based_on_banch(user):
	return get_branch_filter_condition("Provisional Receipt", user)
