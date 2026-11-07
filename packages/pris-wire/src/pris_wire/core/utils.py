from __future__ import annotations

import time
import uuid
from platform import uname
from typing import Any


def new_uuid() -> int:
    """Return a random 64-bit id, as used for correlation ids."""
    return uuid.uuid4().int >> 64


def consumer_id() -> str:
    """Return a unique consumer id: the host name and a random hex id."""
    return '{}/{:X}'.format(uname()[1], new_uuid())


def now() -> float:
    """Return the current time in seconds since the epoch, the clock of Message.created_at."""
    return time.time()


def assert_type(instance: Any, types: type | tuple[type, ...] | list[type], name: str) -> None:
    """Check the type of a value.

    Args:
        instance: the value to check.
        types: the accepted type, or several.
        name: the value's name, used in the error.

    Raises:
        TypeError: `instance` is of none of `types`.
    """
    if isinstance(types, list):
        types = tuple(types)

    if not isinstance(instance, types):
        input_type = type(instance).__name__
        if isinstance(types, tuple):
            names = " or ".join([t.__name__ for t in types])
            error = "Object {} must be of types {}, received type {}".format(
                name, names, input_type)
        else:
            error = "Object {} must be of type {}, received type {}".format(
                name, types.__name__, input_type)
        raise TypeError(error)
