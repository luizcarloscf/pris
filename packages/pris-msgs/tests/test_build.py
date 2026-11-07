import importlib
import sys

from pris_msgs.utils import build

PROTO = """
syntax = "proto3";

package pris.build_test;

import "pris_msgs/camera.proto";

message Wrapper {
  pris.vision.CameraConfig config = 1;
}
"""


def test_build_imports_pris_msgs(tmp_path, monkeypatch):
    monkeypatch.setenv("PROTOC", "{} -m grpc_tools.protoc".format(sys.executable))
    (tmp_path / "proto").mkdir()
    (tmp_path / "proto" / "wrapper.proto").write_text(PROTO)
    (tmp_path / "gen").mkdir()
    monkeypatch.chdir(tmp_path)
    monkeypatch.syspath_prepend(str(tmp_path / "gen"))

    assert build.main(["--proto_path", "proto", "--out", "gen", "proto/wrapper.proto"]) == 0
    assert (tmp_path / "gen" / "wrapper_pb2.pyi").exists()

    wrapper_pb2 = importlib.import_module("wrapper_pb2")
    message = wrapper_pb2.Wrapper()
    message.config.sampling.frequency.value = 5.0
    assert wrapper_pb2.Wrapper.FromString(message.SerializeToString()) == message
    sys.modules.pop("wrapper_pb2")


def test_build_rejects_non_proto(tmp_path):
    other = tmp_path / "file.txt"
    other.write_text("")
    assert build.main([str(other)]) == -1
    assert build.main([str(tmp_path / "missing.proto")]) == -1
    assert build.main([]) == -1
