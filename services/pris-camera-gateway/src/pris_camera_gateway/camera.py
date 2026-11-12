"""A Blackfly or Blackfly S GigE camera through the Spinnaker SDK, used from a single thread."""

from __future__ import annotations

import ipaddress
import time
from typing import NamedTuple

import cv2
import numpy as np
import numpy.typing as npt
import PySpin
from google.protobuf.wrappers_pb2 import FloatValue
from pris_msgs.camera_pb2 import CameraSetting
from pris_msgs.image_pb2 import BoundingPoly, ColorSpace, ColorSpaces, Image, ImageFormat
from pris_msgs.image_pb2 import ImageFormats
from pris_msgs.utils.image import to_image
from pris_wire.core import Logger, StatusCode

from pris_camera_gateway import nodes
from pris_camera_gateway.clock import ClockMapper, LatchSample
from pris_camera_gateway.conf.options_pb2 import CameraOptions, ColorProcessingAlgorithm
from pris_camera_gateway.conf.options_pb2 import TriggerMode
from pris_camera_gateway.nodes import StatusException
from pris_camera_gateway.schedule import normalize_delay, rebase_delay


class Capture(NamedTuple):
    """An encoded image and its capture instant in the host clock."""

    image: Image
    timestamp_ns: int


class SpinnakerCamera(object):
    """Connects to the camera of `options.ip`, triggers and grabs its images, and reads and
    changes its settings.

    Nothing runs in the background: the caller grabs each image, so settings never change
    while an image is being grabbed.
    """

    log = Logger("SpinnakerCamera")

    def __init__(self, options: CameraOptions) -> None:
        """Get the Spinnaker system; nothing is connected before `connect`.

        Args:
            options: the camera's options.
        """
        self.options = options
        self.scheduled = options.trigger_mode == TriggerMode.SOFTWARE_SCHEDULED
        self.period_ns = 0
        self.delay_ns = 0
        self.color_space = ColorSpaces.RGB
        self.image_format = ImageFormats.JPEG
        self.compression = 0.8
        self.mapper: ClockMapper | None = None
        self.ns_per_tick = 1.0
        self.model = ""
        self.system = PySpin.System.GetInstance()
        self.processor = PySpin.ImageProcessor()
        name = ColorProcessingAlgorithm.Name(options.algorithm)
        if options.onboard_color_processing:
            name = "NONE"
        self.processor.SetColorProcessing(
            getattr(PySpin, "SPINNAKER_COLOR_PROCESSING_ALGORITHM_" + name)
        )
        self.camera: PySpin.CameraPtr = None

    def connect(self) -> None:
        """Connect, load the camera's `Default` user set, set the trigger, the stream and the
        network options, then map the camera clock to the host's.

        Raises:
            RuntimeError: no camera has the IP of the options, or it can't be initialized.
        """
        self.camera = self._find(self.options.ip)
        try:
            self.camera.Init()
        except PySpin.SpinnakerException as ex:
            raise RuntimeError(f"can't initialize the camera at {self.options.ip}: {ex}")
        self.model = nodes.get_str(self.camera.GetTLDeviceNodeMap(), "DeviceModelName")
        node_map, stream = self.camera.GetNodeMap(), self.camera.GetTLStreamNodeMap()
        nodes.set_enum(node_map, "UserSetSelector", "Default")
        self.camera.UserSetLoad()
        nodes.set_enum(node_map, "TriggerMode", "Off")
        nodes.set_enum(node_map, "AcquisitionMode", "Continuous")
        nodes.set_enum(stream, "StreamBufferHandlingMode", "NewestOnly")
        if self.scheduled:
            # ! TriggerSelector and TriggerSource only change while TriggerMode is off
            nodes.set_enum(node_map, "TriggerSelector", "FrameStart")
            nodes.set_enum(node_map, "TriggerSource", "Software")
            nodes.set_enum(node_map, "TriggerMode", "On")
        for map_, name, value in (
            (node_map, "ReverseX", self.options.reverse_x),
            (node_map, "GevSCPSPacketSize", self.options.packet_size),
            (node_map, "GevSCPD", self.options.packet_delay),
            (stream, "StreamPacketResendEnable", self.options.packet_resend),
            (stream, "StreamPacketResendTimeout", self.options.packet_resend_timeout),
            (stream, "StreamPacketResendMaxRequests", self.options.packet_resend_max_requests),
        ):
            try:
                if isinstance(value, bool):
                    nodes.set_bool(map_, name, value)
                else:
                    nodes.set_int(map_, name, value)
            except StatusException as ex:
                self.log.warn("{}: {}", name, ex)
        self._start_clock_mapping()
        self.log.info("Connected to {} at {}", self.model, self.options.ip)

    def disconnect(self) -> None:
        """Stop streaming and release the camera and the Spinnaker system."""
        try:
            self.stop()
            self.camera.DeInit()
            self.camera = None
            self.system.ReleaseInstance()
        except PySpin.SpinnakerException as ex:
            self.log.warn("Disconnect: {}", ex)

    def start(self) -> None:
        """Start streaming."""
        if not self.camera.IsStreaming():
            self.camera.BeginAcquisition()

    def stop(self) -> None:
        """Stop streaming."""
        if self.camera.IsStreaming():
            self.camera.EndAcquisition()

    def trigger(self) -> None:
        """Trigger a capture now (SOFTWARE_SCHEDULED)."""
        try:
            nodes.execute(self.camera.GetNodeMap(), "TriggerSoftware")
        except StatusException as ex:
            self.log.warn("Trigger: {}", ex)

    def grab(self, timeout_ms: int) -> Capture | None:
        """Wait for the next image and encode it.

        Args:
            timeout_ms: the most milliseconds to wait.

        Returns:
            The image and its capture instant, or None when no complete image arrived in time
            or it couldn't be encoded.
        """
        try:
            image = self.camera.GetNextImage(timeout_ms)
        except PySpin.SpinnakerException as ex:
            self.log.warn("No image in {} ms: {}", timeout_ms, ex)
            return None
        try:
            timestamp_ns = time.time_ns()
            if self.mapper is not None and self.mapper.ready:
                # * GetTimeStamp() is in nanoseconds of the camera clock, the latch in ticks
                # ? whether it marks the start of the exposure: check on both camera families
                ticks = round(image.GetTimeStamp() / self.ns_per_tick)
                timestamp_ns = self.mapper.to_host_ns(ticks)
            if image.IsIncomplete():
                self.log.warn("Incomplete image, status {}", image.GetImageStatus())
                return None
            encoded = self._encode(image)
            return None if encoded is None else Capture(encoded, timestamp_ns)
        finally:
            image.Release()

    def sync_clock(self) -> None:
        """Estimate the camera clock against the host's again; nothing without latch nodes."""
        if self.mapper is None:
            return
        try:
            self.mapper.update([self._latch() for _ in range(self.options.latch_samples)])
        except StatusException as ex:
            self.log.warn("Clock: {}", ex)

    def get_sampling_rate(self) -> FloatValue:
        if self.scheduled:
            return FloatValue(value=1e9 / self.period_ns if self.period_ns else 0.0)
        return FloatValue(value=nodes.get_float(self.camera.GetNodeMap(), "AcquisitionFrameRate"))

    def set_sampling_rate(self, rate: FloatValue) -> None:
        if self.scheduled:
            if rate.value <= 0:
                raise StatusException(
                    StatusCode.INVALID_ARGUMENT, "'frequency' must be greater than zero"
                )
            period_ns = round(1e9 / rate.value)
            self.delay_ns = rebase_delay(self.delay_ns, period_ns)
            self.period_ns = period_ns
            return
        node_map = self.camera.GetNodeMap()
        if "BFS" in self.model:
            nodes.set_bool(node_map, "AcquisitionFrameRateEnable", True)
        else:
            nodes.set_enum(node_map, "AcquisitionFrameRateAuto", "Off")
            nodes.set_bool(node_map, "AcquisitionFrameRateEnabled", True)
        nodes.set_float(node_map, "AcquisitionFrameRate", rate.value)

    def get_delay(self) -> FloatValue:
        return FloatValue(value=self.delay_ns / 1e9)

    def set_delay(self, delay: FloatValue) -> None:
        if not self.scheduled:
            raise StatusException(
                StatusCode.FAILED_PRECONDITION,
                "'delay' requires trigger_mode SOFTWARE_SCHEDULED",
            )
        try:
            self.delay_ns = normalize_delay(round(delay.value * 1e9), self.period_ns)
        except ValueError as ex:
            raise StatusException(StatusCode.INVALID_ARGUMENT, str(ex))

    def get_format(self) -> ImageFormat:
        result = ImageFormat(format=self.image_format)
        result.compression.value = self.compression
        return result

    def set_format(self, image_format: ImageFormat) -> None:
        if image_format.format not in (ImageFormats.JPEG, ImageFormats.PNG, ImageFormats.WebP):
            raise StatusException(
                StatusCode.INVALID_ARGUMENT,
                "'format' must be JPEG, PNG or WebP",
            )
        if not 0 < image_format.compression.value < 1:
            raise StatusException(
                StatusCode.INVALID_ARGUMENT, "'compression' must be between 0 and 1"
            )
        self.image_format = image_format.format
        self.compression = image_format.compression.value

    def get_color_space(self) -> ColorSpace:
        return ColorSpace(value=self.color_space)

    def set_color_space(self, color_space: ColorSpace) -> None:
        self._check_stopped("color_space")
        if color_space.value == ColorSpaces.RGB:
            pixel_format = "RGB8Packed" if self.options.onboard_color_processing else "BayerRG8"
        elif color_space.value == ColorSpaces.GRAY:
            pixel_format = "Mono8"
        else:
            raise StatusException(
                StatusCode.INVALID_ARGUMENT,
                "'color_space' must be RGB or GRAY",
            )
        nodes.set_enum(self.camera.GetNodeMap(), "PixelFormat", pixel_format)
        self.color_space = color_space.value

    def get_region(self) -> BoundingPoly:
        node_map = self.camera.GetNodeMap()
        x, y = nodes.get_int(node_map, "OffsetX"), nodes.get_int(node_map, "OffsetY")
        region = BoundingPoly()
        region.vertices.add(x=x, y=y)
        region.vertices.add(
            x=x + nodes.get_int(node_map, "Width"), y=y + nodes.get_int(node_map, "Height")
        )
        return region

    def set_region(self, region: BoundingPoly) -> None:
        self._check_stopped("region")
        if len(region.vertices) != 2:
            raise StatusException(
                StatusCode.INVALID_ARGUMENT,
                "'region' must have 2 vertices",
            )
        top_left, bottom_right = region.vertices
        if top_left.x >= bottom_right.x or top_left.y >= bottom_right.y:
            raise StatusException(
                StatusCode.INVALID_ARGUMENT,
                "'region' must go from its top-left to its bottom-right vertex",
            )
        node_map = self.camera.GetNodeMap()
        width = min(int(bottom_right.x - top_left.x), nodes.get_int(node_map, "WidthMax"))
        height = min(int(bottom_right.y - top_left.y), nodes.get_int(node_map, "HeightMax"))
        nodes.set_int(node_map, "Width", width)
        nodes.set_int(node_map, "Height", height)
        for name, value in (("OffsetX", top_left.x), ("OffsetY", top_left.y)):
            nodes.set_int(node_map, name, min(nodes.range_int(node_map, name)[1], int(value)))

    def get_brightness(self) -> CameraSetting:
        return CameraSetting(automatic=False, ratio=self._get_ratio("BlackLevel"))

    def set_brightness(self, setting: CameraSetting) -> None:
        self._set_ratio("BlackLevel", setting.ratio)

    def get_gain(self) -> CameraSetting:
        return self._get_auto("GainAuto", "Gain")

    def set_gain(self, setting: CameraSetting) -> None:
        self._set_auto("GainAuto", "Gain", setting)

    def get_shutter(self) -> CameraSetting:
        return self._get_auto("ExposureAuto", "ExposureTime")

    def set_shutter(self, setting: CameraSetting) -> None:
        self._set_auto("ExposureAuto", "ExposureTime", setting)

    def get_white_balance_rv(self) -> CameraSetting:
        return self._get_white_balance("Red")

    def set_white_balance_rv(self, setting: CameraSetting) -> None:
        self._set_white_balance("Red", setting)

    def get_white_balance_bu(self) -> CameraSetting:
        return self._get_white_balance("Blue")

    def set_white_balance_bu(self, setting: CameraSetting) -> None:
        self._set_white_balance("Blue", setting)

    def _find(self, ip: str) -> PySpin.CameraPtr:
        cameras = self.system.GetCameras()
        try:
            for index in range(cameras.GetSize()):
                camera = cameras.GetByIndex(index)
                try:
                    address = nodes.get_int(camera.GetTLDeviceNodeMap(), "GevDeviceIPAddress")
                except StatusException:
                    continue
                if str(ipaddress.ip_address(address)) == ip:
                    return camera
        finally:
            cameras.Clear()
        raise RuntimeError(f"no camera at {ip}")

    def _start_clock_mapping(self) -> None:
        try:
            frequency = nodes.get_int(self.camera.GetNodeMap(), "GevTimestampTickFrequency")
            self._latch()
        except StatusException as ex:
            self.log.warn("No timestamp latch, frames are stamped on arrival: {}", ex)
            return
        if frequency <= 0:
            self.log.warn("Tick frequency {}, frames are stamped on arrival", frequency)
            return
        self.ns_per_tick = 1e9 / frequency
        self.mapper = ClockMapper(self.ns_per_tick)
        self.sync_clock()

    def _latch(self) -> LatchSample:
        node_map = self.camera.GetNodeMap()
        before = time.time_ns()
        nodes.execute(node_map, "TimestampLatch")
        after = time.time_ns()
        return LatchSample(before, nodes.get_int(node_map, "TimestampLatchValue"), after)

    def _to_array(self, image: PySpin.ImagePtr) -> npt.NDArray[np.uint8]:
        if self.options.onboard_color_processing:
            return image.GetNDArray()
        pixel_format = (
            PySpin.PixelFormat_BGR8
            if self.color_space == ColorSpaces.RGB
            else PySpin.PixelFormat_Mono8
        )
        return self.processor.Convert(image, pixel_format).GetNDArray()

    def _encode(self, image: PySpin.ImagePtr) -> Image | None:
        try:
            return to_image(
                self._to_array(image),
                self.image_format,
                self.compression,
                turbojpeg=self.options.use_turbojpeg,
            )
        except (ValueError, cv2.error, OSError) as ex:
            self.log.warn("Can't encode the image: {}", ex)
            return None

    def _check_stopped(self, name: str) -> None:
        if self.camera.IsStreaming():
            raise StatusException(
                StatusCode.FAILED_PRECONDITION,
                f"'{name}' can't change while streaming",
            )

    def _get_ratio(self, name: str) -> float:
        node_map = self.camera.GetNodeMap()
        low, high = nodes.range_float(node_map, name)
        return (nodes.get_float(node_map, name) - low) / (high - low)

    def _set_ratio(self, name: str, ratio: float) -> None:
        node_map = self.camera.GetNodeMap()
        low, high = nodes.range_float(node_map, name)
        nodes.set_float(node_map, name, low + ratio * (high - low))

    def _get_auto(self, auto: str, name: str) -> CameraSetting:
        automatic = nodes.get_enum(self.camera.GetNodeMap(), auto) == "Continuous"
        return CameraSetting(automatic=automatic, ratio=self._get_ratio(name))

    def _set_auto(self, auto: str, name: str, setting: CameraSetting) -> None:
        node_map = self.camera.GetNodeMap()
        if setting.automatic:
            nodes.set_enum(node_map, auto, "Continuous")
            return
        nodes.set_enum(node_map, auto, "Off")
        self._set_ratio(name, setting.ratio)

    def _get_white_balance(self, channel: str) -> CameraSetting:
        self._check_color("white_balance")
        node_map = self.camera.GetNodeMap()
        if nodes.get_enum(node_map, "BalanceWhiteAuto") == "Continuous":
            return CameraSetting(automatic=True)
        nodes.set_enum(node_map, "BalanceRatioSelector", channel)
        return CameraSetting(automatic=False, ratio=self._get_ratio("BalanceRatio"))

    def _set_white_balance(self, channel: str, setting: CameraSetting) -> None:
        self._check_color("white_balance")
        node_map = self.camera.GetNodeMap()
        if setting.automatic:
            nodes.set_enum(node_map, "BalanceWhiteAuto", "Continuous")
            return
        nodes.set_enum(node_map, "BalanceWhiteAuto", "Off")
        nodes.set_enum(node_map, "BalanceRatioSelector", channel)
        self._set_ratio("BalanceRatio", setting.ratio)

    def _check_color(self, name: str) -> None:
        if self.color_space != ColorSpaces.RGB:
            raise StatusException(
                StatusCode.FAILED_PRECONDITION,
                f"'{name}' needs the RGB color space",
            )
