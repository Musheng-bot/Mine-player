"""TCP frame protocol shared by sender and receiver."""

from __future__ import annotations

import socket
import struct


HEADER = struct.Struct("!IQ")
MAX_FRAME_SIZE = 50 * 1024 * 1024


def pack_frame(frame: bytes, captured_at_ns: int) -> bytes:
    return HEADER.pack(len(frame), captured_at_ns) + frame


def send_frame(connection: socket.socket, frame: bytes, captured_at_ns: int) -> None:
    connection.sendall(pack_frame(frame, captured_at_ns))


def receive_exact(connection: socket.socket, size: int) -> bytes | None:
    chunks = bytearray()
    while len(chunks) < size:
        chunk = connection.recv(size - len(chunks))
        if not chunk:
            return None
        chunks.extend(chunk)
    return bytes(chunks)


def receive_frame(connection: socket.socket) -> tuple[bytes, int] | None:
    header = receive_exact(connection, HEADER.size)
    if header is None:
        return None
    frame_size, captured_at_ns = HEADER.unpack(header)
    if frame_size == 0 or frame_size > MAX_FRAME_SIZE:
        raise RuntimeError(f"无效帧大小：{frame_size}")
    payload = receive_exact(connection, frame_size)
    if payload is None:
        return None
    return payload, captured_at_ns
