from importlib.metadata import entry_points

from opentelemetry.instrumentation.dependencies import get_dependency_conflicts
from opentelemetry.instrumentation.pris_wire import PrisWireInstrumentor
from opentelemetry.instrumentation.pris_wire.package import _instruments


def test_instrument_uninstrument():
    instrumentor = PrisWireInstrumentor()
    instrumentor.instrument()
    try:
        assert instrumentor.is_instrumented_by_opentelemetry
    finally:
        instrumentor.uninstrument()
    assert not instrumentor.is_instrumented_by_opentelemetry


def test_entry_point():
    found = entry_points(group="opentelemetry_instrumentor", name="pris_wire")
    assert [ep.load() for ep in found] == [PrisWireInstrumentor]


def test_installed_pris_wire_satisfies_dependencies():
    assert get_dependency_conflicts(_instruments) is None
