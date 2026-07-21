import unittest
from unittest.mock import patch

import frappe

from pawnshop_management.pawnshop_management.doctype.text_blast.text_blast import TextBlast, send_text_blast


class TestTextBlast(unittest.TestCase):
	def test_message_length_uses_160_character_segments(self):
		doc = TextBlast({"doctype": "Text Blast", "message": "x" * 230})
		doc._set_message_length()
		self.assertEqual(doc.message_length, "Characters: 230 / 320\nSMS Segments: 2")

	@patch("pawnshop_management.pawnshop_management.doctype.text_blast.text_blast.frappe.get_doc")
	def test_bulk_sender_rejects_unapproved_document(self, get_doc):
		get_doc.return_value = frappe._dict(workflow_state="For Approval", approved_by=None)
		with self.assertRaises(frappe.ValidationError):
			send_text_blast("TEXT-BLAST-00001")
