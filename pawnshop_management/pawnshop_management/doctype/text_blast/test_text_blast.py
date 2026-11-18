import unittest
from datetime import date
from unittest.mock import patch, Mock
from types import SimpleNamespace
from .selection import sms_metrics, registration_matches, fx_buying_trackers
from . import text_blast as module

from pawnshop_management.pawnshop_management.doctype.text_blast.text_blast import (
	_get_batch_ranges,
	_get_message_length_display,
	_get_next_client_message_id,
)


class TestTextBlast(unittest.TestCase):
	def test_message_length_includes_campaign_estimate(self):
		self.assertIn("3 (SMS Segments) x 10 (Recipients) = 30 (Estimated total SMS Segments)", _get_message_length_display("x" * 307, 10))

	def test_encoding_boundaries(self):
		for message, encoding, units, segments in (
			("", "GSM", 0, 0), ("x" * 160, "GSM", 160, 1),
			("x" * 161, "GSM", 161, 2), ("x" * 306, "GSM", 306, 2),
			("x" * 307, "GSM", 307, 3), ("^" * 80, "GSM", 160, 1),
			("€" * 81, "GSM", 162, 2), ("漢" * 70, "Unicode", 70, 1),
			("漢" * 71, "Unicode", 71, 2), ("漢" * 135, "Unicode", 135, 3),
			("😀" * 35, "Unicode", 70, 1), ("😀" * 36, "Unicode", 72, 2),
		):
			with self.subTest(message=message):
				result = sms_metrics(message)
				self.assertEqual((result["encoding"], result["units"], result["segments"]), (encoding, units, segments))
		self.assertEqual(sms_metrics("Hello ’😀’")["unsupported"], ["’", "😀"])

	def test_registration_exact_dates_and_legacy_year(self):
		start, end = date(2026, 7, 1), date(2026, 7, 31)
		for tracker, expected in (("5.1-40-07012026", True), ("5.1-40-07312026", True),
			("5.1-40-08012026", False), ("6-40-362026", True),
			("6-40-2025", False), ("6-40-02302026", False), ("bad", False)):
			self.assertEqual(registration_matches(tracker, start, end), expected)

	def test_fx_buying_voids_dates_and_tracker_extraction(self):
		def row(day, customer, void=None):
			return ["BRANCH", day, "1", customer] + [""] * 9 + [void or ""]
		rows = [row("2026-07-01 00:00:00", "A~Name~Mobile"),
			row("2026-07-31 23:59:59", "B"), row("2026-08-01", "C"),
			row("2026-07-02", "D", "voided"), row("2026-07-02", "A"),
			row("invalid", "E"), [], row(46204, "F")]
		self.assertEqual(fx_buying_trackers(rows, date(2026, 7, 1), date(2026, 7, 31)), {"A", "B", "F"})

	def test_transaction_validity_filters(self):
		with patch.object(module.frappe, "get_all", return_value=["customer"]) as query:
			start, end = date(2026, 1, 1), date(2026, 12, 31)
			module._transaction_customers("Pawn ticket date range", start, end)
			self.assertEqual(query.call_count, 2)
			for call in query.call_args_list:
				self.assertEqual(call.kwargs["filters"]["workflow_state"], ["not in", ["Rejected", "Draft"]])
			module._transaction_customers("Agreement to sell date range", start, end)
			self.assertEqual(query.call_args.kwargs["filters"]["workflow_state"], ["in", ["Active", "Pulled Out"]])
			module._transaction_customers("FX selling date range", start, end)
			self.assertEqual(query.call_args.kwargs["filters"]["docstatus"], 1)
			module._transaction_customers("Subastado sales date range", start, end)
			self.assertEqual(set(query.call_args.kwargs["filters"]), {"date_bought_or_returned"})

	def test_missing_filter_and_reversed_dates_rejected(self):
		with patch.object(module.frappe, "throw", side_effect=ValueError):
			with self.assertRaises(ValueError):
				module._validate_selection("Branch", None, None, None)
			with self.assertRaises(ValueError):
				module._validate_selection("Branch", "Registered date range", "2026-02-01", "2026-01-01")

	def test_filter_changes_locked_after_approval(self):
		previous = module.frappe._dict(workflow_state="For Approval", message="Hello", recipient_options="Branch",
			recipient_filter="Registered date range", from_date="2026-01-01", to_date="2026-12-31", recipient_list=[])
		doc = SimpleNamespace(**dict(previous))
		doc.get = lambda field: getattr(doc, field, None)
		doc.get_doc_before_save = lambda: previous
		module.TextBlast._prevent_approved_content_changes(doc)
		doc.from_date = "2026-02-01"
		with patch.object(module.frappe, "throw", side_effect=ValueError):
			with self.assertRaises(ValueError):
				module.TextBlast._prevent_approved_content_changes(doc)


	def test_approval_accepts_database_dates_and_browser_date_strings(self):
		previous = module.frappe._dict(workflow_state="For Approval", message="Hello", recipient_options="Branch",
			recipient_filter="Registered date range", from_date=date(2026, 1, 1),
			to_date=date(2026, 12, 31), recipient_list=[])
		doc = SimpleNamespace(**dict(previous))
		doc.workflow_state = "Sent"
		doc.from_date, doc.to_date = "2026-01-01", "2026-12-31"
		doc.get = lambda field: getattr(doc, field, None)
		doc.get_doc_before_save = lambda: previous
		with patch.object(module.frappe, "throw", side_effect=ValueError):
			module.TextBlast._prevent_approved_content_changes(doc)
			# Representation normalization must not permit actual content changes.
			for field, value in (("from_date", "2026-01-02"), ("to_date", "2026-12-30"),
				("message", "Changed"), ("recipient_options", "Other Branch"),
				("recipient_filter", "FX buying date range"),
				("recipient_list", [module.frappe._dict(contact_name="Other", mobile_number="09123456789")])):
				with self.subTest(field=field):
					original = getattr(doc, field)
					setattr(doc, field, value)
					with self.assertRaises(ValueError):
						module.TextBlast._prevent_approved_content_changes(doc)
					setattr(doc, field, original)

	def test_approval_accepts_empty_optional_filters(self):
		previous = module.frappe._dict(workflow_state="For Approval", message="Hello", recipient_options=None,
			recipient_filter=None, from_date=None, to_date=None, recipient_list=[])
		doc = SimpleNamespace(**dict(previous))
		doc.recipient_options = doc.recipient_filter = doc.from_date = doc.to_date = ""
		doc.get = lambda field: getattr(doc, field, None)
		doc.get_doc_before_save = lambda: previous
		with patch.object(module.frappe, "throw", side_effect=ValueError):
			module.TextBlast._prevent_approved_content_changes(doc)

	def test_branch_customers_intersect_transactions_and_deduplicate(self):
		customers = [module.frappe._dict(name="1.1-1-01012026", customer_primary_contact="C1"),
			module.frappe._dict(name="1.1-2-01012026", customer_primary_contact="C2"),
			module.frappe._dict(name="1.1-3-01012026", customer_primary_contact="C3"),
			module.frappe._dict(name="2.1-4-01012026", customer_primary_contact="C4")]
		contacts = [module.frappe._dict(name="C1", mobile_no="09123456789"),
			module.frappe._dict(name="C2", mobile_no="09123456789")]
		def query(doctype, **kwargs):
			return {"Customer": customers, "Dynamic Link": [], "Contact": contacts}[doctype]
		with patch.object(module.frappe, "has_permission"), patch.object(module.frappe, "db", Mock()) as db, \
			patch.object(module.frappe, "get_all", side_effect=query), \
			patch.object(module, "_transaction_customers", return_value={c.name for c in customers[:2]}):
			db.get_value.return_value = "1"
			result = module.get_branch_recipients("Registered branch", "FX selling date range", "2026-01-01", "2026-12-31")
			self.assertEqual(result, [{"contact_name": "C1", "mobile_number": "09123456789"}])

	def test_fx_read_failure_is_not_an_empty_audience(self):
		path = "pawnshop_management.pawnshop_management.doctype.fx_selling.fx_selling._sheet_service"
		with patch(path, side_effect=RuntimeError("unavailable")), \
			patch.object(module.frappe, "get_single"), patch.object(module.frappe, "get_traceback"), \
			patch.object(module.frappe, "log_error"), patch.object(module.frappe, "throw", side_effect=ValueError):
			with self.assertRaises(ValueError):
				module._fx_buying_customers(date(2026, 1, 1), date(2026, 12, 31))

	def test_eleven_thousand_recipients_create_44_batches(self):
		batches = _get_batch_ranges(11000, 250)
		self.assertEqual(len(batches), 44)
		self.assertEqual(batches[0], (1, 1, 250))
		self.assertEqual(batches[-1], (44, 10751, 11000))

	def test_retry_client_message_id_is_deterministic(self):
		self.assertEqual(_get_next_client_message_id("TEXT-BLAST-00001", 7, 1), "TEXT-BLAST-TEXT-BLAST-00001-7")
		self.assertEqual(_get_next_client_message_id("TEXT-BLAST-00001", 7, 3), "TEXT-BLAST-TEXT-BLAST-00001-7-R3")
