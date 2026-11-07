from google.protobuf import any_pb2 as _any_pb2
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class StatusCode(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    UNKNOWN: _ClassVar[StatusCode]
    OK: _ClassVar[StatusCode]
    CANCELLED: _ClassVar[StatusCode]
    INVALID_ARGUMENT: _ClassVar[StatusCode]
    DEADLINE_EXCEEDED: _ClassVar[StatusCode]
    NOT_FOUND: _ClassVar[StatusCode]
    ALREADY_EXISTS: _ClassVar[StatusCode]
    PERMISSION_DENIED: _ClassVar[StatusCode]
    UNAUTHENTICATED: _ClassVar[StatusCode]
    FAILED_PRECONDITION: _ClassVar[StatusCode]
    OUT_OF_RANGE: _ClassVar[StatusCode]
    UNIMPLEMENTED: _ClassVar[StatusCode]
    INTERNAL_ERROR: _ClassVar[StatusCode]

class ContentType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    NONE: _ClassVar[ContentType]
    PROTOBUF: _ClassVar[ContentType]
    JSON: _ClassVar[ContentType]
    PROTOTEXT: _ClassVar[ContentType]
UNKNOWN: StatusCode
OK: StatusCode
CANCELLED: StatusCode
INVALID_ARGUMENT: StatusCode
DEADLINE_EXCEEDED: StatusCode
NOT_FOUND: StatusCode
ALREADY_EXISTS: StatusCode
PERMISSION_DENIED: StatusCode
UNAUTHENTICATED: StatusCode
FAILED_PRECONDITION: StatusCode
OUT_OF_RANGE: StatusCode
UNIMPLEMENTED: StatusCode
INTERNAL_ERROR: StatusCode
NONE: ContentType
PROTOBUF: ContentType
JSON: ContentType
PROTOTEXT: ContentType

class Status(_message.Message):
    __slots__ = ("code", "why")
    CODE_FIELD_NUMBER: _ClassVar[int]
    WHY_FIELD_NUMBER: _ClassVar[int]
    code: StatusCode
    why: str
    def __init__(self, code: _Optional[_Union[StatusCode, str]] = ..., why: _Optional[str] = ...) -> None: ...

class WireFormat(_message.Message):
    __slots__ = ("raw", "message", "created_at", "content_type", "status", "correlation_id", "reply_to", "expires_in")
    RAW_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    CONTENT_TYPE_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    CORRELATION_ID_FIELD_NUMBER: _ClassVar[int]
    REPLY_TO_FIELD_NUMBER: _ClassVar[int]
    EXPIRES_IN_FIELD_NUMBER: _ClassVar[int]
    raw: bytes
    message: _any_pb2.Any
    created_at: int
    content_type: ContentType
    status: Status
    correlation_id: int
    reply_to: str
    expires_in: int
    def __init__(self, raw: _Optional[bytes] = ..., message: _Optional[_Union[_any_pb2.Any, _Mapping]] = ..., created_at: _Optional[int] = ..., content_type: _Optional[_Union[ContentType, str]] = ..., status: _Optional[_Union[Status, _Mapping]] = ..., correlation_id: _Optional[int] = ..., reply_to: _Optional[str] = ..., expires_in: _Optional[int] = ...) -> None: ...
