import unittest

from pawnshop_management.pawnshop_management.doctype.text_blast.text_blast import (
	_get_batch_ranges,
	_get_message_length_display,
	_get_next_client_message_id,
)


class TestTextBlast(unittest.TestCase):
	def test_message_length_uses_160_character_segments(self):
		self.assertEqual(_get_message_length_display("x" * 230), "Characters: 230 / 320\nSMS Segments: 2")

	def test_eleven_thousand_recipients_create_44_batches(self):
		batches = _get_batch_ranges(11000, 250)
		self.assertEqual(len(batches), 44)
		self.assertEqual(batches[0], (1, 1, 250))
		self.assertEqual(batches[-1], (44, 10751, 11000))

	def test_retry_client_message_id_is_deterministic(self):
		self.assertEqual(_get_next_client_message_id("TEXT-BLAST-00001", 7, 1), "TEXT-BLAST-TEXT-BLAST-00001-7")
		self.assertEqual(_get_next_client_message_id("TEXT-BLAST-00001", 7, 3), "TEXT-BLAST-TEXT-BLAST-00001-7-R3")
