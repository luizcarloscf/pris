from __future__ import annotations

from enum import Enum

from ..utils import assert_type
from . import wire_pb2


class StatusCode(Enum):
    """The result of a request, as in pris.wire.StatusCode."""

    UNKNOWN = wire_pb2.StatusCode.Value('UNKNOWN')
    OK = wire_pb2.StatusCode.Value('OK')
    CANCELLED = wire_pb2.StatusCode.Value('CANCELLED')
    INVALID_ARGUMENT = wire_pb2.StatusCode.Value('INVALID_ARGUMENT')
    DEADLINE_EXCEEDED = wire_pb2.StatusCode.Value('DEADLINE_EXCEEDED')
    NOT_FOUND = wire_pb2.StatusCode.Value('NOT_FOUND')
    ALREADY_EXISTS = wire_pb2.StatusCode.Value('ALREADY_EXISTS')
    PERMISSION_DENIED = wire_pb2.StatusCode.Value('PERMISSION_DENIED')
    UNAUTHENTICATED = wire_pb2.StatusCode.Value('UNAUTHENTICATED')
    FAILED_PRECONDITION = wire_pb2.StatusCode.Value('FAILED_PRECONDITION')
    OUT_OF_RANGE = wire_pb2.StatusCode.Value('OUT_OF_RANGE')
    UNIMPLEMENTED = wire_pb2.StatusCode.Value('UNIMPLEMENTED')
    INTERNAL_ERROR = wire_pb2.StatusCode.Value('INTERNAL_ERROR')


class Status(object):
    """The result of a request: a code and a human-readable reason."""

    def __init__(self, code: StatusCode = StatusCode.UNKNOWN, why: str = "") -> None:
        """Create a status.

        Args:
            code: the result.
            why: why it failed, for people.

        Raises:
            TypeError: `code` isn't a StatusCode or `why` isn't a str.
        """
        self._code = code
        self._why = why
        self.code = code
        self.why = why

    def __eq__(self, other: object) -> bool:
        return self.__dict__ == other.__dict__

    def __str__(self) -> str:
        pretty = "{{ code={} why='{}' }}".format(self.code, self.why or "")
        return pretty

    @property
    def code(self) -> StatusCode:
        """The result; setting it raises TypeError if it isn't a StatusCode."""
        return self._code

    @code.setter
    def code(self, code: StatusCode) -> None:
        assert_type(code, StatusCode, "code")
        self._code = code

    def ok(self) -> bool:
        """Return True if the code is OK."""
        return self._code == StatusCode.OK

    @property
    def why(self) -> str:
        """Why it failed; setting it raises TypeError if it isn't a str."""
        return self._why

    @why.setter
    def why(self, reason: str) -> None:
        assert_type(reason, str, "why")
        self._why = reason
