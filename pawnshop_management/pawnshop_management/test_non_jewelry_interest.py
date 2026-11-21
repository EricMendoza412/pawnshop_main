import unittest
from unittest.mock import patch
import frappe
from pawnshop_management.pawnshop_management import non_jewelry_interest as rates
from pawnshop_management.pawnshop_management.test_jewelry_interest import ticket


class TestNonJewelryInterest(unittest.TestCase):
    def setUp(self):
        self.api = patch.object(rates, 'frappe').start()
        self.addCleanup(patch.stopall)
        self.api.throw.side_effect = ValueError
        self.api.get_single.return_value = frappe._dict(gadget_interest_rate=10)

    def test_server_corrects_stale_or_zero_amounts(self):
        for interest, net in [(0, 0), (100, 900)]:
            doc = ticket(desired_principal=5000, interest=interest, net_proceeds=net)
            rates.apply_ticket_rate(doc)
            self.assertEqual((doc.interest_rate, doc.interest, doc.net_proceeds), (10, 500, 4500))

    def test_draft_keeps_assigned_rate_after_settings_change(self):
        doc = ticket(desired_principal=5000, _previous=ticket(interest_rate=7))
        rates.apply_ticket_rate(doc)
        self.assertEqual((doc.interest_rate, doc.interest, doc.net_proceeds), (7, 350, 4650))

    def test_amendments_renewals_and_replacements_keep_source_rate(self):
        self.api.get_doc.return_value = ticket(interest_rate=7)
        for extra in [dict(amended_from='J-1'), dict(flags=frappe._dict(interest_source_ticket='J-1'))]:
            doc = ticket(desired_principal=5000, interest_rate=99, **extra)
            rates.apply_ticket_rate(doc)
            self.assertEqual(doc.interest_rate, 7)
            self.assertEqual(doc.interest, 350)

    def test_invalid_numbers_rejected(self):
        for value in (None, '', 'invalid', 0, -1, float('nan'), float('inf')):
            with self.subTest(value=value), self.assertRaises(ValueError):
                rates.apply_ticket_rate(ticket(desired_principal=value))
        self.api.get_single.return_value.gadget_interest_rate = 0
        with self.assertRaises(ValueError):
            rates.apply_ticket_rate(ticket())

    def test_finalized_ticket_unchanged(self):
        doc = ticket(docstatus=1, _previous=ticket(docstatus=1), interest=500, net_proceeds=9500)
        rates.apply_ticket_rate(doc)
        self.assertEqual((doc.interest, doc.net_proceeds), (500, 9500))
        self.api.get_single.assert_not_called()

    def test_legacy_source_inference_and_unknown_rate(self):
        self.assertEqual(rates.historical_rate(ticket()), 5)
        with self.assertRaises(ValueError):
            rates.historical_rate(ticket(desired_principal=0, interest=0))
