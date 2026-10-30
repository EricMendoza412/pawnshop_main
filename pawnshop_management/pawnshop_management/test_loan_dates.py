import unittest
from datetime import date
from types import SimpleNamespace
from unittest.mock import Mock, patch

import frappe

from pawnshop_management.pawnshop_management import loan_dates
from pawnshop_management.pawnshop_management.patches.v1_0 import set_loan_periods


class TestLoanDates(unittest.TestCase):
    def setUp(self):
        self.settings = SimpleNamespace(**loan_dates.LOAN_PERIOD_DEFAULTS)
        self.settings_patch = patch.object(loan_dates.frappe, 'get_single', return_value=self.settings)
        self.get_settings = self.settings_patch.start()
        self.addCleanup(self.settings_patch.stop)
        throw_patch = patch.object(loan_dates.frappe, 'throw', side_effect=ValueError)
        throw_patch.start()
        self.addCleanup(throw_patch.stop)

    def test_defaults_across_year_boundary(self):
        for kind, expiry in [('Jewelry', '2027-02-24'), ('Non Jewelry', '2026-11-26')]:
            self.assertEqual(
                loan_dates.calculate_pawn_ticket_dates('Pawn Ticket ' + kind, '2026-10-27'),
                {'maturity_date': '2026-11-26', 'expiry_date': expiry},
            )

    def test_custom_periods_and_leap_year(self):
        self.settings.jewelry_maturity_days = 1
        self.settings.jewelry_expiry_days = 2
        self.settings.non_jewelry_maturity_days = 5
        self.settings.non_jewelry_expiry_days = 10
        self.assertEqual(loan_dates.calculate_pawn_ticket_dates('Pawn Ticket Jewelry', '2024-02-28'),
                         {'maturity_date': '2024-02-29', 'expiry_date': '2024-03-01'})
        self.assertEqual(loan_dates.calculate_pawn_ticket_dates('Pawn Ticket Non Jewelry', '2024-02-28'),
                         {'maturity_date': '2024-03-04', 'expiry_date': '2024-03-09'})

    def test_invalid_periods(self):
        for field in loan_dates.LOAN_PERIOD_DEFAULTS:
            for value in (None, '', 0, -1, 1.5, 'bad'):
                with self.subTest(field=field, value=value):
                    settings = SimpleNamespace(**loan_dates.LOAN_PERIOD_DEFAULTS)
                    setattr(settings, field, value)
                    with self.assertRaises(ValueError):
                        loan_dates.validate_loan_periods(settings)
        for prefix in loan_dates.TICKET_PREFIXES.values():
            settings = SimpleNamespace(**loan_dates.LOAN_PERIOD_DEFAULTS)
            setattr(settings, prefix + '_expiry_days', 29)
            with self.assertRaises(ValueError):
                loan_dates.validate_loan_periods(settings)

    def ticket(self, previous=None):
        doc = Mock()
        doc.doctype = 'Pawn Ticket Jewelry'
        doc.date_loan_granted = '2026-10-27'
        doc.flags = frappe._dict()
        doc.get.return_value = None
        doc.get_doc_before_save.return_value = previous
        return doc

    def test_new_ticket_and_changed_loan_date_use_current_terms(self):
        self.settings.jewelry_expiry_days = 60
        for previous in (None, SimpleNamespace(date_loan_granted='2026-10-26')):
            doc = self.ticket(previous)
            loan_dates.set_pawn_ticket_dates(doc)
            doc.update.assert_called_once_with({'maturity_date': '2026-11-26', 'expiry_date': '2026-12-26'})

    def test_existing_ticket_keeps_dates_after_settings_change(self):
        previous = SimpleNamespace(date_loan_granted=date(2026, 10, 27),
                                   maturity_date='2026-11-26', expiry_date='2027-02-24')
        doc = self.ticket(previous)
        self.settings.jewelry_expiry_days = 60
        loan_dates.set_pawn_ticket_dates(doc)
        self.assertEqual(doc.expiry_date, previous.expiry_date)
        self.assertEqual(doc.maturity_date, previous.maturity_date)
        self.get_settings.assert_not_called()
        doc.update.assert_not_called()

    def test_paper_jam_preserves_copied_dates(self):
        doc = self.ticket()
        doc.flags.preserve_loan_dates = True
        loan_dates.set_pawn_ticket_dates(doc)
        doc.update.assert_not_called()
        self.get_settings.assert_not_called()

    def test_amendment_preserves_original_dates(self):
        doc = self.ticket()
        doc.get.return_value = 'ORIGINAL'
        doc.amended_from = 'ORIGINAL'
        previous = SimpleNamespace(date_loan_granted='2026-10-27',
                                   maturity_date='2026-11-26', expiry_date='2027-02-24')
        with patch.object(frappe, 'get_doc', return_value=previous):
            loan_dates.set_pawn_ticket_dates(doc)
        self.assertEqual(doc.expiry_date, previous.expiry_date)
        doc.update.assert_not_called()

    def test_migration_preserves_existing_values(self):
        with patch.object(set_loan_periods, 'frappe') as mocked:
            mocked.db.get_value.side_effect = [None, '', '45', '90']
            set_loan_periods.execute()
            self.assertEqual(mocked.db.set_single_value.call_count, 2)
            mocked.db.set_single_value.assert_any_call('Pawnshop Management Settings', 'jewelry_maturity_days', 30)
            mocked.db.set_single_value.assert_any_call('Pawnshop Management Settings', 'jewelry_expiry_days', 120)

    def test_renewal_uses_receipt_date_and_current_terms(self):
        from pawnshop_management.pawnshop_management.doctype.provisional_receipt.provisional_receipt import ProvisionalReceipt

        for kind in ('Jewelry', 'Non Jewelry'):
            for transaction in ('Renewal', 'Renewal w/ Amortization'):
                with self.subTest(kind=kind, transaction=transaction):
                    ticket_type = 'Pawn Ticket ' + kind
                    prefix = loan_dates.TICKET_PREFIXES[ticket_type]
                    setattr(self.settings, prefix + '_maturity_days', 10)
                    setattr(self.settings, prefix + '_expiry_days', 40)
                    previous = frappe._dict(jewelry_items=[], non_jewelry_items=[], desired_principal=1000)
                    new = self.ticket()
                    new.doctype = ticket_type
                    new.docstatus = 1
                    new.update.side_effect = lambda values: [setattr(new, key, value) for key, value in values.items()]
                    receipt = frappe._dict(doctype='Provisional Receipt', name='TEST',
                                           pawn_ticket_type=ticket_type, pawn_ticket_no='OLD',
                                           new_pawn_ticket_no='NEW', transaction_type=transaction,
                                           date_issued='2026-12-25', additional_amortization=100, advance_interest=70)
                    with patch.object(frappe, 'db', Mock()) as db, \
                         patch.object(frappe, 'get_doc', return_value=previous), \
                         patch.object(frappe, 'new_doc', return_value=new), \
                         patch('pawnshop_management.pawnshop_management.doctype.provisional_receipt.provisional_receipt.today', return_value='2026-12-25'):
                        db.get_value.return_value = None
                        ProvisionalReceipt.on_submit(receipt)
                    self.assertEqual(new.date_loan_granted, '2026-12-25')
                    self.assertEqual(new.maturity_date, '2027-01-04')
                    self.assertEqual(new.expiry_date, '2027-02-03')
                    new.save.assert_called_once()
                    new.submit.assert_called_once()
