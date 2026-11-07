import importlib
from importlib import resources

import pytest

PROTOS = ["camera", "common", "image", "power", "robot"]


def test_protos_are_packaged():
    packaged = sorted(f.name for f in resources.files("pris_msgs").iterdir()
                      if f.name.endswith(".proto"))
    assert packaged == [f"{name}.proto" for name in PROTOS]


@pytest.mark.parametrize("name", PROTOS)
def test_generated_module_matches_its_proto(name):
    module = importlib.import_module(f"pris_msgs.{name}_pb2")
    assert module.DESCRIPTOR.name == f"pris_msgs/{name}.proto"
