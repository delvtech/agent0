:py:mod:`elfpy.utils.outputs`
=============================

.. py:module:: elfpy.utils.outputs

.. autoapi-nested-parse::

   Helper functions for delivering simulation outputs

   ..
       !! processed by numpydoc !!


Module Contents
---------------

Classes
~~~~~~~

.. autoapisummary::

   elfpy.utils.outputs.CustomEncoder



Functions
~~~~~~~~~

.. autoapisummary::

   elfpy.utils.outputs.plot_market_lp_reserves
   elfpy.utils.outputs.plot_market_spot_price
   elfpy.utils.outputs.plot_pool_apr
   elfpy.utils.outputs.plot_longs_and_shorts
   elfpy.utils.outputs.plot_wallet_returns
   elfpy.utils.outputs.get_gridspec_subplots
   elfpy.utils.outputs.clear_axis
   elfpy.utils.outputs.clear_axes
   elfpy.utils.outputs.format_axis
   elfpy.utils.outputs.annotate
   elfpy.utils.outputs.delete_log_file
   elfpy.utils.outputs.setup_logging
   elfpy.utils.outputs.close_logging



.. py:function:: plot_market_lp_reserves(simulator: elfpy.simulators.Simulator) -> matplotlib.figure.Figure

   
   Plot the simulator market LP reserves per day

   :param simulator: An instantiated simulator that has run trades with agents
   :type simulator: Simulator

   :rtype: Figure















   ..
       !! processed by numpydoc !!

.. py:function:: plot_market_spot_price(simulator: elfpy.simulators.Simulator) -> matplotlib.figure.Figure

   
   Plot the simulator market APR per day

   :param simulator: An instantiated simulator that has run trades with agents
   :type simulator: Simulator

   :rtype: Figure















   ..
       !! processed by numpydoc !!

.. py:function:: plot_pool_apr(simulator: elfpy.simulators.Simulator) -> matplotlib.figure.Figure

   
   Plot the simulator market APR per day

   :param simulator: An instantiated simulator that has run trades with agents
   :type simulator: Simulator

   :rtype: Figure















   ..
       !! processed by numpydoc !!

.. py:function:: plot_longs_and_shorts(simulator: elfpy.simulators.Simulator, exclude_first_agent: bool = True, xtick_step: int = 10) -> matplotlib.figure.Figure

   
   Plot the total market longs & shorts over time

   :param simulator: An instantiated simulator that has run trades with agents
   :type simulator: Simulator
   :param exclude_first_agent: If true, exclude the first agent in simulator.agents (this is usually the init_lp agent)
   :type exclude_first_agent: bool

   :rtype: Figure















   ..
       !! processed by numpydoc !!

.. py:function:: plot_wallet_returns(simulator: elfpy.simulators.Simulator, exclude_first_agent: bool = True, xtick_step: int = 10) -> matplotlib.figure.Figure

   
   Plot the wallet base asset and LP token quantities over time

   :param simulator: An instantiated simulator that has run trades with agents
   :type simulator: Simulator
   :param exclude_first_agent: If true, exclude the first agent in simulator.agents (this is usually the init_lp agent)
   :type exclude_first_agent: bool

   :rtype: Figure















   ..
       !! processed by numpydoc !!

.. py:function:: get_gridspec_subplots(nrows: int = 1, ncols: int = 1, **kwargs: Any) -> tuple[matplotlib.figure.Figure, matplotlib.pyplot.Axes, matplotlib.gridspec.GridSpec]

   
   Setup a figure with axes that have reasonable spacing

   :param nrows: number of rows in the figure
   :type nrows: int
   :param ncols: number of columns in the figure
   :type ncols: int
   :param kwargs: optional keyword arguments to be supplied to matplotlib.gridspec.GridSpec()
   :type kwargs: Any

   :returns: a tuple containing the relevant figure objects
   :rtype: tuple[Figure, Axes, GridSpec]















   ..
       !! processed by numpydoc !!

.. py:function:: clear_axis(axis: matplotlib.pyplot.Axes, spines: str = 'none') -> matplotlib.pyplot.Axes

   
   Clear spines & tick labels from proplot axis object

   :param axis: axis to be cleared
   :type axis: matplotlib axis object
   :param spines: any matplotlib color, defaults to "none" which makes the spines invisible
   :type spines: str

   :returns: axis : matplotlib axis object















   ..
       !! processed by numpydoc !!

.. py:function:: clear_axes(axes: list[matplotlib.pyplot.Axes], spines: str = 'none') -> list

   
   Calls clear_axis iteratively for each axis in axes

   :param axes: axes to be cleared
   :type axes: list of matplotlib axis objects
   :param spines: any matplotlib color, defaults to "none" which makes the spines invisible
   :type spines: str

   :returns: axes : list of matplotlib axis objects















   ..
       !! processed by numpydoc !!

.. py:function:: format_axis(axis_handle, xlabel='', fontsize=18, linestyle='--', linewidth='1', color='grey', which='both', axis='y')

   
   Formats the axis
















   ..
       !! processed by numpydoc !!

.. py:function:: annotate(axis_handle, text, major_offset, minor_offset, val)

   
   Adds legend-like labels
















   ..
       !! processed by numpydoc !!

.. py:function:: delete_log_file() -> None

   
   If the logger's handler if a file handler, delete the underlying file.
















   ..
       !! processed by numpydoc !!

.. py:function:: setup_logging(log_filename: Optional[str] = None, max_bytes: int = elfpy.DEFAULT_LOG_MAXBYTES, log_level: int = elfpy.DEFAULT_LOG_LEVEL) -> None

   
   Setup logging and handlers with default settings
















   ..
       !! processed by numpydoc !!

.. py:function:: close_logging(delete_logs=True)

   
   Close logging and handlers for the test
















   ..
       !! processed by numpydoc !!

.. py:class:: CustomEncoder(*, skipkeys=False, ensure_ascii=True, check_circular=True, allow_nan=True, sort_keys=False, indent=None, separators=None, default=None)

   Bases: :py:obj:`json.JSONEncoder`

   
   Custom encoder for JSON string dumps
















   ..
       !! processed by numpydoc !!
   .. py:method:: default(o)

      
      Override default behavior
















      ..
          !! processed by numpydoc !!


