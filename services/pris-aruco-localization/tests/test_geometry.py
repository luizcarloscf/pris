import numpy as np
import pytest
from pris_msgs.camera_pb2 import FrameTransformation
from pris_msgs.utils.tensor import to_array, to_tensor

from pris_aruco_localization.geometry import (
    Camera,
    Observation,
    camera_from_calibration,
    extrinsic_from,
    invert,
    kabsch,
    localize,
    marker_corners,
    to_matrix,
    transform,
    triangulate,
    undistort,
)

WORLD = 1000
LENGTH = 0.2
MAX_CAMERA_ERROR = 5.0


# Calibrations


def test_camera_from_calibration(cameras):
    camera = cameras[1]
    assert camera.id == 1
    assert (camera.width, camera.height) == (1288, 728)
    assert camera.intrinsic.shape == (3, 3)
    assert camera.distortion.shape == (5,)
    assert camera.extrinsic.shape == (4, 4)


def test_calibration_without_the_reference_frame(scene):
    with pytest.raises(ValueError, match="no extrinsic from frame 1002"):
        camera_from_calibration(scene.load(0), 1002)


def test_extrinsic_from(scene):
    calibration = scene.load(0)
    extrinsic = extrinsic_from(calibration, WORLD)
    assert (extrinsic.source, extrinsic.target) == (WORLD, 0)
    assert extrinsic_from(calibration, 2000) is None


def test_an_extrinsic_from_another_world(scene):
    calibration = scene.load(0)
    world_to_corridor = to_matrix([0, 0, np.pi / 2], [10, 0, 0])
    corridor_to_camera = to_array(extrinsic_from(calibration, WORLD).tf) @ invert(
        world_to_corridor)
    composed = FrameTransformation(source=2000, target=0, tf=to_tensor(corridor_to_camera))

    camera = camera_from_calibration(calibration, 2000, composed)

    np.testing.assert_allclose(camera.extrinsic, corridor_to_camera)
    np.testing.assert_allclose(
        camera_from_calibration(calibration, WORLD, composed).extrinsic, corridor_to_camera)


def test_calibration_with_bad_matrices(scene):
    calibration = scene.load(0)
    calibration.intrinsic.CopyFrom(to_tensor(np.eye(4)))
    with pytest.raises(ValueError, match="3x3"):
        camera_from_calibration(calibration, WORLD)


def test_extrinsic_must_end_at_the_camera(scene):
    calibration = scene.load(0)
    calibration.extrinsic.append(FrameTransformation(target=7, tf=to_tensor(np.eye(4))))
    calibration.extrinsic[-1].source = 1002
    with pytest.raises(ValueError):
        camera_from_calibration(calibration, 1002)


def test_scaled_intrinsics_follow_the_resolution(cameras):
    camera = cameras[0]
    half = camera.scaled(camera.width // 2, camera.height // 2)
    np.testing.assert_allclose(half.intrinsic[:2], camera.intrinsic[:2] / 2)
    np.testing.assert_allclose(half.intrinsic[2], [0, 0, 1])
    assert camera.scaled(camera.width, camera.height) is camera
    # the same ray: a point at half the pixel coordinates undistorts the same
    point = np.array([[400.0, 300.0]])
    np.testing.assert_allclose(undistort(half, point / 2), undistort(camera, point), atol=1e-9)


# Building blocks


def test_triangulate_known_points(cameras):
    points = np.array([[0.0, 0.0, 0.0], [0.5, -0.3, 1.2], [-1.0, 0.8, 0.1]])
    extrinsics = np.stack([camera.extrinsic for camera in cameras])
    normalized = np.stack([
        transform(camera.extrinsic, points)[:, :2] / transform(camera.extrinsic, points)[:, 2:]
        for camera in cameras])
    np.testing.assert_allclose(triangulate(extrinsics, normalized), points, atol=1e-9)
    np.testing.assert_allclose(triangulate(extrinsics[:2], normalized[:2]), points, atol=1e-9)


def test_kabsch_recovers_a_transformation():
    rng = np.random.default_rng(1)
    model = rng.normal(size=(6, 3))
    expected = to_matrix(rng.normal(size=3), rng.normal(size=3))
    np.testing.assert_allclose(kabsch(model, transform(expected, model)), expected, atol=1e-9)


def test_kabsch_never_reflects():
    model = marker_corners(1.0)
    mirrored = model * [1.0, -1.0, 1.0]     # a reflection of the planar model
    for points in (mirrored, mirrored + np.random.default_rng(2).normal(0, 0.05, (4, 3))):
        rotation = kabsch(model, points)[:3, :3]
        assert np.linalg.det(rotation) == pytest.approx(1.0)
        np.testing.assert_allclose(rotation @ rotation.T, np.eye(3), atol=1e-9)


def test_invert_and_to_matrix():
    matrix = to_matrix([0.1, -0.2, 0.3], [1.0, 2.0, 3.0])
    np.testing.assert_allclose(invert(matrix) @ matrix, np.eye(4), atol=1e-12)


# Localization


@pytest.mark.parametrize("ids", [(0,), (1,), (2,), (3,), (0, 2), (1, 3), (0, 1, 2, 3)])
def test_exact_poses_without_noise(cameras, ids, scene):
    pose = scene.marker_pose(0.3, -0.2, 0.8, 0.3, -0.2, 1.0)
    observations = [Observation(cameras[i], scene.pixels(cameras[i], pose)) for i in ids]
    assert all(scene.visible(o.camera, o.corners) for o in observations)

    estimate = localize(observations, LENGTH, MAX_CAMERA_ERROR)

    translation, rotation = scene.errors(estimate, pose)
    assert translation < 1e-6
    assert rotation < 1e-6
    assert estimate.camera_ids == ids
    assert estimate.error < 1e-4
    assert estimate.rejected == ()


def test_detection_resolution_differs_from_calibration(cameras, scene):
    pose = scene.marker_pose(0.0, 0.0, 0.5)
    half = [camera.scaled(camera.width // 2, camera.height // 2) for camera in cameras]
    observations = [Observation(camera, scene.pixels(camera, pose)) for camera in half]

    translation, rotation = scene.errors(localize(observations, LENGTH, MAX_CAMERA_ERROR), pose)
    assert translation < 1e-6 and rotation < 1e-6


def test_multi_view_beats_a_single_camera_with_noise(cameras, scene):
    rng = np.random.default_rng(3)
    single, multi = [], []
    for pose in scene.random_poses(200, seed=4):
        observations = [Observation(c, scene.pixels(c, pose) + rng.normal(0, 0.5, (4, 2)))
                        for c in cameras]
        if not all(scene.visible(o.camera, o.corners, pose) for o in observations):
            continue
        multi.append(scene.errors(localize(observations, LENGTH, MAX_CAMERA_ERROR), pose))
        single.append(scene.errors(localize(observations[:1], LENGTH, MAX_CAMERA_ERROR), pose))
    assert len(multi) > 30
    single_t, single_r = np.median(single, axis=0)
    multi_t, multi_r = np.median(multi, axis=0)
    # 0.2 m marker at ~5 m, 0.5 px noise: centimeters alone, millimeters together
    # (measured: 54 mm / 2.0 deg alone, 1.1 mm / 0.6 deg with 4 cameras)
    assert multi_t < 0.005
    assert multi_t < single_t / 10
    assert multi_r < single_r / 2.5
    # a single camera sometimes picks the flipped orientation; together, never
    assert np.percentile(multi, 95, axis=0)[1] < np.radians(3)
    assert np.percentile(single, 95, axis=0)[1] > np.radians(30)


def test_a_camera_with_wrong_corners_is_rejected(cameras, scene):
    pose = scene.marker_pose(-0.4, 0.5, 0.3, 0.0, 0.4, -0.7)
    observations = [Observation(c, scene.pixels(c, pose)) for c in cameras]
    # camera 2 reports the corners of another marker 30 px away
    observations[2] = Observation(cameras[2], observations[2].corners + [30.0, -20.0])

    estimate = localize(observations, LENGTH, MAX_CAMERA_ERROR)

    assert estimate.rejected == (2,)
    assert estimate.camera_ids == (0, 1, 3)
    translation, rotation = scene.errors(estimate, pose)
    assert translation < 1e-6 and rotation < 1e-6


def test_corners_in_the_wrong_order_are_rejected(cameras, scene):
    pose = scene.marker_pose(0.2, 0.2, 0.2, 0.0, 0.0, 0.5)
    observations = [Observation(c, scene.pixels(c, pose)) for c in cameras]
    observations[0] = Observation(cameras[0], np.roll(observations[0].corners, 1, axis=0))

    estimate = localize(observations, LENGTH, MAX_CAMERA_ERROR)

    assert estimate.rejected == (0,)
    assert scene.errors(estimate, pose)[0] < 1e-6


def test_noise_within_the_threshold_keeps_every_camera(cameras, scene):
    rng = np.random.default_rng(5)
    pose = scene.marker_pose(0.0, 0.0, 0.5, 0.2, 0.1, 0.0)
    observations = [Observation(c, scene.pixels(c, pose) + rng.normal(0, 1.0, (4, 2)))
                    for c in cameras]

    estimate = localize(observations, LENGTH, MAX_CAMERA_ERROR)

    assert estimate.rejected == ()
    assert set(estimate.camera_errors) == {0, 1, 2, 3}
    assert 0.3 < estimate.error < 3.0


def test_marker_length_scales_the_pose(cameras, scene):
    pose = scene.marker_pose(0.5, 0.5, 0.0)
    observations = [Observation(c, scene.pixels(c, pose, length=0.5)) for c in cameras]
    assert scene.errors(localize(observations, 0.5, MAX_CAMERA_ERROR), pose)[0] < 1e-6
    # a wrong length puts the marker at the wrong place, not at the right one
    assert scene.errors(localize(observations, 0.25, MAX_CAMERA_ERROR), pose)[0] > 0.01


def test_no_observations():
    assert localize([], LENGTH, MAX_CAMERA_ERROR) is None


def edge_on_pose(camera, center):
    """Marker at `center` whose plane contains camera's ray to it."""
    ray = center - invert(camera.extrinsic)[:3, 3]
    ray /= np.linalg.norm(ray)
    z = np.cross(ray, [0.0, 0.0, 1.0])
    z /= np.linalg.norm(z)
    y = np.cross(z, ray)
    pose = np.eye(4)
    pose[:3, :3] = np.stack([np.cross(y, z), y, z], axis=1)
    pose[:3, 3] = center
    return pose


def test_a_marker_seen_edge_on(cameras, scene):
    pose = edge_on_pose(cameras[0], np.array([0.0, 0.0, 0.5]))
    observations = [Observation(c, scene.pixels(c, pose)) for c in cameras]
    # alone, camera 0 sees almost collinear corners: no pose in front of it
    assert localize(observations[:1], LENGTH, MAX_CAMERA_ERROR) is None
    # the other cameras fix it, and camera 0 still agrees with the result
    estimate = localize(observations, LENGTH, MAX_CAMERA_ERROR)
    assert estimate.rejected == ()
    assert scene.errors(estimate, pose)[0] < 1e-6


def test_scaled_copies_the_intrinsic():
    camera = Camera(id=9, intrinsic=np.eye(3), distortion=np.zeros(5), extrinsic=np.eye(4),
                    width=10, height=10)
    assert camera.scaled(20, 20).intrinsic is not camera.intrinsic
