"""Trace context propagation through Message.metadata, which pris-wire sends as AMQP headers."""

from __future__ import annotations

from typing import Any

from opentelemetry import propagate
from opentelemetry.context import Context
from opentelemetry.propagators.textmap import Getter, Setter


class _MetadataGetter(Getter[dict[str, Any]]):

    def get(self, carrier: dict[str, Any], key: str) -> list[str] | None:
        value = carrier.get(key)
        if value is None:
            return None
        if isinstance(value, bytes):
            value = value.decode("utf-8", errors="replace")
        return [str(value)]

    def keys(self, carrier: dict[str, Any]) -> list[str]:
        return list(carrier.keys())


class _MetadataSetter(Setter[dict[str, Any]]):

    def set(self, carrier: dict[str, Any], key: str, value: str) -> None:
        carrier[key] = value


_getter = _MetadataGetter()
_setter = _MetadataSetter()


def inject(message: Any, context: Context | None = None) -> None:
    """Write a trace context into a message's metadata, with the global propagator.

    Args:
        message: the pris_wire Message to publish.
        context: the context to write; by default the current one.
    """
    carrier = dict(message.metadata)
    propagate.inject(carrier, context=context, setter=_setter)
    message.metadata = carrier


def extract(message: Any) -> Context:
    """Read the trace context a received message carries, with the global propagator.

    Args:
        message: a pris_wire Message received by Channel.consume.

    Returns:
        The context, to use as the parent (or a link) of the spans that process the message;
        an empty context if the message carries none.
    """
    return propagate.extract(message.metadata, getter=_getter)
