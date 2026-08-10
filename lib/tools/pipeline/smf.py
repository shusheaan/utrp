"""Minimal Standard MIDI File writer (pure functions, stdlib only).

Event = (tick, on, channel, note, vel). Shared by drummidi (drum patterns)
and tools/harmony (progression export).
"""
from __future__ import annotations

import struct

Event = tuple[int, bool, int, int, int]


def _vlq(n: int) -> bytes:
    if n < 0:
        raise ValueError(f"negative delta: {n}")
    out = [n & 0x7F]
    n >>= 7
    while n:
        out.append(0x80 | (n & 0x7F))
        n >>= 7
    return bytes(reversed(out))


def _meta(tick_delta: int, kind: int, data: bytes) -> bytes:
    return _vlq(tick_delta) + bytes([0xFF, kind]) + _vlq(len(data)) + data


def track_bytes(events: list[Event], name: str = "",
                tempo_bpm: float | None = None) -> bytes:
    body = b""
    if name:
        body += _meta(0, 0x03, name.encode())
    if tempo_bpm is not None:
        us = int(round(60_000_000 / tempo_bpm))
        body += _meta(0, 0x51, struct.pack(">I", us)[1:])
        body += _meta(0, 0x58, bytes([4, 2, 24, 8]))          # 4/4
    last = 0
    for tick, on, ch, note, vel in sorted(events, key=lambda e: (e[0], e[1])):
        status = (0x90 if on else 0x80) | (ch & 0x0F)
        body += _vlq(tick - last) + bytes([status, note & 0x7F, vel & 0x7F])
        last = tick
    body += _meta(0, 0x2F, b"")                               # end of track
    return b"MTrk" + struct.pack(">I", len(body)) + body


def file_bytes(tracks: list[bytes], ppq: int = 480) -> bytes:
    fmt = 0 if len(tracks) == 1 else 1
    header = b"MThd" + struct.pack(">IHHH", 6, fmt, len(tracks), ppq)
    return header + b"".join(tracks)
