"""
File: src/safeshell/daemon/protocol.py
Purpose: JSON lines protocol for daemon IPC
Exports: encode_message, decode_message, read_message, write_message
Depends: json, asyncio, safeshell.models, safeshell.exceptions
Overview: Handles serialization and deserialization of messages between wrapper and daemon
"""

import asyncio
import json
from typing import Any

from pydantic import BaseModel

from safeshell.exceptions import ProtocolError


def encode_message(msg: BaseModel) -> bytes:
    """Encode a Pydantic model to JSON lines format (newline-delimited).

    Args:
        msg: Pydantic model to encode

    Returns:
        UTF-8 encoded JSON with trailing newline
    """
    return msg.model_dump_json().encode("utf-8") + b"\n"


def decode_message(data: bytes) -> dict[str, Any]:
    """Decode JSON bytes to a dictionary.

    Args:
        data: UTF-8 encoded JSON bytes

    Returns:
        Parsed dictionary

    Raises:
        ProtocolError: If JSON parsing fails
    """
    try:
        return json.loads(data.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise ProtocolError(f"Failed to decode message: {e}") from e


async def read_message(reader: asyncio.StreamReader) -> dict[str, Any]:
    """Read a JSON lines message from an async stream.

    Reads until newline, then decodes JSON.

    Args:
        reader: asyncio StreamReader

    Returns:
        Parsed message dictionary

    Raises:
        ProtocolError: If reading or parsing fails
    """
    try:
        line = await reader.readline()
        if not line:
            raise ProtocolError("Connection closed")
        return decode_message(line.strip())
    except asyncio.IncompleteReadError as e:
        raise ProtocolError(f"Incomplete read: {e}") from e


async def write_message(writer: asyncio.StreamWriter, msg: BaseModel) -> None:
    """Write a Pydantic model as JSON lines to an async stream.

    Args:
        writer: asyncio StreamWriter
        msg: Pydantic model to write
    """
    writer.write(encode_message(msg))
    await writer.drain()


def sync_encode_message(msg: BaseModel) -> bytes:
    """Synchronous version of encode_message for wrapper client."""
    return encode_message(msg)


def sync_decode_message(data: bytes) -> dict[str, Any]:
    """Synchronous version of decode_message for wrapper client."""
    return decode_message(data)
