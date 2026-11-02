import importlib.util
import unittest
from datetime import date
from pathlib import Path

path = Path(__file__).resolve().parents[1] / 'skills/pjs-find-empty-legs/scripts/search_empty_legs.py'
spec = importlib.util.spec_from_file_location('empty_legs', path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def flight(id='one', **overrides):
    row = dict(id=id, **{'from': 'TPA', 'to': 'TEB'}, date='2026-11-04', aircraft='Example aircraft',
               capacity=8, price=12000, currency='USD', url=f'https://villiers.ai/empty-legs/{id}?id=ZBCS78')
    row.update(overrides)
    return row


class SearchTests(unittest.TestCase):
    def query(self, rows, **kwargs):
        return module.search(rows, as_of=date(2026, 11, 2), **kwargs)

    def test_direction_is_not_reversed(self):
        result = self.query([flight(), flight('return', **{'from':'TEB','to':'TPA'})], origins={'TPA'}, destinations={'TEB'})
        self.assertEqual([r['id'] for r in result['matches']], ['one'])

    def test_dates_are_inclusive_and_past_excluded(self):
        rows=[flight('past',date='2026-11-01'), flight('start',date='2026-11-03'), flight('end',date='2026-11-05'), flight('after',date='2026-11-06')]
        result=self.query(rows,date_from=date(2026,11,3),date_to=date(2026,11,5))
        self.assertEqual([r['id'] for r in result['matches']],['start','end'])

    def test_same_day_requires_time_confirmation(self):
        self.assertTrue(self.query([flight(date='2026-11-02')])['matches'][0]['same_day_time_unverified'])

    def test_capacity_conflict_and_unknown_are_different(self):
        result=self.query([flight('small',capacity=3),flight('unknown',capacity=None),flight('fits',capacity=4)],passengers=4)
        self.assertEqual([r['id'] for r in result['matches']],['fits'])
        self.assertEqual(result['needs_confirmation'][0]['filter_uncertainties'],['capacity_unknown'])

    def test_price_filter_requires_currency(self):
        with self.assertRaises(ValueError): self.query([flight()],max_price=15000)

    def test_different_currencies_not_budget_equivalent(self):
        result=self.query([flight('usd'),flight('eur',price=1000,currency='EUR')],max_price=15000,currency='USD')
        self.assertEqual([r['id'] for r in result['matches']],['usd'])

    def test_unknown_price_not_zero(self):
        result=self.query([flight(price=None)],max_price=15000,currency='USD')
        self.assertEqual(result['match_count'],0)
        self.assertEqual(result['needs_confirmation_count'],1)

    def test_unknown_currency_not_compared_numerically(self):
        result=self.query([flight(price=200000,currency=None)],max_price=15000,currency='USD')
        self.assertEqual(result['needs_confirmation_count'],1)

    def test_zero_nan_bool_prices_are_unknown(self):
        result=self.query([flight(str(i),price=p) for i,p in enumerate([0,float('nan'),True])],max_price=15000,currency='USD')
        self.assertEqual(result['match_count'],0)
        self.assertEqual(result['needs_confirmation_count'],3)

    def test_empty_array_is_inconclusive(self):
        self.assertEqual(self.query([])['status'],'empty_feed_unverified')

    def test_no_route_match_has_distinct_status(self):
        self.assertEqual(self.query([flight()],origins={'LAX'})['status'],'no_matches_in_source')

    def test_all_invalid_records_are_error(self):
        with self.assertRaises(ValueError): self.query([flight(date='2026-02-30')])

    def test_untrusted_urls_excluded(self):
        result=self.query([flight('good'),flight('bad',url='https://villiers.ai.evil.test/empty-legs/x'),flight('user',url='https://user:pass@villiers.ai/empty-legs/x')])
        self.assertEqual(result['match_count'],1)
        self.assertEqual(result['invalid_records_skipped'],2)

    def test_duplicates_do_not_inflate_inventory(self):
        result=self.query([flight(),flight()])
        self.assertEqual(result['match_count'],1)
        self.assertEqual(result['duplicates_skipped'],1)

    def test_referral_url_preserved(self):
        self.assertEqual(self.query([flight()])['matches'][0]['url'],flight()['url'])

    def test_icao_not_blindly_converted_to_iata(self):
        self.assertEqual(self.query([flight(**{'from':'SCF'})],origins={'SDL'})['match_count'],0)

    def test_multiple_currencies_are_grouped_for_price_sort(self):
        result=self.query([flight('usd',price=100,currency='USD'),flight('eur',price=1000,currency='EUR')],sort='price')
        self.assertEqual([r['currency'] for r in result['matches']],['EUR','USD'])
        self.assertTrue(result['price_sort_groups_by_currency'])

    def test_invalid_date_range_rejected(self):
        with self.assertRaises(ValueError): self.query([flight()],date_from=date(2026,11,8),date_to=date(2026,11,3))


if __name__=='__main__': unittest.main()
