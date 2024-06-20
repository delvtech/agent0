"""Extend the default JSON encoder to include additional types."""

import json
from dataclasses import asdict, is_dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from traceback import format_tb
from types import TracebackType
from typing import Any

import numpy as np
import pandas as pd
from fixedpointmath import FixedPoint
from hexbytes import HexBytes
from numpy.random import Generator
from web3.datastructures import AttributeDict, MutableAttributeDict


class ExtendedJSONEncoder(json.JSONEncoder):
    r"""Custom encoder for JSON string dumps."""

    # pylint: disable=too-many-return-statements
    # pylint: disable=too-many-branches
    def default(self, o: Any) -> Any:
        """Override default behavior.

        Arguments
        ---------
        o: Any
            The object to be converted to JSON.

        Returns
        -------
        Any
            The corresponding object ready to be serialized to JSON.
        """
        if isinstance(o, set):
            return list(o)
        if isinstance(o, HexBytes):
            return o.hex()
        if isinstance(o, (AttributeDict, MutableAttributeDict)):
            return dict(o)
        if isinstance(o, np.integer):
            return int(o)
        if isinstance(o, np.floating):
            return float(o)
        if isinstance(o, np.ndarray):
            return o.tolist()
        if isinstance(o, FixedPoint):
            return str(o)
        if isinstance(o, Decimal):
            return str(o)
        if isinstance(o, Generator):
            return "NumpyGenerator"
        if isinstance(o, datetime):
            return str(o)
        if isinstance(o, TracebackType):
            return format_tb(o)
        if isinstance(o, Exception):
            return repr(o)
        if isinstance(o, BaseException):
            return repr(o)
        if isinstance(o, Enum):
            return o.name
        if isinstance(o, bytes):
            return str(o)
        if isinstance(o, pd.DataFrame):
            return o.to_dict(orient="records")
        if is_dataclass(o):
            # We know o is an object here, not a type.
            out = asdict(o)  # type: ignore
            out.update({"class_name": o.__class__.__name__})  # type: ignore
            return out

        try:
            return o.__dict__
        except AttributeError:
            pass
        # Let the base class default method raise the TypeError
        return json.JSONEncoder.default(self, o)
