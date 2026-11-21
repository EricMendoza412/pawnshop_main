import unittest
from unittest.mock import patch, Mock

import frappe
from pawnshop_management.pawnshop_management import jewelry_interest as rates


class Ticket(frappe._dict):
    def get_doc_before_save(self):
        return self.get('_previous')

    def is_new(self):
        return self.get('_previous') is None

    def precision(self, field):
        return 2


def ticket(**values):
    defaults = dict(name='J-1', desired_principal=10000, interest=500, net_proceeds=9500,
                    interest_rate=None, use_promo_interest_rate=0, docstatus=0,
                    branch='Branch A', date_loan_granted='2026-11-21', creation='2026-11-21',
                    flags=frappe._dict())
    defaults.update(values)
    return Ticket(defaults)


class TestJewelryInterest(unittest.TestCase):
    def setUp(self):
        self.settings = frappe._dict(jewelry_interest_rate=5, promo_interest=1, promo_schedule=[
            frappe._dict(branch='Branch A', start_date='2026-11-20', end_date='2026-11-24')])
        self.api = patch.object(rates, 'frappe').start()
        self.api.get_single.return_value = self.settings
        self.api.session.user = 'staff@example.com'
        self.api.throw.side_effect = ValueError
        patch.object(rates, 'nowdate', return_value='2026-11-21').start()
        self.addCleanup(patch.stopall)

    def test_inference_and_no_financial_changes(self):
        doc = ticket()
        self.assertEqual(rates.resolve_rate(doc, persist=True), 5)
        self.assertEqual((doc.interest, doc.desired_principal, doc.net_proceeds), (500, 10000, 9500))
        self.api.db.set_value.assert_called_once_with(rates.TICKET, 'J-1', 'interest_rate', 5.0, update_modified=False)

    def test_rounding_and_invalid_historical_values(self):
        self.assertEqual(rates.inferred_rate(ticket(desired_principal=333.33, interest=16.67)), 5)
        for principal, interest in [(0, 500), (100, 0), (-1, 1), (100, 101), (float('inf'), 5)]:
            with self.subTest(principal=principal, interest=interest), self.assertRaises(ValueError):
                rates.resolve_rate(ticket(desired_principal=principal, interest=interest))
        self.api.get_single.assert_not_called()

    def test_saved_rate_wins_over_settings(self):
        self.assertEqual(rates.resolve_rate(ticket(interest_rate=1)), 1)
        self.api.get_single.assert_not_called()

    def test_schedule_boundaries_and_issuing_branch(self):
        for day in ('2026-11-20', '2026-11-24'):
            with patch.object(rates, 'nowdate', return_value=day):
                self.assertTrue(rates.promo_eligible(self.settings, 'Branch A', day))
        self.assertFalse(rates.promo_eligible(self.settings, 'Branch B', '2026-11-21'))
        self.assertFalse(rates.promo_eligible(self.settings, 'Branch A', '2026-11-20'))
        self.assertFalse(rates.promo_eligible(self.settings, 'Branch A', '2026-11-21', '2026-11-20'))

    def test_invalid_and_overlapping_schedule(self):
        rates.validate_promo_settings(self.settings)
        self.settings.promo_schedule.append(frappe._dict(branch='Branch A', start_date='2026-11-24', end_date='2026-11-25'))
        with self.assertRaises(ValueError):
            rates.validate_promo_settings(self.settings)

    def test_new_regular_and_promo(self):
        for promo, rate in [(0, 5), (1, 1)]:
            doc = ticket(use_promo_interest_rate=promo, interest_rate=99)
            rates.apply_ticket_rate(doc)
            self.assertEqual(doc.interest_rate, rate)
            self.assertEqual(doc.interest, 10000 * rate / 100)
            self.assertEqual(doc.net_proceeds, 10000 - doc.interest)

    def test_initial_submission_rechecks_day_even_if_active(self):
        doc = ticket(use_promo_interest_rate=1, docstatus=1, workflow_state='Active',
                     creation='2026-11-20', _previous=ticket(workflow_state='Active', interest_rate=1))
        with self.assertRaises(ValueError):
            rates.apply_ticket_rate(doc)

    def test_renewal_inherits_outside_schedule(self):
        source = ticket(interest_rate=1, use_promo_interest_rate=1, docstatus=1)
        self.api.get_doc.return_value = source
        doc = ticket(date_loan_granted='2026-12-21', flags=frappe._dict(interest_source_ticket='J-1'), desired_principal=8000)
        rates.apply_ticket_rate(doc)
        self.assertEqual((doc.interest_rate, doc.interest, doc.use_promo_interest_rate), (1, 80, 1))

    def test_only_administrator_can_override_on_amendment(self):
        self.api.get_doc.return_value = ticket(interest_rate=1, use_promo_interest_rate=1)
        for user, expected in [('staff@example.com', 1), ('Administrator', 2)]:
            self.api.session.user = user
            doc = ticket(amended_from='J-1', interest_rate=2, creation='2025-01-01')
            rates.apply_ticket_rate(doc)
            self.assertEqual(doc.interest_rate, expected)
            self.assertEqual(doc.interest, expected * 100)

    def test_administrator_resolves_unknown_amendment(self):
        self.api.get_doc.return_value = ticket(desired_principal=0, interest=0)
        self.api.session.user = 'Administrator'
        doc = ticket(amended_from='J-1', interest_rate=5)
        rates.apply_ticket_rate(doc)
        self.assertEqual(doc.interest_rate, 5)

    def test_finalized_amounts_preserved_and_edits_rejected(self):
        old = ticket(docstatus=1, workflow_state='Collected')
        doc = ticket(docstatus=1, _previous=old, workflow_state='Returned')
        rates.apply_ticket_rate(doc)
        self.assertEqual((doc.interest_rate, doc.interest, doc.net_proceeds), (5, 500, 9500))
        doc = ticket(docstatus=1, _previous=ticket(docstatus=1, interest_rate=1), interest_rate=2)
        with self.assertRaises(ValueError):
            rates.apply_ticket_rate(doc)

    def test_all_receipt_types_resolve_rate(self):
        self.api.get_doc.return_value = ticket(interest_rate=1, interest=100)
        for kind in ('Renewal', 'Renewal w/ Amortization', 'Amortization', 'Redemption', 'Interest Payment'):
            doc = ticket(pawn_ticket_type=rates.TICKET, pawn_ticket_no='J-1', transaction_type=kind,
                         principal_amount=10000, additional_amortization=2000, advance_interest=80)
            rates.prepare_receipt(doc)
        doc.advance_interest = 400
        doc.transaction_type = 'Amortization'
        with self.assertRaises(ValueError):
            rates.prepare_receipt(doc)

    def test_unresolved_ticket_blocks_financial_processing(self):
        self.api.get_doc.return_value = ticket(desired_principal=0)
        with self.assertRaises(ValueError):
            rates.prepare_receipt(ticket(pawn_ticket_type=rates.TICKET, pawn_ticket_no='J-1', transaction_type='Redemption'))

    def test_backfill_limits_statuses_preserves_amounts_and_logs_exceptions(self):
        from pawnshop_management.pawnshop_management.patches.v1_0 import backfill_jewelry_interest_rates as migration
        good, bad = ticket(), ticket(name='J-2', desired_principal=0)
        with patch.object(migration, 'frappe') as api:
            api.get_all.return_value = [frappe._dict(name='J-1'), frappe._dict(name='J-2')]
            api.get_doc.side_effect = [good, bad]
            migration.execute()
            self.assertEqual(api.get_all.call_args.kwargs['filters'], {
                'workflow_state': ['in', ['Active', 'Expired', 'Returned']], 'docstatus': ['!=', 2]})
            api.log_error.assert_called_once()
            self.assertIn('J-2', api.log_error.call_args.args[0])
            self.assertEqual((good.desired_principal, good.interest, good.net_proceeds), (10000, 500, 9500))
            self.assertEqual(good.interest_rate, 5)

    def test_stale_or_excessive_amortization_rejected(self):
        self.api.get_doc.return_value = ticket(interest_rate=1)
        for principal, amort in [(9000, 1000), (10000, 11000)]:
            with self.subTest(principal=principal, amort=amort), self.assertRaises(ValueError):
                rates.prepare_receipt(ticket(pawn_ticket_type=rates.TICKET, pawn_ticket_no='J-1',
                    transaction_type='Amortization', principal_amount=principal,
                    additional_amortization=amort, advance_interest=0))

    def test_invalid_administrator_override_is_rejected(self):
        self.api.session.user = 'Administrator'
        self.api.get_doc.return_value = ticket(interest_rate=5)
        for value in (-1, 101, float('nan')):
            with self.subTest(value=value), self.assertRaises(ValueError):
                rates.apply_ticket_rate(ticket(amended_from='J-1', interest_rate=value))

    def test_promo_discount_rejected_even_when_selection_is_none(self):
        self.api.get_doc.return_value = ticket(interest_rate=1, use_promo_interest_rate=1)
        for selection, discount in [('3%', 300), ('4%', 400), ('None', 100), ('3%', 0)]:
            with self.subTest(selection=selection, discount=discount), self.assertRaises(ValueError):
                rates.prepare_receipt(ticket(pawn_ticket_type=rates.TICKET, pawn_ticket_no='J-1',
                    transaction_type='Redemption', principal_amount=10000,
                    other_discount_st=selection, discount=discount))

    def test_promo_redemption_without_discount_and_regular_discount_allowed(self):
        for promo, selection, discount in [(1, 'None', 0), (0, '4%', 400)]:
            self.api.get_doc.return_value = ticket(interest_rate=1 if promo else 5, use_promo_interest_rate=promo)
            rates.prepare_receipt(ticket(pawn_ticket_type=rates.TICKET, pawn_ticket_no='J-1',
                transaction_type='Redemption', principal_amount=10000,
                other_discount_st=selection, discount=discount))

    def test_early_redemption_calculation_excludes_promo_only(self):
        from pawnshop_management.pawnshop_management.doctype.provisional_receipt import provisional_receipt as receipts
        for promo in (0, 1):
            with patch.object(receipts, 'frappe') as api, patch.object(receipts, 'resolve_rate'):
                source = ticket(use_promo_interest_rate=promo)
                source.check_permission = Mock()
                api.get_doc.return_value = source
                api.get_value.side_effect = ['1990-01-01', 'Holidays']
                api.get_all.return_value = []
                result = receipts.calculate_interest('2026-11-21', '2026-11-21', '2026-12-21',
                    '2027-03-21', 500, 'J-1', rates.TICKET, 'Branch A')
                self.assertEqual(result['st_rate'], 0 if promo else 4)
                self.assertEqual(result['promo_loan'], bool(promo))
