"""Measures how aligned the captures of several gateways are.

Subscribes to `CameraGateway.{id}.Timestamp` and groups the timestamps of the
same tick, `k = round(t / period)`. Meant for gateways on SOFTWARE_SCHEDULED
mode, where all cameras are triggered on the same ticks. On FREE_RUN mode the
captures may be up to half a period apart, so the grouping is meaningless.

E.g.: python etc/examples/measure_sync.py --cameras 0 1 2 3 --frequency 10
"""
import argparse
import socket
from typing import Dict, List

import numpy as np
from google.protobuf.timestamp_pb2 import Timestamp
from pris_wire.core import Channel, Subscription

# incomplete ticks older than this are dropped (e.g. a lost frame)
MAX_PENDING_TICKS = 10


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--uri", default="amqp://guest:guest@localhost:5672", help="broker uri")
    parser.add_argument("--cameras", type=int, nargs="+", default=[0, 1, 2, 3], help="camera ids")
    parser.add_argument("--frequency", type=float, default=10.0,
                        help="sampling rate of the gateways, in Hz")
    parser.add_argument("--samples", type=int, default=50,
                        help="number of complete ticks to measure")
    args = parser.parse_args()

    period_ns = round(1e9 / args.frequency)
    topics = {f"CameraGateway.{cam}.Timestamp": cam for cam in args.cameras}
    channel = Channel(args.uri)
    subscription = Subscription(channel)
    for topic in topics:
        subscription.subscribe(topic)

    pending: Dict[int, Dict[int, int]] = {}
    # one row per complete tick, one column per camera
    rows: List[List[int]] = []
    while len(rows) < args.samples:
        try:
            message = channel.consume(timeout=5.0)
        except socket.timeout:
            print(f"No timestamps received in 5 seconds from {sorted(topics)}")
            continue
        if message.topic not in topics:
            continue
        timestamp_ns = message.unpack(Timestamp).ToNanoseconds()
        k = round(timestamp_ns / period_ns)
        pending.setdefault(k, {})[topics[message.topic]] = timestamp_ns
        if len(pending[k]) == len(args.cameras):
            tick = pending.pop(k)
            row = [tick[cam] for cam in args.cameras]
            rows.append(row)
            print(f"tick {k}: spread={(max(row) - min(row)) / 1e6:.3f} ms")
        for old in [key for key in pending if key < k - MAX_PENDING_TICKS]:
            del pending[old]

    samples = np.array(rows, dtype=np.float64)
    spread_ms = (samples.max(axis=1) - samples.min(axis=1)) / 1e6
    # same convention of the sync service: how much each camera captures
    # before the latest one
    lag_ms = (samples.max(axis=1, keepdims=True) - samples) / 1e6
    print(f"\nspread between cameras over {len(rows)} ticks:")
    print(f"  median={np.median(spread_ms):.3f} ms  p95={np.percentile(spread_ms, 95):.3f} ms"
          f"  max={spread_ms.max():.3f} ms")
    print("median time before the latest camera:")
    for i, cam in enumerate(args.cameras):
        print(f"  CameraGateway.{cam}: {np.median(lag_ms[:, i]):.3f} ms")


if __name__ == "__main__":
    main()
