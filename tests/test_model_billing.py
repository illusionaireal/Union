import unittest
from ai_union.engine import Rejected


class BillingTests(unittest.TestCase):
    def test_metered_uses_integer_minor_units_and_unknown_is_never_zero(self):
        from ai_union.model_billing import calculate, validate_billing
        billing={'basis':'metered','currency':'USD','revision':'price-1','input_per_million_minor':150,'output_per_million_minor':600}
        validate_billing(billing)
        value=calculate(billing,{'input_tokens':1000,'output_tokens':1000})
        self.assertEqual(value['cost_minor'],1)
        self.assertEqual(value['cost_status'],'estimated')
        for basis in ('subscription','owned','unknown'):
            value=calculate({'basis':basis}, {'input_tokens':10,'output_tokens':20})
            self.assertEqual(value['cost_basis'],basis);self.assertIsNone(value['cost_minor'])
        self.assertIsNone(calculate(billing,{'output_tokens':10})['cost_minor'])

    def test_rejects_float_negative_or_unversioned_price(self):
        from ai_union.model_billing import validate_billing
        for value in ({'basis':'invented'},{'basis':'metered','input_per_million_minor':1.5},{'basis':'metered','currency':'USD','revision':'1','input_per_million_minor':-1,'output_per_million_minor':1}):
            with self.assertRaises(Rejected):validate_billing(value)

    def test_largest_remainder_allocation_preserves_exact_total(self):
        from ai_union.model_billing import distribute
        self.assertEqual(distribute(5,{'a':1,'b':1,'c':1}),{'a':2,'b':2,'c':1})
        self.assertEqual(sum(distribute(1000000000000,{'a':111,'b':222,'c':333}).values()),1000000000000)
