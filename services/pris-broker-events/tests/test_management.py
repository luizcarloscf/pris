import pytest
import requests
from opentelemetry.trace import SpanKind

from pris_broker_events.management import fetch_bindings


def test_the_broker_bindings(management_uri):
    bindings = fetch_bindings(management_uri, timeout=5.0)

    assert {"source": "amq.rabbitmq.event", "destination": "pris", "routing_key": "#"}.items() \
        <= next(b for b in bindings if b["source"] == "amq.rabbitmq.event").items()


def test_an_unreachable_api_raises():
    with pytest.raises(requests.ConnectionError):
        fetch_bindings("http://localhost:1", timeout=1.0)


def test_wrong_credentials_raise(management_uri):
    with pytest.raises(requests.HTTPError):
        fetch_bindings(management_uri.replace("guest:guest", "guest:wrong"), timeout=5.0)


def test_the_span_holds_no_credentials(spans, management_uri):
    fetch_bindings(management_uri, timeout=5.0)

    (span,) = spans.get_finished_spans()
    assert span.name == "GET /api/bindings"
    assert span.kind == SpanKind.CLIENT
    assert span.attributes["server.address"] == "localhost"
    assert span.attributes["http.response.status_code"] == 200
    assert "guest" not in repr(span.to_json())
