"""Load and save protobuf messages as JSON files."""

from typing import Type, TypeVar

from google.protobuf.json_format import MessageToJson, Parse
from google.protobuf.message import Message

T = TypeVar("T", bound=Message)


def load(path: str, message_type: Type[T]) -> T:
    """Load a message from a JSON file.

    Args:
        path: the JSON file.
        message_type: the message class to parse it into.

    Returns:
        A new `message_type` with the file's fields; fields left out keep their zero value.

    Raises:
        OSError: the file can't be read.
        UnicodeDecodeError: the file isn't UTF-8.
        google.protobuf.json_format.ParseError: the file isn't JSON or has unknown fields.
    """
    with open(path, encoding="utf-8") as file:
        return Parse(file.read(), message_type())


def save(path: str, message: Message) -> None:
    """Save a message to a JSON file, indented.

    Args:
        path: the file to write, replaced if it exists.
        message: the message to save.

    Raises:
        OSError: the file can't be written.
    """
    with open(path, "w", encoding="utf-8") as file:
        file.write(MessageToJson(message, indent=2) + "\n")
