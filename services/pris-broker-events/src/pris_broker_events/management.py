"""The broker's management API: the bindings that exist when the service starts."""

from __future__ import annotations

from typing import Any
from urllib.parse import urljoin, urlparse

import requests
from opentelemetry import trace
from opentelemetry.trace import SpanKind


def fetch_bindings(uri: str, timeout: float) -> list[dict[str, Any]]:
    """Get every binding of the broker, in a CLIENT span that holds no credentials.

    Args:
        uri: the management API, e.g. 'http://guest:guest@localhost:15672'.
        timeout: the most seconds to wait for the response.

    Returns:
        The bindings, as `GET /api/bindings` returns them.

    Raises:
        requests.RequestException: the API can't be reached, answers an error or no JSON.
    """
    url = urljoin(uri, "/api/bindings")
    parsed = urlparse(url)
    attributes: dict[str, Any] = {
        "http.request.method": "GET",
        "url.template": "/api/bindings",
        "server.address": parsed.hostname or "",
    }
    if parsed.port is not None:
        attributes["server.port"] = parsed.port

    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span("GET /api/bindings", kind=SpanKind.CLIENT,
                                      attributes=attributes) as span:
        response = requests.get(url, timeout=timeout)
        span.set_attribute("http.response.status_code", response.status_code)
        response.raise_for_status()
        bindings: list[dict[str, Any]] = response.json()
        return bindings
