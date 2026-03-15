from __future__ import annotations
import math


class RatNum:
    """
    RatNum — неизменяемое рациональное число или NaN.

    ============================
    Representation Fields
    ============================
    _numer: int
    _denom: int

    ============================
    Representation Invariant
    ============================
    1) Если НЕ NaN:
        - _denom > 0
        - gcd(abs(_numer), _denom) == 1
    2) Если NaN:
        - _numer == 0
        - _denom == 0

    ============================
    Abstraction Function
    ============================
    AF(self):
        если _denom == 0:
            NaN
        иначе:
            _numer / _denom
    """

    __slots__ = ("_numer", "_denom")

    def __init__(self, numer: int, denom: int = 1):
        if not isinstance(numer, int) or not isinstance(denom, int):
            raise TypeError("numer and denom must be int")

        if denom == 0:
            self._numer = 0
            self._denom = 0
            return

        if denom < 0:
            numer = -numer
            denom = -denom

        g = math.gcd(numer, denom)
        numer //= g
        denom //= g

        self._numer = numer
        self._denom = denom

    # ---------------- Basic ----------------

    def is_nan(self) -> bool:
        return self._denom == 0

    def is_negative(self) -> bool:
        return not self.is_nan() and self._numer < 0

    def is_positive(self) -> bool:
        return not self.is_nan() and self._numer > 0

    def compare_to(self, other: "RatNum") -> int:
        if not isinstance(other, RatNum):
            raise TypeError

        if self.is_nan() and other.is_nan():
            return 0
        if self.is_nan():
            return 1
        if other.is_nan():
            return -1

        left = self._numer * other._denom
        right = other._numer * self._denom
        return (left > right) - (left < right)

    def float_value(self) -> float:
        return float("nan") if self.is_nan() else self._numer / self._denom

    def int_value(self) -> int:
        if self.is_nan() or self._denom != 1:
            raise ArithmeticError
        return self._numer

    # ---------------- Arithmetic ----------------

    def __neg__(self):
        return RatNum(0, 0) if self.is_nan() else RatNum(-self._numer, self._denom)

    def __add__(self, other):
        if not isinstance(other, RatNum):
            raise TypeError
        if self.is_nan() or other.is_nan():
            return RatNum(0, 0)
        return RatNum(
            self._numer * other._denom + other._numer * self._denom,
            self._denom * other._denom
        )

    def __sub__(self, other):
        return self + (-other)

    def __mul__(self, other):
        if not isinstance(other, RatNum):
            raise TypeError
        if self.is_nan() or other.is_nan():
            return RatNum(0, 0)
        return RatNum(self._numer * other._numer,
                      self._denom * other._denom)

    def __truediv__(self, other):
        if not isinstance(other, RatNum):
            raise TypeError
        if self.is_nan() or other.is_nan():
            return RatNum(0, 0)
        if other._numer == 0:
            return RatNum(0, 0)
        return RatNum(self._numer * other._denom,
                      self._denom * other._numer)

    # ---------------- Utility ----------------

    @staticmethod
    def gcd(a: int, b: int) -> int:
        if not isinstance(a, int) or not isinstance(b, int):
            raise TypeError
        return abs(math.gcd(a, b))

    def __eq__(self, other):
        if not isinstance(other, RatNum):
            return False
        if self.is_nan() and other.is_nan():
            return True
        return (self._numer, self._denom) == (other._numer, other._denom)

    def __hash__(self):
        return hash(("NaN",)) if self.is_nan() else hash((self._numer, self._denom))

    def __str__(self):
        if self.is_nan():
            return "NaN"
        if self._denom == 1:
            return str(self._numer)
        return f"{self._numer}/{self._denom}"
