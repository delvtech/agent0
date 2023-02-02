:py:mod:`elfpy.policies.single_lp`
==================================

.. py:module:: elfpy.policies.single_lp

.. autoapi-nested-parse::

   User strategy that adds base liquidity and doesn't remove until liquidation

   ..
       !! processed by numpydoc !!


Module Contents
---------------

Classes
~~~~~~~

.. autoapisummary::

   elfpy.policies.single_lp.Policy




.. py:class:: Policy(wallet_address, budget=1000)

   Bases: :py:obj:`elfpy.agent.Agent`

   
   simple LP that only has one LP open at a time
















   ..
       !! processed by numpydoc !!
   .. py:method:: action(_market: elfpy.markets.Market)

      
      implement user strategy
      LP if you can, but only do it once
















      ..
          !! processed by numpydoc !!


