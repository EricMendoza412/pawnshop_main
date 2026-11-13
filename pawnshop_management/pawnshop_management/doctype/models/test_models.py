import unittest
from types import SimpleNamespace
from unittest.mock import patch, Mock

import frappe
from pawnshop_management.pawnshop_management.doctype.models import models as pricing


def document(**values):
    doc = object.__new__(pricing.Models)
    doc.__dict__.update({field: None for field in pricing.CONTROLLED + pricing.INPUTS + pricing.OUTPUTS})
    doc._meta = SimpleNamespace(get_table_fields=lambda: [], _table_doctypes={})
    doc.__dict__.update(values)
    return doc


class TestModels(unittest.TestCase):
    def setUp(self):
        for name, value in [('today', '2026-11-13'), ('now_datetime', '2026-11-13 12:00:00')]:
            clock_patch = patch.object(pricing, name, return_value=value)
            clock_patch.start()
            self.addCleanup(clock_patch.stop)
        def throw(message, exc=frappe.ValidationError):
            raise exc(message)
        for name, value in [('throw', throw), ('session', SimpleNamespace(user='proposer@example.com')),
                            ('get_roles', lambda: [pricing.ROLE])]:
            mock = patch.object(pricing.frappe, name, value)
            mock.start()
            self.addCleanup(mock.stop)

    def test_rounding(self):
        self.assertEqual(pricing.calculate_prices(12345, 80), (9900, 8000, 6000))
        self.assertEqual(pricing.calculate_prices(10000, 80), (8000, 6400, 4800))
        self.assertEqual(pricing.calculate_prices(0, 80), (0, 0, 0))

    def test_invalid_values(self):
        for price, percent in [(1, 0), (1, -1), (1, 101), (-1, 80), ('NaN', 80), (1, 'Infinity'), (1, None)]:
            with self.subTest(price=price, percent=percent), self.assertRaises(frappe.ValidationError):
                pricing.calculate_prices(price, percent)

    def test_initial_proposal_does_not_apply_prices(self):
        doc = document(new_max_sell_price=10000, new_max_av_percent=80)
        doc.validate()
        self.assertEqual(doc.maximum, 0)
        self.assertEqual(doc.new_maximum, 8000)
        self.assertEqual(doc.pending_price_change_approval, 1)
        self.assertEqual(doc.proposed_by, 'proposer@example.com')

    def test_existing_proposal_keeps_effective_prices(self):
        old = document(maximum=7000, minimum=5600, defective=4200, has_approved_pricing=1)
        doc = document()
        doc.__dict__.update(old.__dict__)
        doc._doc_before_save = old
        doc.new_max_sell_price, doc.new_max_av_percent = 12000, 80
        doc.validate()
        self.assertEqual(doc.maximum, 7000)
        self.assertEqual(doc.new_maximum, 9600)
        self.assertEqual(doc.maximum_difference, 2600)

    def test_direct_effective_price_and_audit_edits_rejected(self):
        for field in pricing.CONTROLLED:
            doc = document(**{field: 1})
            with self.subTest(field=field), self.assertRaises(frappe.ValidationError):
                doc.validate()

    def test_unrelated_save_preserves_proposal(self):
        old = document(pending_price_change_approval=1, proposed_by='someone@example.com', new_maximum=8000,
                       new_max_sell_price=10000, new_max_av_percent=80)
        doc = document(**old.__dict__)
        doc._doc_before_save = old
        doc.new_maximum = 999999
        doc.validate()
        self.assertEqual(doc.new_maximum, 8000)
        self.assertEqual(doc.proposed_by, 'someone@example.com')

    def test_revision_requires_proposer_even_for_administrator(self):
        old = document(pending_price_change_approval=1, proposed_by='someone@example.com')
        for user in ['proposer@example.com', 'Administrator']:
            pricing.frappe.session.user = user
            doc = document(**old.__dict__)
            doc._doc_before_save = old
            doc.new_max_sell_price, doc.new_max_av_percent = 10000, 80
            with self.assertRaises(frappe.PermissionError):
                doc.validate()

    def test_missing_role_rejected(self):
        with patch.object(pricing.frappe, 'get_roles', return_value=['System Manager']), self.assertRaises(frappe.PermissionError):
            document(new_max_sell_price=100, new_max_av_percent=80).validate()

    def pending(self):
        doc = document(name='test', modified='reviewed-version', proposed_by='proposer@example.com',
                       pending_price_change_approval=1, new_max_sell_price=10000, new_max_av_percent=80)
        doc.check_permission = Mock()
        doc.save = Mock()
        return doc

    def test_self_approval_rejected(self):
        with patch.object(pricing.frappe, 'get_doc', return_value=self.pending()), self.assertRaises(frappe.PermissionError):
            pricing.approve_price_change('test', 'reviewed-version')

    def test_approval_applies_and_clears(self):
        for user in ['reviewer@example.com', 'Administrator']:
            pricing.frappe.session.user = user
            doc = self.pending()
            with patch.object(pricing.frappe, 'get_doc', return_value=doc):
                pricing.approve_price_change('test', 'reviewed-version')
            self.assertEqual((doc.maximum, doc.minimum, doc.defective), (8000, 6400, 4800))
            self.assertEqual(doc.max_sell_price, 10000)
            self.assertEqual(doc.approved_by, user)
            self.assertEqual(doc.has_approved_pricing, 1)
            self.assertEqual(doc.pending_price_change_approval, 0)
            self.assertIsNone(doc.new_max_sell_price)
            doc.save.assert_called_once()

    def test_stale_review_rejected(self):
        with patch.object(pricing.frappe, 'get_doc', return_value=self.pending()), self.assertRaises(frappe.ValidationError):
            pricing.approve_price_change('test', 'stale-version')

    def test_withdrawal_preserves_current_prices(self):
        doc = self.pending()
        doc.maximum = 6000
        with patch.object(pricing.frappe, 'get_doc', return_value=doc):
            pricing.withdraw_price_change('test', 'reviewed-version')
        self.assertEqual(doc.maximum, 6000)
        self.assertEqual(doc.pending_price_change_approval, 0)
        self.assertIsNone(doc.proposed_by)

    def test_other_user_cannot_withdraw(self):
        pricing.frappe.session.user = 'Administrator'
        with patch.object(pricing.frappe, 'get_doc', return_value=self.pending()), self.assertRaises(frappe.PermissionError):
            pricing.withdraw_price_change('test', 'reviewed-version')

    def test_proposer_can_revise_and_timestamp_changes(self):
        old = document(pending_price_change_approval=1, proposed_by='proposer@example.com', proposed_on='earlier',
                       new_max_sell_price=10000, new_max_av_percent=80, maximum=7000)
        doc = document(**old.__dict__)
        doc._doc_before_save = old
        doc.new_max_av_percent = 90
        doc.validate()
        self.assertEqual(doc.new_maximum, 9000)
        self.assertEqual(doc.maximum, 7000)
        self.assertNotEqual(doc.proposed_on, old.proposed_on)

    def test_bulk_reports_partial_results(self):
        db = Mock()
        with patch.object(pricing.frappe, 'db', db, create=True), patch.object(pricing, 'approve_price_change',
                side_effect=[frappe.ValidationError('Changed after review'), 'b']):
            results = pricing.approve_price_changes([{'name': 'a', 'modified': 'old'}, {'name': 'b', 'modified': 'new'}])
        self.assertFalse(results[0]['approved'])
        self.assertTrue(results[1]['approved'])
        db.rollback.assert_called_once_with(save_point='price_approval')

    def test_initial_appraisal_guard(self):
        from pawnshop_management.pawnshop_management.doctype.non_jewelry_items.non_jewelry_items import NonJewelryItems
        item = SimpleNamespace(model='unapproved', get_doc_before_save=lambda: None)
        with patch.object(pricing.frappe, 'db', Mock(), create=True) as db:
            db.get_value.return_value = 0
            with self.assertRaises(frappe.ValidationError):
                NonJewelryItems.validate_approved_model_pricing(item)
            db.get_value.return_value = 1
            NonJewelryItems.validate_approved_model_pricing(item)

    def test_browser_date_serialization_preserves_audit_fields(self):
        from datetime import date, datetime
        old = document(last_srp_update=date(2026, 11, 13),
                       proposed_on=datetime(2026, 11, 13, 10, 30, 15, 123456),
                       approved_on=datetime(2026, 11, 12, 9, 15))
        doc = document(**old.__dict__)
        doc._doc_before_save = old
        doc.last_srp_update = '2026-11-13'
        doc.proposed_on = '2026-11-13 10:30:15.123456'
        doc.approved_on = '2026-11-12 09:15:00'
        doc.new_max_sell_price, doc.new_max_av_percent = 6000, 80
        doc.validate()
        self.assertEqual(doc.new_maximum, 4800)
        self.assertEqual(doc.pending_price_change_approval, 1)

    def test_browser_cannot_change_audit_date(self):
        from datetime import date
        doc = document(last_srp_update='2026-11-14')
        doc._doc_before_save = document(last_srp_update=date(2026, 11, 13))
        with self.assertRaises(frappe.ValidationError):
            doc.validate()
