from pawnshop_management.operations_access_control.access_control import get_branch_filter_condition


def filter_transaction_log_based_on_banch(user):
	return get_branch_filter_condition("Pawnshop Transaction Log", user)
