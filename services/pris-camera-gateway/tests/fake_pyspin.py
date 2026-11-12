"""Minimal stand-in for PySpin, enough to run SpinnakerCamera without the SDK or a camera.

Node maps record every write, so tests can check which nodes were set and in which order.
"""
from typing import Any, Callable, Dict, List, Set, Tuple
from unittest.mock import MagicMock


class SpinnakerException(Exception):
    pass


class FakeNode:

    def __init__(self, name: str, node_map: "FakeNodeMap") -> None:
        self.name = name
        self.node_map = node_map
        self.value: Any = 0.0
        self.executed = 0


class FakeNodeMap:

    def __init__(self) -> None:
        self.nodes: Dict[str, FakeNode] = {}
        self.writes: List[Tuple[str, Any]] = []
        # nodes the camera doesn't have: using them raises, as in the SDK
        self.missing: Set[str] = set()
        # commands that do something when executed
        self.on_execute: Dict[str, Callable[[], None]] = {}

    def GetNode(self, name: str) -> FakeNode:
        if name not in self.nodes:
            self.nodes[name] = FakeNode(name, self)
        return self.nodes[name]

    def value(self, name: str) -> Any:
        return self.GetNode(name).value


class _Entry:

    def __init__(self, symbolic: str) -> None:
        self._symbolic = symbolic

    def GetValue(self) -> str:
        return self._symbolic

    def GetSymbolic(self) -> str:
        return self._symbolic


class _ValuePtr:

    def __init__(self, node: FakeNode) -> None:
        self._node = node

    def _check(self) -> None:
        if self._node.name in self._node.node_map.missing:
            raise SpinnakerException(f"node '{self._node.name}' not available")

    def GetValue(self) -> Any:
        self._check()
        return self._node.value

    def SetValue(self, value: Any) -> None:
        self._check()
        self._node.value = value
        self._node.node_map.writes.append((self._node.name, value))

    def GetMin(self) -> float:
        return -1e12

    def GetMax(self) -> float:
        return 1e12


class CBooleanPtr(_ValuePtr):
    pass


class CIntegerPtr(_ValuePtr):
    pass


class CFloatPtr(_ValuePtr):
    pass


class CStringPtr(_ValuePtr):
    pass


class CEnumerationPtr(_ValuePtr):

    def GetEntryByName(self, name: str) -> _Entry:
        return _Entry(name)

    def SetIntValue(self, value: str) -> None:
        self.SetValue(value)

    def GetCurrentEntry(self) -> _Entry:
        self._check()
        return _Entry(self._node.value)


class CCommandPtr(_ValuePtr):

    def Execute(self) -> None:
        self._check()
        action = self._node.node_map.on_execute.get(self._node.name)
        if action is not None:
            action()
        self._node.executed += 1
        self._node.node_map.writes.append((self._node.name, "Execute"))


class FakeImage:

    def __init__(self, timestamp_ns: int = 0, incomplete: bool = False) -> None:
        self.timestamp_ns = timestamp_ns
        self.incomplete = incomplete
        self.released = False

    def IsIncomplete(self) -> bool:
        return self.incomplete

    def GetImageStatus(self) -> int:
        return 1

    def GetTimeStamp(self) -> int:
        return self.timestamp_ns

    def GetNDArray(self) -> Any:
        import numpy as np
        return np.zeros((8, 8, 3), dtype=np.uint8)

    def Release(self) -> None:
        self.released = True


class FakeCamera:

    def __init__(self, ip: int = 0x0A140600, model: str = "Blackfly BFLY-PGE-09S2C") -> None:
        self.node_map = FakeNodeMap()
        self.stream_node_map = FakeNodeMap()
        self.device_node_map = FakeNodeMap()
        self.device_node_map.GetNode("GevDeviceIPAddress").value = ip
        self.device_node_map.GetNode("DeviceModelName").value = model
        self.streaming = False
        # GetTimeStamp() of the next image: nanoseconds of the camera clock
        self.image_timestamp_ns: Callable[[], int] = lambda: 0
        self.incomplete = False
        self.timeout = False
        self.images: List[FakeImage] = []

    def GetNodeMap(self) -> FakeNodeMap:
        return self.node_map

    def GetTLStreamNodeMap(self) -> FakeNodeMap:
        return self.stream_node_map

    def GetTLDeviceNodeMap(self) -> FakeNodeMap:
        return self.device_node_map

    def Init(self) -> None:
        pass

    def DeInit(self) -> None:
        pass

    def UserSetLoad(self) -> None:
        pass

    def IsStreaming(self) -> bool:
        return self.streaming

    def BeginAcquisition(self) -> None:
        self.streaming = True

    def EndAcquisition(self) -> None:
        self.streaming = False

    def GetNextImage(self, timeout_ms: int) -> FakeImage:
        if self.timeout:
            raise SpinnakerException("timeout")
        image = FakeImage(self.image_timestamp_ns(), self.incomplete)
        self.images.append(image)
        return image


class FakeCameraList:

    def __init__(self, cameras: List[FakeCamera]) -> None:
        self.cameras = cameras

    def GetSize(self) -> int:
        return len(self.cameras)

    def GetByIndex(self, index: int) -> FakeCamera:
        return self.cameras[index]

    def Clear(self) -> None:
        pass


INodeMap = FakeNodeMap
CameraPtr = FakeCamera
ImagePtr = FakeImage
System = MagicMock()
ImageProcessor = MagicMock


def __getattr__(name: str) -> Any:
    # SDK constants (e.g. SPINNAKER_COLOR_PROCESSING_ALGORITHM_*, PixelFormat_*)
    return name
