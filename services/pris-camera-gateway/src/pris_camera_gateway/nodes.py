"""Typed access to the camera's GenICam nodes; SDK errors become a StatusException."""

from __future__ import annotations

from collections.abc import Callable
from typing import ParamSpec, TypeVar

from pris_wire.core import Status, StatusCode
from PySpin import (
    CBooleanPtr,
    CCommandPtr,
    CEnumerationPtr,
    CFloatPtr,
    CIntegerPtr,
    CStringPtr,
    INodeMap,
    SpinnakerException,
)

R = TypeVar("R")
P = ParamSpec("P")


class StatusException(Exception):
    """An error that becomes the Status of a request's reply."""

    def __init__(self, code: StatusCode, message: str) -> None:
        self.status = Status(code=code, why=message)
        super().__init__(message)


def _get_status(func: Callable[P, R]) -> Callable[P, R]:

    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        try:
            return func(*args, **kwargs)
        except SpinnakerException as ex:
            msg = f"Failed to get property '{args[1]}'"
            raise StatusException(StatusCode.INTERNAL_ERROR, msg) from ex

    return wrapper


def _set_status(func: Callable[P, R]) -> Callable[P, R]:

    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        try:
            return func(*args, **kwargs)
        except SpinnakerException as ex:
            msg = f"Failed to set property '{args[1]}' to '{args[2]}'"
            raise StatusException(StatusCode.INTERNAL_ERROR, msg) from ex

    return wrapper


def _check_range(name: str, value: float, min_value: float, max_value: float) -> None:
    if value < min_value or value > max_value:
        msg = f"Property '{name}' must be in interval [{min_value}, {max_value}]"
        raise StatusException(StatusCode.INVALID_ARGUMENT, msg)


@_get_status
def get_bool(node_map: INodeMap, name: str) -> bool:
    return CBooleanPtr(node_map.GetNode(name)).GetValue()


@_set_status
def set_bool(node_map: INodeMap, name: str, value: bool) -> None:
    CBooleanPtr(node_map.GetNode(name)).SetValue(value)


@_get_status
def get_int(node_map: INodeMap, name: str) -> int:
    return CIntegerPtr(node_map.GetNode(name)).GetValue()


@_set_status
def set_int(node_map: INodeMap, name: str, value: int) -> None:
    node = CIntegerPtr(node_map.GetNode(name))
    _check_range(name, value, node.GetMin(), node.GetMax())
    node.SetValue(value)


@_get_status
def get_float(node_map: INodeMap, name: str) -> float:
    return CFloatPtr(node_map.GetNode(name)).GetValue()


@_set_status
def set_float(node_map: INodeMap, name: str, value: float) -> None:
    node = CFloatPtr(node_map.GetNode(name))
    _check_range(name, value, node.GetMin(), node.GetMax())
    node.SetValue(value)


@_get_status
def get_str(node_map: INodeMap, name: str) -> str:
    return CStringPtr(node_map.GetNode(name)).GetValue()


@_get_status
def get_enum(node_map: INodeMap, name: str) -> str:
    return CEnumerationPtr(node_map.GetNode(name)).GetCurrentEntry().GetSymbolic()


@_set_status
def set_enum(node_map: INodeMap, name: str, value: str) -> None:
    node = CEnumerationPtr(node_map.GetNode(name))
    node.SetIntValue(node.GetEntryByName(value).GetValue())


@_get_status
def range_float(node_map: INodeMap, name: str) -> tuple[float, float]:
    node = CFloatPtr(node_map.GetNode(name))
    return node.GetMin(), node.GetMax()


@_get_status
def range_int(node_map: INodeMap, name: str) -> tuple[int, int]:
    node = CIntegerPtr(node_map.GetNode(name))
    return node.GetMin(), node.GetMax()


def execute(node_map: INodeMap, name: str) -> None:
    try:
        CCommandPtr(node_map.GetNode(name)).Execute()
    except SpinnakerException as ex:
        raise StatusException(
            StatusCode.INTERNAL_ERROR,
            f"Failed to execute command '{name}'",
        ) from ex
