:py:mod:`elfpy.pricing_models.hyperdrive`
=========================================

.. py:module:: elfpy.pricing_models.hyperdrive

.. autoapi-nested-parse::

   The Hyperdrive pricing model.

   ..
       !! processed by numpydoc !!


Module Contents
---------------

Classes
~~~~~~~

.. autoapisummary::

   elfpy.pricing_models.hyperdrive.HyperdrivePricingModel




.. py:class:: HyperdrivePricingModel

   Bases: :py:obj:`elfpy.pricing_models.yieldspace.YieldSpacePricingModel`

   
   Hyperdrive Pricing Model

   This pricing model uses a combination of a constant sum invariant and a
   YieldSpace invariant with modifications to enable the base reserves to be
   deposited into yield bearing vaults















   ..
       !! processed by numpydoc !!
   .. py:method:: model_name() -> str

      
      Unique name given to the model, can be based on member variable states
















      ..
          !! processed by numpydoc !!

   .. py:method:: model_type() -> str

      
      Unique identifier given to the model, should be lower snake_cased name
















      ..
          !! processed by numpydoc !!

   .. py:method:: calc_in_given_out(out: elfpy.types.Quantity, market_state: elfpy.types.MarketState, time_remaining: elfpy.types.StretchedTime) -> elfpy.types.TradeResult

      
      Calculates the amount of an asset that must be provided to receive a
      specified amount of the other asset given the current AMM reserves.

      The input is calculated as:

      .. math::
          \begin{align*}
          & in' = \;\;
          \begin{cases}\\
          \;\;\text{ if $token\_in$ = "base"} \;\; \mid \;\; c \cdot \bigg(\dfrac{1}{\mu} \Bigg(
          \dfrac{k - \big(2y + cz - \Delta y \cdot t\big)^{1-\tau}}{\dfrac{c}{\mu}}\Bigg)^{\dfrac{1}{1-\tau}} - z\bigg)
          + \Delta y \cdot \big(1 - \tau\big) \\\\
          \;\;\text{ if $token\_in$ "pt"} \;\;\;\;\;\;\;\;\; \mid \;\; \bigg(k - \dfrac{c}{\mu} \Big(\mu * \big(z - \Delta z \cdot t\big)\Big)^{1 - \tau}\bigg)^{\dfrac{1}{1 - \tau}}
          - \big(2y + cz\big) + c \cdot \Delta z \cdot \big(1 - \tau\big) \\\
          \end{cases} \\\\
          & f = \;\;\;\;
          \begin{cases}\\\\\
          \;\;\text{ if $token\_in$ = "base"} \;\; \mid \;\; \Bigg(1 - \dfrac{1}{\bigg(\dfrac{2y + cz}{\mu z}\bigg)^{\tau}}\Bigg)\; \phi\; \Delta y \\\\\\
          \;\;\text{ if $token\_in$ = "pt"} \;\;\;\;\;\; \mid \;\; \bigg(\bigg(\dfrac{2y + cz}{\mu z}\bigg)^{\tau} - 1\bigg)\; \phi\; (c \cdot \Delta z) \\\\\
          \end{cases} \\\\\\
          & in = in' + f\\
          \end{align*}

      :param out: The quantity of tokens that the user wants to receive (the amount
                  and the unit of the tokens).
      :type out: Quantity
      :param market_state: The state of the AMM's reserves and share prices.
      :type market_state: MarketState
      :param time_remaining: The time remaining for the asset (incorporates time stretch).
      :type time_remaining: StretchedTime

      :returns: * *float* -- The amount the user pays without fees or slippage. The units
                  are always in terms of bonds or base.
                * *float* -- The amount the user pays with fees and slippage. The units are
                  always in terms of bonds or base.
                * *float* -- The amount the user pays with slippage and no fees. The units are
                  always in terms of bonds or base.
                * *float* -- The fee the user pays. The units are always in terms of bonds or
                  base.















      ..
          !! processed by numpydoc !!

   .. py:method:: calc_out_given_in(in_: elfpy.types.Quantity, market_state: elfpy.types.MarketState, time_remaining: elfpy.types.StretchedTime) -> elfpy.types.TradeResult

      
      Calculates the amount of an asset that must be provided to receive a specified amount of the
      other asset given the current AMM reserves.

      The output is calculated as:

      .. math::
          \begin{align*}
          & out' =\;\;\;\; \begin{cases}\\
          \;\;\text{if $token\_out$ = "base"} \;\; \mid \;\;
          c \Bigg(z - \dfrac{1}{\mu} \bigg(\dfrac{k - \big(2y + cz + \Delta y \cdot t\big)^{1 - \tau}}{\dfrac{c}{\mu}}\bigg)^{\dfrac{1}{1 - \tau}}\Bigg) + \Delta y \cdot (1 - \tau) \\\\
          \;\;\text{if $token\_out$ = "pt"} \;\;\;\;\; \mid \;\; 2y + cz - \bigg(k - \dfrac{c}{\mu} \Big(\mu \big(z + \Delta z \cdot t\big)\Big)^{1 - \tau}\bigg)^{\dfrac{1}{1 - \tau}} + c \cdot \Delta z \cdot \big(1 - \tau\big) \\\\
          \end{cases} \\\\\\
          & f = \;\;\;\;\;\;\;\; \begin{cases}\\
          \;\;\text{if $token\_out$ = "base"} \;\; \mid \;\; \Big(1 - \dfrac{1}{\Big(\dfrac{2y + cz}{\mu z}\Big)^{\tau}}\Big) \; \phi \; \Delta y \\\\
          \;\;\text{if $token\_out$ = "pt"} \;\;\;\;\; \mid \;\; \Big(\Big(\dfrac{2y + cz}{\mu z}\Big)^{\tau} - 1\Big) \; \phi \; \Big(c \cdot \Delta z\Big) \\\\
          \end{cases} \\\\\\
          & out = out' + f
          \end{align*}

      :param in_: The quantity of tokens that the user wants to pay (the amount and the unit of the
                  tokens).
      :type in_: Quantity
      :param market_state: The state of the AMM's reserves and share prices.
      :type market_state: MarketState
      :param time_remaining: The time remaining for the asset (incorporates time stretch).
      :type time_remaining: StretchedTime

      :returns: The result of performing the trade.
      :rtype: TradeResult















      ..
          !! processed by numpydoc !!


