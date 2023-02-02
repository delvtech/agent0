:py:mod:`elfpy.policies.single_short`
=====================================

.. py:module:: elfpy.policies.single_short

.. autoapi-nested-parse::

   User strategy that opens a single short and doesn't close until liquidation

   ..
       !! processed by numpydoc !!


Module Contents
---------------

Classes
~~~~~~~

.. autoapisummary::

   elfpy.policies.single_short.Policy




.. py:class:: Policy(wallet_address, budget=100)

   Bases: :py:obj:`elfpy.agent.Agent`

   
   simple short thatonly has one long open at a time
















   ..
       !! processed by numpydoc !!
   .. py:method:: action(market: elfpy.markets.Market)

      
      implement user strategy
      short if you can, only once
















      ..
          !! processed by numpydoc !!


