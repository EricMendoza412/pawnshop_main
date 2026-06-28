from pawnshop_management.pawnshop_management.patches.v1_0.create_vc_turnover_checklist_workflow import (
	backfill_existing_workflow_states,
	ensure_workflow,
	ensure_workflow_actions,
	ensure_workflow_states,
)


def execute():
	ensure_workflow_states()
	ensure_workflow_actions()
	ensure_workflow()
	backfill_existing_workflow_states()
