import os
import uuid
from pathlib import Path
from types import SimpleNamespace

import cv2
import numpy as np
import pytest
from google.protobuf.json_format import Parse
from pris_msgs.camera_pb2 import CameraCalibration
from pris_wire.core import Channel
from opentelemetry.instrumentation.pris_wire.otlp import install
from opentelemetry.test.globals_test import reset_metrics_globals, reset_trace_globals
from opentelemetry.test.test_base import TestBase

from pris_aruco_localization.geometry import (
    camera_from_calibration,
    invert,
    marker_corners,
    transform,
)

URI = os.getenv("WIRE_RABBITMQ_URI", "amqp://guest:guest@localhost:5672")
LABVISIO = Path(__file__).parents[3] / "calibrations" / "labvisio"
WORLD = 1000
LENGTH = 0.2


def load(id):
    return Parse((LABVISIO / "{}.json".format(id)).read_text(), CameraCalibration())


def pixels(camera, pose, length=LENGTH):
    """4x2 pixel corners of a marker at `pose`, distortion included."""
    world = transform(pose, marker_corners(length))
    rotation, _ = cv2.Rodrigues(camera.extrinsic[:3, :3])
    projected, _ = cv2.projectPoints(world, rotation, camera.extrinsic[:3, 3],
                                     camera.intrinsic, camera.distortion)
    return projected.reshape(4, 2)


def marker_pose(x, y, z, roll=0.0, pitch=0.0, yaw=0.0):
    """Marker facing up (z out of the marker = world z), then rotated."""
    rotation, _ = cv2.Rodrigues(np.array([roll, pitch, yaw], dtype=np.float64))
    pose = np.eye(4)
    pose[:3, :3] = rotation
    pose[:3, 3] = [x, y, z]
    return pose


def visible(camera, corners, pose=None, max_angle=np.radians(75)):
    """Corners inside the image and, given the pose, the marker facing the
    camera by less than `max_angle` (beyond that a detector can't decode it,
    and seen edge-on its corners are almost collinear)."""
    inside = ((corners >= 0).all() and (corners[:, 0] < camera.width).all()
              and (corners[:, 1] < camera.height).all())
    if pose is None:
        return inside
    to_camera = invert(camera.extrinsic)[:3, 3] - pose[:3, 3]
    facing = pose[:3, 2] @ to_camera / np.linalg.norm(to_camera)
    return inside and facing > np.cos(max_angle)


def errors(estimate, pose):
    """(translation error in m, rotation error in rad)."""
    delta = invert(pose) @ estimate.pose
    angle = np.arccos(np.clip((np.trace(delta[:3, :3]) - 1) / 2, -1, 1))
    return np.linalg.norm(estimate.pose[:3, 3] - pose[:3, 3]), angle


def random_poses(count, seed):
    rng = np.random.default_rng(seed)
    return [marker_pose(*rng.uniform(-1.0, 1.0, 2), rng.uniform(0.0, 1.0),
                        *rng.uniform(-0.6, 0.6, 2), rng.uniform(-np.pi, np.pi))
            for _ in range(count)]


@pytest.fixture(scope="session")
def cameras():
    """The 4 labvisio cameras, extrinsics from the world frame 1000."""
    return [camera_from_calibration(load(id), WORLD) for id in range(4)]


@pytest.fixture
def scene():
    """Helpers to build synthetic observations from the labvisio calibrations."""
    return SimpleNamespace(load=load, pixels=pixels, marker_pose=marker_pose, visible=visible,
                           errors=errors, random_poses=random_poses, WORLD=WORLD,
                           LENGTH=LENGTH)


@pytest.fixture
def connect():
    channels = []

    def _connect():
        channel = Channel(URI)
        channels.append(channel)
        return channel

    yield _connect
    for channel in channels:
        channel.close()


@pytest.fixture
def channel(connect):
    return connect()


@pytest.fixture
def topic():
    return "Test.{}".format(uuid.uuid4().hex[:8])


@pytest.fixture
def spans():
    reset_trace_globals()
    reset_metrics_globals()
    tracer_provider, exporter = TestBase.create_tracer_provider()
    meter_provider, _ = TestBase.create_meter_provider()
    shutdown = install(tracer_provider, meter_provider)
    yield exporter
    shutdown()
    reset_trace_globals()
    reset_metrics_globals()
