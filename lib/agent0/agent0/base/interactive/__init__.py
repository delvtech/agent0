"""Interactive hyperdrive"""

import nest_asyncio

from .chain import Chain
from .hyperdrive import Hyperdrive

# In order to support both scripts and jupyter notebooks with underlying async functions,
# we use the nest_asyncio package so that we can execute asyncio.run within a running event loop.
nest_asyncio.apply()
