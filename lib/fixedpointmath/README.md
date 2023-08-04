# fixedpointmath
**fixedpointmath** is a package that solves the issue of noisy floating point in Python. 

Floating point rounding errors can be deteremental when precision matters, such as in the case of [blockchain simulation](https://github.com/delvtech/elf-simulations). To solve this issue, we built a fixed-point class to use integers to represent real numbers. Internally, the `FixedPoint` class within **fixedpointmath** conducts all operations using 18-decimal fixed-point precision integers and arithmetic.

To avoid confusion, the `FixedPoint` class abstracts the internal integer representation, and provides a suite of operations that act upon the class, including mixed-type operations. For example, 

```python
>>> from fixedpointmath import FixedPoint
>>> float(FixedPoint(8.0))
8.0
>>> int(FixedPoint(8.528))
8
>>> int(8) * FixedPoint(8)
FixedPoint("64.0")
>>> 8.0 * FixedPoint(8)
TypeError: unsupported operand type(s): <class 'float'>
```

The last example throws a `TypeError` due to the lack of known precision between classic `float` and `FixedPoint`.

We also provide support for accessing and initializing `FixedPoint` with the integer internal representation, which can be useful for communicating with Solidity contracts. For example,

```python
>>> from fixedpointmath import FixedPoint
>>> FixedPoint(8.52).scaled_value
8520000000000000000
>>> FixedPoint(scaled_value=int(8e18))
FixedPoint("8.0")
```