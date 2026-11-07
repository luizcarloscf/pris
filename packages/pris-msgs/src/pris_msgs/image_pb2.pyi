from google.protobuf import wrappers_pb2 as _wrappers_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class ImageFormats(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    PNG: _ClassVar[ImageFormats]
    JPEG: _ClassVar[ImageFormats]
    WebP: _ClassVar[ImageFormats]

class ColorSpaces(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    RGB: _ClassVar[ColorSpaces]
    GRAY: _ClassVar[ColorSpaces]
    YCbCr: _ClassVar[ColorSpaces]
    HSV: _ClassVar[ColorSpaces]

class HumanKeypoints(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    UNKNOWN_HUMAN_KEYPOINT: _ClassVar[HumanKeypoints]
    HEAD: _ClassVar[HumanKeypoints]
    NOSE: _ClassVar[HumanKeypoints]
    NECK: _ClassVar[HumanKeypoints]
    RIGHT_SHOULDER: _ClassVar[HumanKeypoints]
    RIGHT_ELBOW: _ClassVar[HumanKeypoints]
    RIGHT_WRIST: _ClassVar[HumanKeypoints]
    LEFT_SHOULDER: _ClassVar[HumanKeypoints]
    LEFT_ELBOW: _ClassVar[HumanKeypoints]
    LEFT_WRIST: _ClassVar[HumanKeypoints]
    RIGHT_HIP: _ClassVar[HumanKeypoints]
    RIGHT_KNEE: _ClassVar[HumanKeypoints]
    RIGHT_ANKLE: _ClassVar[HumanKeypoints]
    LEFT_HIP: _ClassVar[HumanKeypoints]
    LEFT_KNEE: _ClassVar[HumanKeypoints]
    LEFT_ANKLE: _ClassVar[HumanKeypoints]
    RIGHT_EYE: _ClassVar[HumanKeypoints]
    LEFT_EYE: _ClassVar[HumanKeypoints]
    RIGHT_EAR: _ClassVar[HumanKeypoints]
    LEFT_EAR: _ClassVar[HumanKeypoints]
    CHEST: _ClassVar[HumanKeypoints]
    PELVIS: _ClassVar[HumanKeypoints]
    LEFT_BIG_TOE: _ClassVar[HumanKeypoints]
    LEFT_SMALL_TOE: _ClassVar[HumanKeypoints]
    LEFT_HEEL: _ClassVar[HumanKeypoints]
    RIGHT_BIG_TOE: _ClassVar[HumanKeypoints]
    RIGHT_SMALL_TOE: _ClassVar[HumanKeypoints]
    RIGHT_HEEL: _ClassVar[HumanKeypoints]
    FACE_0: _ClassVar[HumanKeypoints]
    FACE_1: _ClassVar[HumanKeypoints]
    FACE_2: _ClassVar[HumanKeypoints]
    FACE_3: _ClassVar[HumanKeypoints]
    FACE_4: _ClassVar[HumanKeypoints]
    FACE_5: _ClassVar[HumanKeypoints]
    FACE_6: _ClassVar[HumanKeypoints]
    FACE_7: _ClassVar[HumanKeypoints]
    FACE_8: _ClassVar[HumanKeypoints]
    FACE_9: _ClassVar[HumanKeypoints]
    FACE_10: _ClassVar[HumanKeypoints]
    FACE_11: _ClassVar[HumanKeypoints]
    FACE_12: _ClassVar[HumanKeypoints]
    FACE_13: _ClassVar[HumanKeypoints]
    FACE_14: _ClassVar[HumanKeypoints]
    FACE_15: _ClassVar[HumanKeypoints]
    FACE_16: _ClassVar[HumanKeypoints]
    FACE_17: _ClassVar[HumanKeypoints]
    FACE_18: _ClassVar[HumanKeypoints]
    FACE_19: _ClassVar[HumanKeypoints]
    FACE_20: _ClassVar[HumanKeypoints]
    FACE_21: _ClassVar[HumanKeypoints]
    FACE_22: _ClassVar[HumanKeypoints]
    FACE_23: _ClassVar[HumanKeypoints]
    FACE_24: _ClassVar[HumanKeypoints]
    FACE_25: _ClassVar[HumanKeypoints]
    FACE_26: _ClassVar[HumanKeypoints]
    FACE_27: _ClassVar[HumanKeypoints]
    FACE_28: _ClassVar[HumanKeypoints]
    FACE_29: _ClassVar[HumanKeypoints]
    FACE_30: _ClassVar[HumanKeypoints]
    FACE_31: _ClassVar[HumanKeypoints]
    FACE_32: _ClassVar[HumanKeypoints]
    FACE_33: _ClassVar[HumanKeypoints]
    FACE_34: _ClassVar[HumanKeypoints]
    FACE_35: _ClassVar[HumanKeypoints]
    FACE_36: _ClassVar[HumanKeypoints]
    FACE_37: _ClassVar[HumanKeypoints]
    FACE_38: _ClassVar[HumanKeypoints]
    FACE_39: _ClassVar[HumanKeypoints]
    FACE_40: _ClassVar[HumanKeypoints]
    FACE_41: _ClassVar[HumanKeypoints]
    FACE_42: _ClassVar[HumanKeypoints]
    FACE_43: _ClassVar[HumanKeypoints]
    FACE_44: _ClassVar[HumanKeypoints]
    FACE_45: _ClassVar[HumanKeypoints]
    FACE_46: _ClassVar[HumanKeypoints]
    FACE_47: _ClassVar[HumanKeypoints]
    FACE_48: _ClassVar[HumanKeypoints]
    FACE_49: _ClassVar[HumanKeypoints]
    FACE_50: _ClassVar[HumanKeypoints]
    FACE_51: _ClassVar[HumanKeypoints]
    FACE_52: _ClassVar[HumanKeypoints]
    FACE_53: _ClassVar[HumanKeypoints]
    FACE_54: _ClassVar[HumanKeypoints]
    FACE_55: _ClassVar[HumanKeypoints]
    FACE_56: _ClassVar[HumanKeypoints]
    FACE_57: _ClassVar[HumanKeypoints]
    FACE_58: _ClassVar[HumanKeypoints]
    FACE_59: _ClassVar[HumanKeypoints]
    FACE_60: _ClassVar[HumanKeypoints]
    FACE_61: _ClassVar[HumanKeypoints]
    FACE_62: _ClassVar[HumanKeypoints]
    FACE_63: _ClassVar[HumanKeypoints]
    FACE_64: _ClassVar[HumanKeypoints]
    FACE_65: _ClassVar[HumanKeypoints]
    FACE_66: _ClassVar[HumanKeypoints]
    FACE_67: _ClassVar[HumanKeypoints]
    LEFT_HAND_ROOT: _ClassVar[HumanKeypoints]
    LEFT_HAND_THUMB_1: _ClassVar[HumanKeypoints]
    LEFT_HAND_THUMB_2: _ClassVar[HumanKeypoints]
    LEFT_HAND_THUMB_3: _ClassVar[HumanKeypoints]
    LEFT_HAND_THUMB_4: _ClassVar[HumanKeypoints]
    LEFT_HAND_INDEX_1: _ClassVar[HumanKeypoints]
    LEFT_HAND_INDEX_2: _ClassVar[HumanKeypoints]
    LEFT_HAND_INDEX_3: _ClassVar[HumanKeypoints]
    LEFT_HAND_INDEX_4: _ClassVar[HumanKeypoints]
    LEFT_HAND_MIDDLE_1: _ClassVar[HumanKeypoints]
    LEFT_HAND_MIDDLE_2: _ClassVar[HumanKeypoints]
    LEFT_HAND_MIDDLE_3: _ClassVar[HumanKeypoints]
    LEFT_HAND_MIDDLE_4: _ClassVar[HumanKeypoints]
    LEFT_HAND_RING_1: _ClassVar[HumanKeypoints]
    LEFT_HAND_RING_2: _ClassVar[HumanKeypoints]
    LEFT_HAND_RING_3: _ClassVar[HumanKeypoints]
    LEFT_HAND_RING_4: _ClassVar[HumanKeypoints]
    LEFT_HAND_PINKY_1: _ClassVar[HumanKeypoints]
    LEFT_HAND_PINKY_2: _ClassVar[HumanKeypoints]
    LEFT_HAND_PINKY_3: _ClassVar[HumanKeypoints]
    LEFT_HAND_PINKY_4: _ClassVar[HumanKeypoints]
    RIGHT_HAND_ROOT: _ClassVar[HumanKeypoints]
    RIGHT_HAND_THUMB_1: _ClassVar[HumanKeypoints]
    RIGHT_HAND_THUMB_2: _ClassVar[HumanKeypoints]
    RIGHT_HAND_THUMB_3: _ClassVar[HumanKeypoints]
    RIGHT_HAND_THUMB_4: _ClassVar[HumanKeypoints]
    RIGHT_HAND_INDEX_1: _ClassVar[HumanKeypoints]
    RIGHT_HAND_INDEX_2: _ClassVar[HumanKeypoints]
    RIGHT_HAND_INDEX_3: _ClassVar[HumanKeypoints]
    RIGHT_HAND_INDEX_4: _ClassVar[HumanKeypoints]
    RIGHT_HAND_MIDDLE_1: _ClassVar[HumanKeypoints]
    RIGHT_HAND_MIDDLE_2: _ClassVar[HumanKeypoints]
    RIGHT_HAND_MIDDLE_3: _ClassVar[HumanKeypoints]
    RIGHT_HAND_MIDDLE_4: _ClassVar[HumanKeypoints]
    RIGHT_HAND_RING_1: _ClassVar[HumanKeypoints]
    RIGHT_HAND_RING_2: _ClassVar[HumanKeypoints]
    RIGHT_HAND_RING_3: _ClassVar[HumanKeypoints]
    RIGHT_HAND_RING_4: _ClassVar[HumanKeypoints]
    RIGHT_HAND_PINKY_1: _ClassVar[HumanKeypoints]
    RIGHT_HAND_PINKY_2: _ClassVar[HumanKeypoints]
    RIGHT_HAND_PINKY_3: _ClassVar[HumanKeypoints]
    RIGHT_HAND_PINKY_4: _ClassVar[HumanKeypoints]

class ObjectLabels(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    UNKNOWN_OBJECT: _ClassVar[ObjectLabels]
    HUMAN_SKELETON: _ClassVar[ObjectLabels]
PNG: ImageFormats
JPEG: ImageFormats
WebP: ImageFormats
RGB: ColorSpaces
GRAY: ColorSpaces
YCbCr: ColorSpaces
HSV: ColorSpaces
UNKNOWN_HUMAN_KEYPOINT: HumanKeypoints
HEAD: HumanKeypoints
NOSE: HumanKeypoints
NECK: HumanKeypoints
RIGHT_SHOULDER: HumanKeypoints
RIGHT_ELBOW: HumanKeypoints
RIGHT_WRIST: HumanKeypoints
LEFT_SHOULDER: HumanKeypoints
LEFT_ELBOW: HumanKeypoints
LEFT_WRIST: HumanKeypoints
RIGHT_HIP: HumanKeypoints
RIGHT_KNEE: HumanKeypoints
RIGHT_ANKLE: HumanKeypoints
LEFT_HIP: HumanKeypoints
LEFT_KNEE: HumanKeypoints
LEFT_ANKLE: HumanKeypoints
RIGHT_EYE: HumanKeypoints
LEFT_EYE: HumanKeypoints
RIGHT_EAR: HumanKeypoints
LEFT_EAR: HumanKeypoints
CHEST: HumanKeypoints
PELVIS: HumanKeypoints
LEFT_BIG_TOE: HumanKeypoints
LEFT_SMALL_TOE: HumanKeypoints
LEFT_HEEL: HumanKeypoints
RIGHT_BIG_TOE: HumanKeypoints
RIGHT_SMALL_TOE: HumanKeypoints
RIGHT_HEEL: HumanKeypoints
FACE_0: HumanKeypoints
FACE_1: HumanKeypoints
FACE_2: HumanKeypoints
FACE_3: HumanKeypoints
FACE_4: HumanKeypoints
FACE_5: HumanKeypoints
FACE_6: HumanKeypoints
FACE_7: HumanKeypoints
FACE_8: HumanKeypoints
FACE_9: HumanKeypoints
FACE_10: HumanKeypoints
FACE_11: HumanKeypoints
FACE_12: HumanKeypoints
FACE_13: HumanKeypoints
FACE_14: HumanKeypoints
FACE_15: HumanKeypoints
FACE_16: HumanKeypoints
FACE_17: HumanKeypoints
FACE_18: HumanKeypoints
FACE_19: HumanKeypoints
FACE_20: HumanKeypoints
FACE_21: HumanKeypoints
FACE_22: HumanKeypoints
FACE_23: HumanKeypoints
FACE_24: HumanKeypoints
FACE_25: HumanKeypoints
FACE_26: HumanKeypoints
FACE_27: HumanKeypoints
FACE_28: HumanKeypoints
FACE_29: HumanKeypoints
FACE_30: HumanKeypoints
FACE_31: HumanKeypoints
FACE_32: HumanKeypoints
FACE_33: HumanKeypoints
FACE_34: HumanKeypoints
FACE_35: HumanKeypoints
FACE_36: HumanKeypoints
FACE_37: HumanKeypoints
FACE_38: HumanKeypoints
FACE_39: HumanKeypoints
FACE_40: HumanKeypoints
FACE_41: HumanKeypoints
FACE_42: HumanKeypoints
FACE_43: HumanKeypoints
FACE_44: HumanKeypoints
FACE_45: HumanKeypoints
FACE_46: HumanKeypoints
FACE_47: HumanKeypoints
FACE_48: HumanKeypoints
FACE_49: HumanKeypoints
FACE_50: HumanKeypoints
FACE_51: HumanKeypoints
FACE_52: HumanKeypoints
FACE_53: HumanKeypoints
FACE_54: HumanKeypoints
FACE_55: HumanKeypoints
FACE_56: HumanKeypoints
FACE_57: HumanKeypoints
FACE_58: HumanKeypoints
FACE_59: HumanKeypoints
FACE_60: HumanKeypoints
FACE_61: HumanKeypoints
FACE_62: HumanKeypoints
FACE_63: HumanKeypoints
FACE_64: HumanKeypoints
FACE_65: HumanKeypoints
FACE_66: HumanKeypoints
FACE_67: HumanKeypoints
LEFT_HAND_ROOT: HumanKeypoints
LEFT_HAND_THUMB_1: HumanKeypoints
LEFT_HAND_THUMB_2: HumanKeypoints
LEFT_HAND_THUMB_3: HumanKeypoints
LEFT_HAND_THUMB_4: HumanKeypoints
LEFT_HAND_INDEX_1: HumanKeypoints
LEFT_HAND_INDEX_2: HumanKeypoints
LEFT_HAND_INDEX_3: HumanKeypoints
LEFT_HAND_INDEX_4: HumanKeypoints
LEFT_HAND_MIDDLE_1: HumanKeypoints
LEFT_HAND_MIDDLE_2: HumanKeypoints
LEFT_HAND_MIDDLE_3: HumanKeypoints
LEFT_HAND_MIDDLE_4: HumanKeypoints
LEFT_HAND_RING_1: HumanKeypoints
LEFT_HAND_RING_2: HumanKeypoints
LEFT_HAND_RING_3: HumanKeypoints
LEFT_HAND_RING_4: HumanKeypoints
LEFT_HAND_PINKY_1: HumanKeypoints
LEFT_HAND_PINKY_2: HumanKeypoints
LEFT_HAND_PINKY_3: HumanKeypoints
LEFT_HAND_PINKY_4: HumanKeypoints
RIGHT_HAND_ROOT: HumanKeypoints
RIGHT_HAND_THUMB_1: HumanKeypoints
RIGHT_HAND_THUMB_2: HumanKeypoints
RIGHT_HAND_THUMB_3: HumanKeypoints
RIGHT_HAND_THUMB_4: HumanKeypoints
RIGHT_HAND_INDEX_1: HumanKeypoints
RIGHT_HAND_INDEX_2: HumanKeypoints
RIGHT_HAND_INDEX_3: HumanKeypoints
RIGHT_HAND_INDEX_4: HumanKeypoints
RIGHT_HAND_MIDDLE_1: HumanKeypoints
RIGHT_HAND_MIDDLE_2: HumanKeypoints
RIGHT_HAND_MIDDLE_3: HumanKeypoints
RIGHT_HAND_MIDDLE_4: HumanKeypoints
RIGHT_HAND_RING_1: HumanKeypoints
RIGHT_HAND_RING_2: HumanKeypoints
RIGHT_HAND_RING_3: HumanKeypoints
RIGHT_HAND_RING_4: HumanKeypoints
RIGHT_HAND_PINKY_1: HumanKeypoints
RIGHT_HAND_PINKY_2: HumanKeypoints
RIGHT_HAND_PINKY_3: HumanKeypoints
RIGHT_HAND_PINKY_4: HumanKeypoints
UNKNOWN_OBJECT: ObjectLabels
HUMAN_SKELETON: ObjectLabels

class Image(_message.Message):
    __slots__ = ("data", "uri")
    DATA_FIELD_NUMBER: _ClassVar[int]
    URI_FIELD_NUMBER: _ClassVar[int]
    data: bytes
    uri: str
    def __init__(self, data: _Optional[bytes] = ..., uri: _Optional[str] = ...) -> None: ...

class ImageFormat(_message.Message):
    __slots__ = ("format", "compression")
    FORMAT_FIELD_NUMBER: _ClassVar[int]
    COMPRESSION_FIELD_NUMBER: _ClassVar[int]
    format: ImageFormats
    compression: _wrappers_pb2.FloatValue
    def __init__(self, format: _Optional[_Union[ImageFormats, str]] = ..., compression: _Optional[_Union[_wrappers_pb2.FloatValue, _Mapping]] = ...) -> None: ...

class Vertex(_message.Message):
    __slots__ = ("x", "y", "z")
    X_FIELD_NUMBER: _ClassVar[int]
    Y_FIELD_NUMBER: _ClassVar[int]
    Z_FIELD_NUMBER: _ClassVar[int]
    x: float
    y: float
    z: float
    def __init__(self, x: _Optional[float] = ..., y: _Optional[float] = ..., z: _Optional[float] = ...) -> None: ...

class BoundingPoly(_message.Message):
    __slots__ = ("vertices",)
    VERTICES_FIELD_NUMBER: _ClassVar[int]
    vertices: _containers.RepeatedCompositeFieldContainer[Vertex]
    def __init__(self, vertices: _Optional[_Iterable[_Union[Vertex, _Mapping]]] = ...) -> None: ...

class Resolution(_message.Message):
    __slots__ = ("height", "width")
    HEIGHT_FIELD_NUMBER: _ClassVar[int]
    WIDTH_FIELD_NUMBER: _ClassVar[int]
    height: int
    width: int
    def __init__(self, height: _Optional[int] = ..., width: _Optional[int] = ...) -> None: ...

class ColorSpace(_message.Message):
    __slots__ = ("value",)
    VALUE_FIELD_NUMBER: _ClassVar[int]
    value: ColorSpaces
    def __init__(self, value: _Optional[_Union[ColorSpaces, str]] = ...) -> None: ...

class ImageSettings(_message.Message):
    __slots__ = ("resolution", "format", "color_space", "region")
    RESOLUTION_FIELD_NUMBER: _ClassVar[int]
    FORMAT_FIELD_NUMBER: _ClassVar[int]
    COLOR_SPACE_FIELD_NUMBER: _ClassVar[int]
    REGION_FIELD_NUMBER: _ClassVar[int]
    resolution: Resolution
    format: ImageFormat
    color_space: ColorSpace
    region: BoundingPoly
    def __init__(self, resolution: _Optional[_Union[Resolution, _Mapping]] = ..., format: _Optional[_Union[ImageFormat, _Mapping]] = ..., color_space: _Optional[_Union[ColorSpace, _Mapping]] = ..., region: _Optional[_Union[BoundingPoly, _Mapping]] = ...) -> None: ...

class PointAnnotation(_message.Message):
    __slots__ = ("id", "score", "position")
    ID_FIELD_NUMBER: _ClassVar[int]
    SCORE_FIELD_NUMBER: _ClassVar[int]
    POSITION_FIELD_NUMBER: _ClassVar[int]
    id: int
    score: float
    position: Vertex
    def __init__(self, id: _Optional[int] = ..., score: _Optional[float] = ..., position: _Optional[_Union[Vertex, _Mapping]] = ...) -> None: ...

class ObjectAnnotation(_message.Message):
    __slots__ = ("label", "id", "score", "region", "keypoints")
    LABEL_FIELD_NUMBER: _ClassVar[int]
    ID_FIELD_NUMBER: _ClassVar[int]
    SCORE_FIELD_NUMBER: _ClassVar[int]
    REGION_FIELD_NUMBER: _ClassVar[int]
    KEYPOINTS_FIELD_NUMBER: _ClassVar[int]
    label: str
    id: int
    score: float
    region: BoundingPoly
    keypoints: _containers.RepeatedCompositeFieldContainer[PointAnnotation]
    def __init__(self, label: _Optional[str] = ..., id: _Optional[int] = ..., score: _Optional[float] = ..., region: _Optional[_Union[BoundingPoly, _Mapping]] = ..., keypoints: _Optional[_Iterable[_Union[PointAnnotation, _Mapping]]] = ...) -> None: ...

class ObjectAnnotations(_message.Message):
    __slots__ = ("objects", "resolution", "frame_id")
    OBJECTS_FIELD_NUMBER: _ClassVar[int]
    RESOLUTION_FIELD_NUMBER: _ClassVar[int]
    FRAME_ID_FIELD_NUMBER: _ClassVar[int]
    objects: _containers.RepeatedCompositeFieldContainer[ObjectAnnotation]
    resolution: Resolution
    frame_id: int
    def __init__(self, objects: _Optional[_Iterable[_Union[ObjectAnnotation, _Mapping]]] = ..., resolution: _Optional[_Union[Resolution, _Mapping]] = ..., frame_id: _Optional[int] = ...) -> None: ...
