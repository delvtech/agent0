"""
Test how numpy allclose works
"""

# pylint: disable=invalid-name

import unittest
import logging

import numpy as np


class SanityTests(unittest.TestCase):
    """are we crazy?"""

    a = 991044.807829243
    b = 991044.798842315

    def explicit_allclose(self, a, b, atol=1e-9, rtol=1e-9):
        """show me how close it is"""
        absolute_difference = np.abs(a - b)
        relative_difference = rtol * np.abs(b)
        return absolute_difference, atol + relative_difference, absolute_difference <= atol + relative_difference

    def is_it_allclose_really(self, a, b, absolute_tolerance=1e-9, relative_tolerance=None, quiet=False):
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
        if not quiet:
            output = f"WEIRD: python thinks {a=} and {b=} are off by {verdict} than ({absolute_tolerance=}"
            output += f", {relative_tolerance=})" if relative_tolerance else ")"
            output += f" when {absolute_difference=}({absolute_difference:.0e})"
            output += f" and {relative_difference=}({relative_difference:.0e})" if relative_tolerance else ""
            if relative_tolerance is None:
                explicit_result = self.explicit_allclose(a=a, b=b, atol=absolute_tolerance)
            else:
                explicit_result = self.explicit_allclose(a=a, b=b, atol=absolute_tolerance, rtol=relative_tolerance)
            explicit_absolute_difference, threshold, close_enough = explicit_result
            output += f". explicit allclose gives {explicit_absolute_difference=}, {threshold=}, {close_enough=}"
            logging.debug(output)
        assert verdict == "LESS"


class TestTolerance(SanityTests):
    """test tolerance"""

    def test_without_rtol(self):
        """test allclose without relative tolerance"""
        self.is_it_allclose_really(a=self.a, b=self.b, absolute_tolerance=1e-99)

    def test_with_rtol_0(self):
        """test allclose with relative tolerance"""
        self.is_it_allclose_really(a=self.a, b=self.b, absolute_tolerance=1e-99, relative_tolerance=0)

    def test_with_rtol_1(self):
        """test allclose with relative tolerance"""
        self.is_it_allclose_really(a=self.a, b=self.b, absolute_tolerance=1e-99, relative_tolerance=1)

    def test_with_rtol(self):
        """test allclose with relative tolerance"""
        self.is_it_allclose_really(a=self.a, b=self.b, absolute_tolerance=1e-99, relative_tolerance=1e-1)

    def test_with_rtol_1_e_minus_2(self):
        """test allclose with relative tolerance"""
        self.is_it_allclose_really(a=self.a, b=self.b, absolute_tolerance=1e-99, relative_tolerance=1e-2)

    def test_with_rtol_1_e_minus_3(self):
        """test allclose with relative tolerance"""
        self.is_it_allclose_really(a=self.a, b=self.b, absolute_tolerance=1e-99, relative_tolerance=1e-3)

    def test_with_rtol_1_e_minus_4(self):
        """test allclose with relative tolerance"""
        self.is_it_allclose_really(a=self.a, b=self.b, absolute_tolerance=1e-99, relative_tolerance=1e-4)

    def test_with_rtol_1_e_minus_5(self):
        """test allclose with relative tolerance"""
        self.is_it_allclose_really(a=self.a, b=self.b, absolute_tolerance=1e-99, relative_tolerance=1e-5)

    def test_with_rtol_1_e_minus_6(self):
        """test allclose with relative tolerance"""
        self.is_it_allclose_really(a=self.a, b=self.b, absolute_tolerance=1e-99, relative_tolerance=1e-6)

    def test_with_rtol_1_e_minus_7(self):
        """test allclose with relative tolerance"""
        self.is_it_allclose_really(a=self.a, b=self.b, absolute_tolerance=1e-99, relative_tolerance=1e-7)

    def test_with_rtol_1_e_minus_8(self):
        """test allclose with relative tolerance"""
        self.is_it_allclose_really(a=self.a, b=self.b, absolute_tolerance=1e-99, relative_tolerance=1e-8)

    def test_with_rtol_1_e_minus_9(self):
        """test allclose with relative tolerance"""
        self.is_it_allclose_really(a=self.a, b=self.b, absolute_tolerance=1e-99, relative_tolerance=1e-9)


class InSanityTests(SanityTests):
    """are we sane?"""

    a = 991044.807829243
    b = 990000

    def test_without_rtol(self):
        """test allclose without relative tolerance"""
        self.is_it_allclose_really(a=self.a, b=self.b, absolute_tolerance=1e-99)

    def test_with_rtol_0(self):
        """test allclose with relative tolerance"""
        self.is_it_allclose_really(a=self.a, b=self.b, absolute_tolerance=1e-99, relative_tolerance=0)

    def test_with_rtol_1(self):
        """test allclose with relative tolerance"""
        self.is_it_allclose_really(a=self.a, b=self.b, absolute_tolerance=1e-99, relative_tolerance=1)

    def test_with_rtol_1_e_minus_1(self):
        """test allclose with relative tolerance"""
        self.is_it_allclose_really(a=self.a, b=self.b, absolute_tolerance=1e-99, relative_tolerance=1e-1)

    def test_with_rtol_1_e_minus_2(self):
        """test allclose with relative tolerance"""
        self.is_it_allclose_really(a=self.a, b=self.b, absolute_tolerance=1e-99, relative_tolerance=1e-2)

    def test_with_rtol_1_e_minus_3(self):
        """test allclose with relative tolerance"""
        self.is_it_allclose_really(a=self.a, b=self.b, absolute_tolerance=1e-99, relative_tolerance=1e-3)

    def test_with_rtol_1_e_minus_4(self):
        """test allclose with relative tolerance"""
        self.is_it_allclose_really(a=self.a, b=self.b, absolute_tolerance=1e-99, relative_tolerance=1e-4)

    def test_with_rtol_1_e_minus_5(self):
        """test allclose with relative tolerance"""
        self.is_it_allclose_really(a=self.a, b=self.b, absolute_tolerance=1e-99, relative_tolerance=1e-5)

    def test_with_rtol_1_e_minus_6(self):
        """test allclose with relative tolerance"""
        self.is_it_allclose_really(a=self.a, b=self.b, absolute_tolerance=1e-99, relative_tolerance=1e-6)

    def test_with_rtol_1_e_minus_7(self):
        """test allclose with relative tolerance"""
        self.is_it_allclose_really(a=self.a, b=self.b, absolute_tolerance=1e-99, relative_tolerance=1e-7)

    def test_with_rtol_1_e_minus_8(self):
        """test allclose with relative tolerance"""
        self.is_it_allclose_really(a=self.a, b=self.b, absolute_tolerance=1e-99, relative_tolerance=1e-8)

    def test_with_rtol_1_e_minus_9(self):
        """test allclose with relative tolerance"""
        self.is_it_allclose_really(a=self.a, b=self.b, absolute_tolerance=1e-99, relative_tolerance=1e-9)


class LetsEdgeCloser(SanityTests):
    """find the threshold where we can get off (without an assertion error)"""

    a = 100

    def you_good(self, a, b, atol, rtol=None, quiet=True):
        """test allclose with relative tolerance"""
        try:
            if rtol is None:
                self.is_it_allclose_really(a=a, b=b, absolute_tolerance=atol, quiet=quiet)
            else:
                self.is_it_allclose_really(
                    a=a,
                    b=b,
                    absolute_tolerance=atol,
                    relative_tolerance=rtol,
                    quiet=quiet,
                )
        except AssertionError:
            return True  # found the first b that fails, you good now
        return False  # keep going, we can edge closer (you not good)

    def find_failing_b(self, a, absolute_tolerance=1e-9, relative_tolerance=None):
        """find the first b that fails"""
        b = a
        while self.you_good(a=a, b=b, atol=absolute_tolerance, rtol=relative_tolerance, quiet=True) is False:
            b -= 1
            logging.debug(f"testing {b=}")
        # YEAH YOU GOOD, DON'T BE QUIET NOW
        self.you_good(a=a, b=b, atol=absolute_tolerance, rtol=relative_tolerance, quiet=False)
        logging.debug(f"first failing b is {b=} for {a=} with {absolute_tolerance=} and {relative_tolerance=}")

    def test_custom(self):
        """test allclose with relative tolerance"""
        self.find_failing_b(a=self.a, absolute_tolerance=1)

    def test_custom2(self):
        """test allclose with relative tolerance"""
        self.find_failing_b(a=self.a, absolute_tolerance=1, relative_tolerance=0)

    def test_custom3(self):
        """test allclose with relative tolerance"""
        self.find_failing_b(a=self.a, absolute_tolerance=1, relative_tolerance=1e-1)

    def test_custom4(self):
        """test allclose with relative tolerance"""
        self.find_failing_b(a=self.a, absolute_tolerance=1, relative_tolerance=1e-2)

    # def test_without_rtol(self):
    #     """test allclose without relative tolerance"""
    #     self.find_failing_b(a=self.a, absolute_tolerance=1e-99)

    # def test_with_rtol_0(self):
    #     """test allclose with relative tolerance"""
    #     self.find_failing_b(a=self.a, absolute_tolerance=1e-99, relative_tolerance=0)

    # def test_with_rtol_1(self):
    #     """test allclose with relative tolerance"""
    #     self.find_failing_b(a=self.a, absolute_tolerance=1e-99, relative_tolerance=1)

    # def test_with_rtol_1_e_minus_1(self):
    #     """test allclose with relative tolerance"""
    #     self.find_failing_b(a=self.a, absolute_tolerance=1e-99, relative_tolerance=1e-1)

    # def test_with_rtol_1_e_minus_2(self):
    #     """test allclose with relative tolerance"""
    #     self.find_failing_b(a=self.a, absolute_tolerance=1e-99, relative_tolerance=1e-2)

    # def test_with_rtol_1_e_minus_3(self):
    #     """test allclose with relative tolerance"""
    #     self.find_failing_b(a=self.a, absolute_tolerance=1e-99, relative_tolerance=1e-3)

    # def test_with_rtol_1_e_minus_4(self):
    #     """test allclose with relative tolerance"""
    #     self.find_failing_b(a=self.a, absolute_tolerance=1e-99, relative_tolerance=1e-4)

    # def test_with_rtol_1_e_minus_5(self):
    #     """test allclose with relative tolerance"""
    #     self.find_failing_b(a=self.a, absolute_tolerance=1e-99, relative_tolerance=1e-5)

    # def test_with_rtol_1_e_minus_6(self):
    #     """test allclose with relative tolerance"""
    #     self.find_failing_b(a=self.a, absolute_tolerance=1e-99, relative_tolerance=1e-6)

    # def test_with_rtol_1_e_minus_7(self):
    #     """test allclose with relative tolerance"""
    #     self.find_failing_b(a=self.a, absolute_tolerance=1e-99, relative_tolerance=1e-7)

    # def test_with_rtol_1_e_minus_8(self):
    #     """test allclose with relative tolerance"""
    #     self.find_failing_b(a=self.a, absolute_tolerance=1e-99, relative_tolerance=1e-8)

    # def test_with_rtol_1_e_minus_9(self):
    #     """test allclose with relative tolerance"""
    #     self.find_failing_b(a=self.a, absolute_tolerance=1e-99, relative_tolerance=1e-9)


if __name__ == "__main__":
    unittest.main()
