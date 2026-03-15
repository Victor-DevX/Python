from __future__ import annotations
from typing import Tuple
from ratnum import RatNum


class RatPoly:
    """
    RatPoly — полином с рациональными коэффициентами.

    Representation:
        _coeffs: tuple[RatNum, ...]
        coeffs[i] — коэффициент при x^i

    Invariant:
        - нет ведущих нулей
        - пустой tuple означает нулевой полином
        - если NaN, то _coeffs = (RatNum(0,0),)
    """

    __slots__ = ("_coeffs",)

    def __init__(self, coeffs=None):
        if coeffs is None:
            coeffs = []

        cleaned = []
        for c in coeffs:
            if not isinstance(c, RatNum):
                raise TypeError
            if c.is_nan():
                self._coeffs = (RatNum(0, 0),)
                return
            cleaned.append(c)

        while cleaned and cleaned[-1] == RatNum(0):
            cleaned.pop()

        self._coeffs = tuple(cleaned)

    def is_nan(self):
        return len(self._coeffs) == 1 and self._coeffs[0].is_nan()

    def degree(self):
        if self.is_nan():
            raise ArithmeticError
        return len(self._coeffs) - 1

    def get_coeff(self, i):
        if self.is_nan():
            raise ArithmeticError
        if i < 0:
            raise ValueError
        if i >= len(self._coeffs):
            return RatNum(0)
        return self._coeffs[i]

    def __neg__(self):
        if self.is_nan():
            return RatPoly((RatNum(0, 0),))
        return RatPoly([-c for c in self._coeffs])

    def __add__(self, other):
        if self.is_nan() or other.is_nan():
            return RatPoly((RatNum(0, 0),))

        max_len = max(len(self._coeffs), len(other._coeffs))
        result = []
        for i in range(max_len):
            result.append(self.get_coeff(i) + other.get_coeff(i))
        return RatPoly(result)

    def __sub__(self, other):
        return self + (-other)

    def __mul__(self, other):
        if self.is_nan() or other.is_nan():
            return RatPoly((RatNum(0, 0),))

        if self.degree() == -1 or other.degree() == -1:
            return RatPoly()

        result = [RatNum(0)] * (self.degree() + other.degree() + 1)

        for i, a in enumerate(self._coeffs):
            for j, b in enumerate(other._coeffs):
                result[i + j] = result[i + j] + a * b

        return RatPoly(result)

    def __truediv__(self, other):
        if self.is_nan() or other.is_nan():
            return RatPoly((RatNum(0, 0),))
        if other.degree() == -1:
            return RatPoly((RatNum(0, 0),))

        dividend = list(self._coeffs)
        divisor = other._coeffs
        result = [RatNum(0)] * max(0, self.degree() - other.degree() + 1)

        while len(dividend) - 1 >= other.degree() and dividend:
            coeff = dividend[-1] / divisor[-1]
            power = len(dividend) - len(divisor)
            result[power] = coeff

            for i in range(len(divisor)):
                dividend[power + i] = dividend[power + i] - coeff * divisor[i]

            while dividend and dividend[-1] == RatNum(0):
                dividend.pop()

        return RatPoly(result)

    def eval(self, x: RatNum):
        if self.is_nan() or x.is_nan():
            return RatNum(0, 0)

        result = RatNum(0)
        for coeff in reversed(self._coeffs):
            result = coeff + x * result
        return result

    def value_of(self, x: RatNum):
        return self.eval(x)

    def differentiate(self):
        if self.is_nan():
            return RatPoly((RatNum(0, 0),))
        if self.degree() <= 0:
            return RatPoly()

        result = []
        for i in range(1, len(self._coeffs)):
            result.append(self._coeffs[i] * RatNum(i))
        return RatPoly(result)

    def anti_differentiate(self, c: RatNum = RatNum(0)):
        if self.is_nan() or c.is_nan():
            return RatPoly((RatNum(0, 0),))

        result = [c]
        for i, coeff in enumerate(self._coeffs):
            result.append(coeff / RatNum(i + 1))
        return RatPoly(result)

    def integrate(self, a: RatNum, b: RatNum):
        if self.is_nan() or a.is_nan() or b.is_nan():
            return RatNum(0, 0)

        F = self.anti_differentiate(RatNum(0))
        return F.eval(b) - F.eval(a)

    def __eq__(self, other):
        if not isinstance(other, RatPoly):
            return False
        if self.is_nan() and other.is_nan():
            return True
        return self._coeffs == other._coeffs

    def __hash__(self):
        return hash(("NaNPoly",)) if self.is_nan() else hash(self._coeffs)

    def __str__(self):
        if self.is_nan():
            return "NaN"
        if self.degree() == -1:
            return "0"

        terms = []
        for i, coeff in enumerate(self._coeffs):
            if coeff == RatNum(0):
                continue
            if i == 0:
                terms.append(str(coeff))
            else:
                base = "" if coeff == RatNum(1) else "-" if coeff == RatNum(-1) else f"{coeff}*"
                if i == 1:
                    terms.append(f"{base}x")
                else:
                    terms.append(f"{base}x^{i}")

        return " + ".join(reversed(terms)).replace("+ -", "- ")