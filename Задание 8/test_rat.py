import unittest
from ratnum import RatNum
from ratpoly import RatPoly


class TestRatNum(unittest.TestCase):

    def test_normalization(self):
        self.assertEqual(RatNum(2, 4), RatNum(1, 2))

    def test_nan_compare(self):
        self.assertTrue(RatNum(1, 0).compare_to(RatNum(5)) > 0)
        self.assertEqual(RatNum(1, 0), RatNum(0, 0))

    def test_hash_consistency(self):
        self.assertEqual(hash(RatNum(2, 4)), hash(RatNum(1, 2)))

    def test_div_zero(self):
        self.assertTrue((RatNum(1) / RatNum(0)).is_nan())

    def test_int_value(self):
        with self.assertRaises(ArithmeticError):
            RatNum(3, 2).int_value()


class TestRatPoly(unittest.TestCase):

    def test_zero_degree(self):
        self.assertEqual(RatPoly().degree(), -1)

    def test_add_mul(self):
        p = RatPoly([RatNum(1), RatNum(1)])
        q = RatPoly([RatNum(1), RatNum(-1)])
        self.assertEqual(p * q, RatPoly([RatNum(1), RatNum(0), RatNum(-1)]))

    def test_division(self):
        p = RatPoly([RatNum(-1), RatNum(0), RatNum(1)])
        q = RatPoly([RatNum(-1), RatNum(1)])
        self.assertEqual(p / q, RatPoly([RatNum(1), RatNum(1)]))

    def test_calculus(self):
        p = RatPoly([RatNum(0), RatNum(1)])
        self.assertEqual(p.integrate(RatNum(0), RatNum(1)), RatNum(1, 2))
        self.assertEqual(p.differentiate(), RatPoly([RatNum(1)]))


if __name__ == "__main__":
    unittest.main()