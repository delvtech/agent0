"""Fixed Point Integer math library"""

# we will use single letter names for the FixedPointIntegerMath class since all functions do basic arithmetic
# pylint: disable=invalid-name

from elfpy.errors import errors


class FixedPointIntegerMath:
    """Safe integer arithmetic that assumes a 18-decimal fixed-point representation

    .. note::
        Most arithmetic adopted from `HyperDrive <https://github.com/delvtech/hyperdrive/blob/main/contracts/src/libraries/FixedPointMath.sol`_
        Credit to
            - `Solmate <https://github.com/transmissions11/solmate/blob/main/src/utils/FixedPointMathLib.sol>`_
            - `Balancer <https://github.com/balancer-labs/balancer-v2-monorepo/blob/master/pkg/solidity-utils/contracts/math/FixedPoint.sol>`_
    """

    # int has no max size in Python 3. We will use 256 since that is max for solidity.
    INT_MAX = 2**255 - 1
    INT_MIN = -(2**255)
    UINT_MAX = 2**256 - 1
    UINT_MIN = 0
    EXP_MAX = 135305999368893231589  # floor(log((2**255 -1) / 1e18) * 1e18)
    EXP_MIN = -42139678854452767622  # floor(log(0.5e-18)*1e18)
    ONE_18 = 1 * 10**18

    @staticmethod
    def add(a: int, b: int) -> int:
        """Add two fixed-point numbers in 1e18 format."""
        c = a + b
        # Solidity has this: `if c < a or a > FixedPointMath.INT_MAX - b`
        # However, we allow negative values sometimes, which trips up that check.
        # Python 3 also won't actually overflow if we go over INT_MAX, so we can just check:
        if c > FixedPointIntegerMath.INT_MAX:
            raise OverflowError(f"add: sum cannot be greater than {FixedPointIntegerMath.INT_MAX=}")
        return c

    @staticmethod
    def sub(a: int, b: int) -> int:
        """Subtract two fixed-point numbers in 1e18 format."""
        c = a - b
        # solidity has this: `if b > a`
        # However, we are encoding our own INT_MIN, since python 3 `int` has no min/max
        if c < FixedPointIntegerMath.INT_MIN:
            raise OverflowError(f"sub: difference cannot be less than {FixedPointIntegerMath.INT_MIN=}")
        return c

    @staticmethod
    def mul_div_down(x: int, y: int, d: int) -> int:
        """Multiply x and y, then divide by d, rounding down."""
        z = x * y
        # don't want to divide by zero; product overflow will cause (x * y) / x != y
        require = d != 0 and (x == 0 or z // x == y)
        if not require:
            raise ValueError("mul_div_down: invalid input")
        if z // d == 0:
            return 0
        # floor div automatically rounds down
        return z // d

    @staticmethod
    def mul_down(a: int, b: int) -> int:
        """Multiply two fixed-point numbers in 1e18 format and round down."""
        return FixedPointIntegerMath.mul_div_down(a, b, FixedPointIntegerMath.ONE_18)

    @staticmethod
    def div_down(a: int, b: int) -> int:
        """Divide two fixed-point numbers in 1e18 format and round down."""
        return FixedPointIntegerMath.mul_div_down(a, FixedPointIntegerMath.ONE_18, b)

    @staticmethod
    def mul_div_up(x: int, y: int, d: int) -> int:
        """Multiply x and y, then divide by d, rounding up."""
        z = x * y
        # don't want to divide by zero; product overflow will cause (x * y) / x != y
        require = d != 0 and (x == 0 or z // x == y)
        if not require:
            raise ValueError("mul_div_up: invalid input")
        # if product is zero, just return zero; this avoids z-1 underflow
        # else, first, divide z - 1 by the d and add 1, which rounds up
        if z == 0:
            return int(0)
        # divide z - 1 by d and add 1, allowing z - 1 to underflow if z is 0
        return ((z - 1) // d) + 1

    @staticmethod
    def mul_up(a: int, b: int) -> int:
        """Multiply a and b, rounding up."""
        return FixedPointIntegerMath.mul_div_up(a, b, FixedPointIntegerMath.ONE_18)

    @staticmethod
    def div_up(a: int, b: int) -> int:
        r"""Divide a by b, rounding up."""
        return FixedPointIntegerMath.mul_div_up(a, FixedPointIntegerMath.ONE_18, b)

    @staticmethod
    def ilog2(x: int) -> int:
        r"""Returns floor(log2(x)) if x is nonzero, otherwise 0.

        This is the same as the location of the highest set bit.
        """
        if x == 0:
            return type(x)(0)
        return x.bit_length() - 1

    @staticmethod
    def ln(x: int) -> int:
        r"""Computes ln(x) in 1e18 fixed point.

        Reverts if value is negative or 0.
        """
        if x <= 0:
            raise ValueError(f"ln: argument must be positive, not {x}")
        # We want to convert x from `precision` fixed point to 2**96 fixed point.
        # We do this by multiplying by 2**96 / precision.
        # But since ln(x * C) = ln(x) + ln(C), we can simply do nothing here
        # and add ln(2**96 / precision) at the end.
        #
        # Reduce range of x to (1, 2) * 2**96
        # ln(2^k * x) = k * ln(2) + ln(x)
        k = FixedPointIntegerMath.ilog2(x) - 96
        x <<= 159 - k
        x >>= 159
        # Evaluate using a (8, 8)-term rational approximation
        # p is made monic, we will multiply by a scale factor later
        p = x + 3273285459638523848632254066296
        p = ((p * x) >> 96) + 24828157081833163892658089445524
        p = ((p * x) >> 96) + 43456485725739037958740375743393
        p = ((p * x) >> 96) - 11111509109440967052023855526967
        p = ((p * x) >> 96) - 45023709667254063763336534515857
        p = ((p * x) >> 96) - 14706773417378608786704636184526
        p = p * x - (795164235651350426258249787498 << 96)
        # We leave p in 2**192 basis so we don't need to scale it back up for the division.
        # q is monic by convention
        q = x + 5573035233440673466300451813936
        q = ((q * x) >> 96) + 71694874799317883764090561454958
        q = ((q * x) >> 96) + 283447036172924575727196451306956
        q = ((q * x) >> 96) + 401686690394027663651624208769553
        q = ((q * x) >> 96) + 204048457590392012362485061816622
        q = ((q * x) >> 96) + 31853899698501571402653359427138
        q = ((q * x) >> 96) + 909429971244387300277376558375
        # r is in the range (0, 0.125) * 2**96
        # r is computed using floor division;
        # future versions could use the remainder, p % q, to increase precision
        r = p // q
        # Finalization, we need to
        # * multiply by the scale factor s = 5.549…
        # * add ln(2**96 / 10**18)
        # * add k * ln(2)
        # * multiply by 10**18 / 2**96 = 5**18 >> 78
        # mul s * 5e18 * 2**96, base is now 5**18 * 2**192
        r *= 1677202110996718588342820967067443963516166
        # add ln(2) * k * 5e18 * 2**192
        r += 16597577552685614221487285958193947469193820559219878177908093499208371 * k
        # add ln(2**96 / 10**18) * 5e18 * 2**192
        r += 600920179829731861736702779321621459595472258049074101567377883020018308
        # base conversion: mul 2**18 / 2**192
        r >>= 174
        return r

    @staticmethod
    def exp(x: int) -> int:
        r"""Perform a high-precision exponential operator on a fixed-point integer with 1e18 precision"""
        # Input x is in fixed point format, with scale factor 1/1e18.
        # When the result is < 0.5 we return zero. This happens when
        # x <= floor(log(0.5e-18) * 1e18) ~ -42e18
        if x <= FixedPointIntegerMath.EXP_MIN:
            return 0
        # When the result is > (2**255 - 1) / 1e18 we can not represent it
        # as an int256. This happens when x >= floor(log((2**255 -1) / 1e18) * 1e18) ~ 135.
        if x >= FixedPointIntegerMath.EXP_MAX:
            raise ValueError(f"exp: exponent={x} must be less than {FixedPointIntegerMath.EXP_MAX=}")
        # x is now in the range (-42, 136) * 1e18, inclusive.
        # Convert to (-42, 136) * 2**96 for more intermediate
        # precision and a binary basis. This base conversion
        # is a multiplication by 1e18 / 2**96 = 5**18 / 2**78.
        x = (x << 78) // (5**18)
        # Reduce range of x to (-0.5 * ln 2, 0.5 * ln 2) * 2**96 by factoring out powers of two
        # such that exp(x) = exp(x') * 2**k, where k is an integer.
        # Solving this gives k = round(x / log(2)) and x' = x - k * log(2).
        # k is in the range [-61, 195].
        k = (((x << 96) // 54916777467707473351141471128) + (2**95)) >> 96
        x = x - k * 54916777467707473351141471128
        # Evaluate using a (6, 7)-term rational approximation
        # p is made monic, we will multiply by a scale factor later
        p = x + 2772001395605857295435445496992
        p = ((p * x) >> 96) + 44335888930127919016834873520032
        p = ((p * x) >> 96) + 398888492587501845352592340339721
        p = ((p * x) >> 96) + 1993839819670624470859228494792842
        p = p * x + (4385272521454847904659076985693276 << 96)
        # We leave p in 2**192 basis so we don't need to scale it back up for the division.
        # Evaluate using using Knuth's scheme from p. 491.
        z = x + 750530180792738023273180420736
        z = ((z * x) >> 96) + 32788456221302202726307501949080
        w = x - 2218138959503481824038194425854
        w = ((w * z) >> 96) + 892943633302991980437332862907700
        q = z + w - 78174809823045304726920794422040
        q = ((q * w) >> 96) + 4203224763890128580604056984195872
        # r should be in the range (0.09, 0.25) * 2**96.
        # r is computed using floor division;
        # future versions could use the remainder, p % q, to increase precision
        r = p // q
        # We now need to multiply r by
        #  * the scale factor s = ~6.031367120...,
        #  * the 2**k factor from the range reduction, and
        #  * the 1e18 / 2**96 factor for base conversion.
        # We do all of this at once, with an intermediate result in 2**213 basis
        # so the final right shift is always by a positive amount.
        return (r * 3822833074963236453042738258902158003155416615667) >> (195 - k)

    @staticmethod
    def pow(x: int, y: int) -> int:
        r"""Using logarithms we calculate x ** y

        .. math::
            \begin{align*}
                &ln(x^y) = y * ln(x)\\
                &ln(x^y) = y * ln(x) / 1 * 10 ** 18 \\
                &e^{(y * ln(y))} = x^y
            \end{align*}

        Any overflow for x will be caught in ln() in the initial bounds check
        """
        if x == 0:
            if y == 0:
                return FixedPointIntegerMath.ONE_18
            return 0
        ylnx = y * FixedPointIntegerMath.ln(x) // FixedPointIntegerMath.ONE_18
        return FixedPointIntegerMath.exp(ylnx)

    @staticmethod
    def sqrt(x: int) -> int:
        """
        Calculates the square root of a fixed-point number with 1e18 precision.

        .. notes::
            - The algorithm used here is based on the Babylonian method.

            - The input x should be a non-negative integer.

            - The result is rounded down to the nearest integer (floor square root).
        """
        if x < 0:
            raise errors.DivisionByZero("input to sqrt must be a non-negative integer")
        if x in [0, FixedPointIntegerMath.ONE_18]:
            return x
        return FixedPointIntegerMath.pow(x, FixedPointIntegerMath.ONE_18 // 2)
