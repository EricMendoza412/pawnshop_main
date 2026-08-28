from pawnshop_management.pawnshop_management.patches.v1_0.sync_branch_field_layout import (
	execute as sync_branch_field_layout,
)
from pawnshop_management.pawnshop_management.patches.v1_0.sync_fund_transfer_workspaces import (
	execute as sync_fund_transfer_workspaces,
)
from pawnshop_management.pawnshop_management.patches.v1_0.sync_fund_transfer_permissions import (
	execute as sync_fund_transfer_permissions,
)
from pawnshop_management.pawnshop_management.patches.v1_0.sync_home_workflow_actions_shortcut import (
	sync_home_workflow_actions_shortcut,
)


def execute():
	"""Synchronize database-managed custom fields and existing workspaces after schema sync."""
	sync_branch_field_layout()
	sync_fund_transfer_permissions()
	sync_fund_transfer_workspaces()
	sync_home_workflow_actions_shortcut()
