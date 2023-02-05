:py:mod:`elfpy.utils.time`
==========================

.. py:module:: elfpy.utils.time

.. autoapi-nested-parse::

   Helper functions for converting time units

   ..
       !! processed by numpydoc !!


Module Contents
---------------


Functions
~~~~~~~~~

.. autoapisummary::

   elfpy.utils.time.current_datetime
   elfpy.utils.time.block_number_to_datetime
   elfpy.utils.time.year_as_datetime
   elfpy.utils.time.get_years_remaining
   elfpy.utils.time.norm_days
   elfpy.utils.time.stretch_time
   elfpy.utils.time.unnorm_days
   elfpy.utils.time.unstretch_time
   elfpy.utils.time.days_to_time_remaining
   elfpy.utils.time.time_to_days_remaining



.. py:function:: current_datetime() -> datetime.datetime

   
   Returns the current time

   :returns: Current UTC time
   :rtype: datetime















   ..
       !! processed by numpydoc !!

.. py:function:: block_number_to_datetime(start_time: datetime.datetime, block_number: float, time_between_blocks: float) -> datetime.datetime

   
   Converts the current block number to a datetime based on the start datetime of the simulation

   :param start_time: Timestamp at which the simulation started
   :type start_time: datetime
   :param block_number: Number of blocks since the simulation started
   :type block_number: int
   :param time_between_blocks: Number of seconds between blocks
   :type time_between_blocks: float

   :returns: Timestamp at which the provided block number was (or will be) validated
   :rtype: datetime















   ..
       !! processed by numpydoc !!

.. py:function:: year_as_datetime(start_time: datetime.datetime, year: float) -> datetime.datetime

   
   Returns a year (e.g. the current market time) in datetime format

   :param start_time: Timestamp at which the simulation started
   :type start_time: datetime
   :param year: Fraction of a year since start_time to convert into datetime
   :type year: float

   :returns: Timestamp for the provided start_time plus the provided year
   :rtype: datetime















   ..
       !! processed by numpydoc !!

.. py:function:: get_years_remaining(market_time: float, mint_time: float, token_duration: float) -> float

   
   Get the year fraction remaining on a token

   :param market_time: Time that has elapsed in the given market, in fractions of a year
   :type market_time: float
   :param mint_time: Time at which the token in question was minted, relative to market_time,
                     in fractions of a year. Should be less than market_time.
   :type mint_time: float
   :param token_duration: Total duration of the token's term, in fractions of a year
   :type token_duration: float

   :returns: Time left until token maturity, in fractions of a year
   :rtype: float















   ..
       !! processed by numpydoc !!

.. py:function:: norm_days(days: float, normalizing_constant: float = 365) -> float

   
   Returns days normalized, with a default assumption of a year-long scale

   :param days: Amount of days to normalize
   :type days: float
   :param normalizing_constant: Amount of days to use as a normalization factor. Defaults to 365
   :type normalizing_constant: float

   :returns: Amount of days provided, converted to fractions of a year
   :rtype: float















   ..
       !! processed by numpydoc !!

.. py:function:: stretch_time(time: float, time_stretch: float = 1.0) -> float

   
   Returns stretched time values

   :param time: Time that needs to be stretched for calculations, in terms of the normalizing constant
   :type time: float
   :param time_stretch: Amount of time units (in terms of a normalizing constant) to use for stretching time, for calculations
                        Defaults to 1
   :type time_stretch: float

   :returns: Stretched time, using the provided parameters
   :rtype: float















   ..
       !! processed by numpydoc !!

.. py:function:: unnorm_days(normed_days: float, normalizing_constant: float = 365) -> float

   
   Returns days from a value between 0 and 1

   :param normed_days: Normalized amount of days, according to a normalizing constant
   :type normed_days: float
   :param normalizing_constant: Amount of days to use as a normalization factor. Defaults to 365
   :type normalizing_constant: float

   :returns: Amount of days, calculated from the provided parameters
   :rtype: float















   ..
       !! processed by numpydoc !!

.. py:function:: unstretch_time(stretched_time: float, time_stretch: float = 1) -> float

   
   Returns unstretched time value, which should be between 0 and 1

   :param stretched_time: Time that has been stretched using the time_stretch factor
   :type stretched_time: float
   :param time_stretch: Amount of time units (in terms of a normalizing constant) to use for stretching time, for calculations
                        Defaults to 1
   :type time_stretch: float

   :returns: Time that was provided, unstretched but still based on the normalization factor
   :rtype: float















   ..
       !! processed by numpydoc !!

.. py:function:: days_to_time_remaining(days_remaining: float, time_stretch: float = 1, normalizing_constant: float = 365) -> float

   
   Converts remaining pool length in days to normalized and stretched time

   :param days_remaining: Time left until term maturity, in days
   :type days_remaining: float
   :param time_stretch: Amount of time units (in terms of a normalizing constant) to use for stretching time, for calculations
                        Defaults to 1
   :type time_stretch: float
   :param normalizing_constant: Amount of days to use as a normalization factor. Defaults to 365
   :type normalizing_constant: float

   :returns: Time remaining until term maturity, in normalized and stretched time
   :rtype: float















   ..
       !! processed by numpydoc !!

.. py:function:: time_to_days_remaining(time_remaining: float, time_stretch: float = 1, normalizing_constant: float = 365) -> float

   
   Converts normalized and stretched time remaining in pool to days

   :param time_remaining: Time left until term maturity, in normalized and stretched time
   :type time_remaining: float
   :param time_stretch: Amount of time units (in terms of a normalizing constant) to use for stretching time, for calculations
                        Defaults to 1
   :type time_stretch: float
   :param normalizing_constant: Amount of days to use as a normalization factor. Defaults to 365
   :type normalizing_constant: float

   :returns: Time remaining until term maturity, in days
   :rtype: float















   ..
       !! processed by numpydoc !!

