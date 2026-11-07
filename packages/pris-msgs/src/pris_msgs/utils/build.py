"""Compile .proto files that may import "pris_msgs/<name>.proto" into *_pb2.py and *_pb2.pyi.

    python -m pris_msgs.utils.build [--proto_path DIR ...] [--out DIR] a.proto [b.proto ...]

protoc comes from the PROTOC environment variable, which may be a full command, else "protoc".
"""

import argparse
import os
import shlex
import subprocess
import sys
from typing import Sequence

import pris_msgs


def get_include() -> str:
    """Return the directory that "pris_msgs/<name>.proto" is imported from."""
    return os.path.dirname(os.path.dirname(os.path.abspath(pris_msgs.__file__)))


def main(args: Sequence[str]) -> int:
    """Run protoc on the .proto files named in `args`.

    Args:
        args: the command-line arguments, without the program name.

    Returns:
        protoc's exit code, or -1 when no file is given or a file isn't an existing .proto.
    """
    parser = argparse.ArgumentParser(prog="python -m pris_msgs.utils.build")
    parser.add_argument("--proto_path", action="append", default=[],
                        help="directory the files are named from (repeatable, default .)")
    parser.add_argument("--out", default=".", help="where the generated code goes (default .)")
    parser.add_argument("protos", nargs="*")
    options = parser.parse_args(args)

    if not options.protos:
        print("Nothing to do. No *.proto files passed on arguments. Exiting...")
        return -1
    for proto in options.protos:
        if not proto.endswith(".proto"):
            print("'{}' isn't a *.proto file. Exiting...".format(proto))
            return -1
        if not os.path.exists(proto):
            print("'{}' file doesn't exist. Exiting...".format(proto))
            return -1

    paths = options.proto_path or ["."]
    include = get_include()
    if os.path.realpath(include) not in {os.path.realpath(path) for path in paths}:
        paths.append(include)

    protoc = shlex.split(os.environ.get("PROTOC", "protoc"))
    command = (protoc + [f"--proto_path={path}" for path in paths]
               + [f"--python_out={options.out}", f"--pyi_out={options.out}"]
               + list(options.protos))
    return subprocess.call(command)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
