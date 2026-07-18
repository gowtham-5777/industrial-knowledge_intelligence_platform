"""Shared byte helpers for storage backends."""

from __future__ import annotations

from typing import BinaryIO


def read_bytes(data: BinaryIO | bytes) -> bytes:
    if isinstance(data, (bytes, bytearray)):
        return bytes(data)
    return data.read()
