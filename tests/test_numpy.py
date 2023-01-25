"""
Test how numpy allclose works
"""

# pylint: disable=invalid-name

import unittest

import numpy as np


class SanityTests(unittest.TestCase):
    """are we crazy?"""

    a = 991044.807829243
    b = 991044.798842315

    def explicit_allclose(self, a, b, atol=1e-9, rtol=1e-9):
        """show me how close it is"""
        absolute_difference = np.abs(a - b)
        relative_difference = rtol * np.abs(b)
        return absolute_difference <= atol + relative_difference

    def is_it_allclose_really(self, a, b, absolute_tolerance=1e-9, relative_tolerance=None):
        """is it allclose?"""
        absolute_difference = np.abs(a - b)
        relative_difference = relative_tolerance * np.abs(b) if relative_tolerance else None
        try:
            if relative_tolerance is None:
                assert np.allclose(a=a, b=b, atol=absolute_tolerance)
            else:
                assert np.allclose(a=a, b=b, atol=absolute_tolerance, rtol=relative_tolerance)
            verdict = "LESS"  # off by less than tolerance
        except AssertionError:
            verdict = "MORE"  # off by more than tolerance
        output = f"WEIRD: python thinks {a=} and {b=} are off by {verdict} than ({absolute_tolerance=}"
        output += f", {relative_tolerance=})" if relative_tolerance else ")"
        output += f" but really {absolute_difference=}({absolute_difference:.0e})"
        output += f" and {relative_difference=}({relative_difference:.0e})" if relative_tolerance else ""
        print(output)
        assert verdict == "LESS"

    def test_without_rtol(self):
        """test allclose without relative tolerance"""
        self.is_it_allclose_really(a=self.a, b=self.b, absolute_tolerance=1e-99)

    def test_with_rtol(self):
        """test allclose with relative tolerance"""
        self.is_it_allclose_really(a=self.a, b=self.b, absolute_tolerance=1e-99, relative_tolerance=1e-1)

    def test_with_rtol_1_e_minus_two(self):
        """test allclose with relative tolerance"""
        self.is_it_allclose_really(a=self.a, b=self.b, absolute_tolerance=1e-99, relative_tolerance=1e-2)

    def test_with_rtol_1_e_minus_three(self):
        """test allclose with relative tolerance"""
        self.is_it_allclose_really(a=self.a, b=self.b, absolute_tolerance=1e-99, relative_tolerance=1e-3)

    def test_with_rtol_1_e_minus_four(self):
        """test allclose with relative tolerance"""
        self.is_it_allclose_really(a=self.a, b=self.b, absolute_tolerance=1e-99, relative_tolerance=1e-4)

    def test_with_rtol_1_e_minus_five(self):
        """test allclose with relative tolerance"""
        self.is_it_allclose_really(a=self.a, b=self.b, absolute_tolerance=1e-99, relative_tolerance=1e-5)

    def test_with_rtol_1_e_minus_six(self):
        """test allclose with relative tolerance"""
        self.is_it_allclose_really(a=self.a, b=self.b, absolute_tolerance=1e-99, relative_tolerance=1e-6)

    def test_with_rtol_1_e_minus_seven(self):
        """test allclose with relative tolerance"""
        self.is_it_allclose_really(a=self.a, b=self.b, absolute_tolerance=1e-99, relative_tolerance=1e-7)

    def test_with_rtol_1_e_minus_eight(self):
        """test allclose with relative tolerance"""
        self.is_it_allclose_really(a=self.a, b=self.b, absolute_tolerance=1e-99, relative_tolerance=1e-8)

    def test_with_rtol_1_e_minus_nine(self):
        """test allclose with relative tolerance"""
        self.is_it_allclose_really(a=self.a, b=self.b, absolute_tolerance=1e-99, relative_tolerance=1e-9)

    def test_with_rtol_1_e_minus_ten(self):
        """test allclose with relative tolerance"""
        self.is_it_allclose_really(a=self.a, b=self.b, absolute_tolerance=1e-99, relative_tolerance=1e-10)


if __name__ == "__main__":
    unittest.main()
