import unittest
from unittest.mock import patch

from pawnshop_management.pawnshop_management import smart_a2p


class TestDailyPawnTicketSMSQuery(unittest.TestCase):
	@patch.object(smart_a2p.frappe, "get_all")
	@patch.object(smart_a2p, "add_days", return_value="2026-07-24")
	@patch.object(smart_a2p, "today", return_value="2026-07-22")
	def test_daily_sms_query_includes_today_and_next_two_days(
		self,
		mock_today,
		mock_add_days,
		mock_get_all,
	):
		mock_get_all.return_value = []

		result = smart_a2p._get_pawn_tickets_for_daily_sms(
			"Pawn Ticket Jewelry",
			"maturity_date",
			"texted_upon_maturity",
		)

		self.assertEqual(result, [])
		mock_add_days.assert_called_once_with("2026-07-22", 2)
		mock_get_all.assert_called_once_with(
			"Pawn Ticket Jewelry",
			filters={
				"maturity_date": ["between", ["2026-07-22", "2026-07-24"]],
				"texted_upon_maturity": 0,
				"workflow_state": ["in", list(smart_a2p.PAWN_TICKET_SMS_WORKFLOW_STATES)],
			},
			fields=["name"],
			order_by="name asc",
		)

	@patch.object(smart_a2p.frappe, "get_all")
	@patch.object(smart_a2p, "add_days", return_value="2026-07-24")
	@patch.object(smart_a2p, "today", return_value="2026-07-22")
	def test_daily_sms_query_preserves_expiry_and_texted_filters(
		self,
		mock_today,
		mock_add_days,
		mock_get_all,
	):
		mock_get_all.return_value = []

		smart_a2p._get_pawn_tickets_for_daily_sms(
			"Pawn Ticket Non Jewelry",
			"expiry_date",
			"texted_upon_expiry",
		)

		filters = mock_get_all.call_args.kwargs["filters"]
		self.assertEqual(filters["expiry_date"], ["between", ["2026-07-22", "2026-07-24"]])
		self.assertEqual(filters["texted_upon_expiry"], 0)
		self.assertEqual(
			set(filters["workflow_state"][1]),
			smart_a2p.PAWN_TICKET_SMS_WORKFLOW_STATES,
		)
