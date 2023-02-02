:py:mod:`elfpy.utils.price`
===========================

.. py:module:: elfpy.utils.price

.. autoapi-nested-parse::

   Utilities for price calculations

   ..
       !! processed by numpydoc !!


Module Contents
---------------


Functions
~~~~~~~~~

.. autoapisummary::

   elfpy.utils.price.calc_apr_from_spot_price
   elfpy.utils.price.calc_spot_price_from_apr



.. py:function:: calc_apr_from_spot_price(price: float, time_remaining: elfpy.types.StretchedTime)

   
   Returns the APR (decimal) given the current (positive) base asset price and the remaining pool duration

   :param price: Spot price of bonds in terms of base
   :type price: float
   :param normalized_time_remaining: Time remaining until bond maturity, in yearfracs
   :type normalized_time_remaining: StretchedTime

   :returns: APR (decimal) calculated from the provided parameters
   :rtype: float















   ..
       !! processed by numpydoc !!

.. py:function:: calc_spot_price_from_apr(apr: float, time_remaining: elfpy.types.StretchedTime)

   
   Returns the current spot price based on the current APR (decimal) and the remaining pool duration

   :param apr: Current fixed APR in decimal units (for example, 5% APR would be 0.05)
   :type apr: float
   :param time_remaining: Time remaining until bond maturity
   :type time_remaining: StretchedTime

   :returns: Spot price of bonds in terms of base, calculated from the provided parameters
   :rtype: float















   ..
       !! processed by numpydoc !!

