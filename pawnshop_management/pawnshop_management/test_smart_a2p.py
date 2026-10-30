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


class TestNonJewelryMaturitySMS(unittest.TestCase):
	def test_maturity_sender_uses_customer_and_maturity_purpose(self):
		for doctype in smart_a2p.PAWN_TICKET_DOCTYPES:
			with self.subTest(doctype=doctype), \
				patch.object(smart_a2p, 'require_vault_custodian_access') as access, \
				patch.object(smart_a2p, 'get_reference_branch', return_value='TEST BRANCH'), \
				patch.object(smart_a2p, '_validate_pawn_ticket_sms_workflow_state') as validate, \
				patch.object(smart_a2p, '_get_pawn_ticket_customer_sms_details', return_value=('TEST PHONE', 'MATURITY MESSAGE')) as details, \
				patch.object(smart_a2p, '_send_administrator_test_sms') as send:
				smart_a2p.send_administrator_test_sms(doctype, 'TEST PT')
				access.assert_called_once_with(branch='TEST BRANCH')
				validate.assert_called_once_with(doctype, 'TEST PT')
				details.assert_called_once_with(doctype, 'TEST PT', 'Maturity')
				self.assertEqual(send.call_args.kwargs['sms_purpose'], 'Maturity')
				self.assertEqual(send.call_args.kwargs['destination'], 'TEST PHONE')
				self.assertEqual(send.call_args.kwargs['text'], 'MATURITY MESSAGE')

	def test_daily_job_processes_both_dates_for_both_types(self):
		from types import SimpleNamespace
		with patch.object(smart_a2p.frappe, 'session', SimpleNamespace(user='TEST USER')), \
			patch.object(smart_a2p.frappe, 'set_user') as set_user, \
			patch.object(smart_a2p, '_get_pawn_tickets_for_daily_sms', return_value=[SimpleNamespace(name='TEST PT')]) as query, \
			patch.object(smart_a2p, '_send_daily_pawn_ticket_sms', return_value=True) as send, \
			patch.object(smart_a2p, '_send_daily_text_blast_status_sms', return_value=True):
			result = smart_a2p.send_daily_pawn_ticket_sms_notifications()
			self.assertEqual(result['maturity_sent'], 2)
			self.assertEqual(result['expiry_sent'], 2)
			self.assertEqual(send.call_count, 4)
			for doctype in smart_a2p.PAWN_TICKET_DOCTYPES:
				query.assert_any_call(doctype, 'maturity_date', 'texted_upon_maturity')
				query.assert_any_call(doctype, 'expiry_date', 'texted_upon_expiry')
			set_user.assert_called_with('TEST USER')

	def test_delivered_maturity_does_not_mark_expiry(self):
		from unittest.mock import Mock
		from frappe import _dict
		for purpose, field in [('Maturity', 'texted_upon_maturity'), ('Expiry', 'texted_upon_expiry')]:
			with self.subTest(purpose=purpose), patch.object(smart_a2p.frappe, 'db', Mock()) as db:
				db.exists.return_value = True
				log = _dict(reference_doctype='Pawn Ticket Non Jewelry', reference_name='TEST PT', sms_purpose=purpose)
				smart_a2p._mark_pawn_ticket_texted_if_delivered(log)
				db.set_value.assert_called_once_with('Pawn Ticket Non Jewelry', 'TEST PT', field, 1, update_modified=False)
