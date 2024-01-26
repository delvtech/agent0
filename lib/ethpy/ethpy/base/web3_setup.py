"""Functions and classes for setting up a web3py interface"""

from __future__ import annotations

from eth_typing import URI
from web3 import Web3
from web3.middleware import geth_poa
from web3.types import RPCEndpoint


def initialize_web3_with_http_provider(
    ethereum_node: URI | str, request_kwargs: dict | None = None, reset_provider: bool = False
) -> Web3:
    """Initialize a Web3 instance using an HTTP provider and inject a geth Proof of Authority (poa) middleware.

    .. note::
        The geth_poa_middleware is required to connect to geth --dev or the Goerli public network.
        It may also be needed for other EVM compatible blockchains like Polygon or BNB Chain (Binance Smart Chain).
        See more `here <https://web3py.readthedocs.io/en/stable/middleware.html#proof-of-authority>`_.

    Arguments
    ---------
    ethereum_node: URI | str
        Address of the http provider
    request_kwargs: dict | None, optional
        The HTTPProvider uses the python requests library for making requests.
        If you would like to modify how requests are made,
        you can use the request_kwargs to do so.
    reset_provider: bool, optional
        If true, will call anvil_reset before returning the Web3 instance.

    Returns
    -------
    Web3
        The connected web3 instance
    """
    if request_kwargs is None:
        request_kwargs = {}
    provider = Web3.HTTPProvider(ethereum_node, request_kwargs)
    web3 = Web3(provider)
    web3.middleware_onion.inject(geth_poa.geth_poa_middleware, layer=0)
    if reset_provider:
        # TODO: Check that the user is running on anvil, raise error if not
        _ = web3.provider.make_request(method=RPCEndpoint("anvil_reset"), params=[])
    return web3
