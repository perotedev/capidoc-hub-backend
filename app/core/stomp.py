"""Minimal STOMP 1.2 frame codec.

Implements only the subset of the spec this app's real-time channel needs —
CONNECT/CONNECTED/SUBSCRIBE/UNSUBSCRIBE/SEND/MESSAGE/ERROR/DISCONNECT — over a
plain WebSocket transport. Not a full spec implementation: no transactions,
no ACK/NACK, no heart-beat negotiation (the client is our own Android app, so
both ends are controlled and can stay deliberately simple).
"""

from dataclasses import dataclass, field

_NULL = "\x00"


@dataclass
class StompFrame:
    command: str
    headers: dict[str, str] = field(default_factory=dict)
    body: str = ""


def encode_frame(frame: StompFrame) -> str:
    lines = [frame.command]
    lines.extend(f"{key}:{value}" for key, value in frame.headers.items())
    return "\n".join(lines) + "\n\n" + frame.body + _NULL


def decode_frame(raw: str) -> StompFrame:
    """Raises `ValueError` on a malformed/empty frame (e.g. a bare heart-beat
    newline) — callers should treat that as "ignore this message"."""
    trimmed = raw.strip("\n").rstrip(_NULL)
    if not trimmed:
        raise ValueError("Empty STOMP frame")

    header_part, _, body = trimmed.partition("\n\n")
    lines = header_part.split("\n")
    command = lines[0].strip()
    if not command:
        raise ValueError("STOMP frame missing command")

    headers: dict[str, str] = {}
    for line in lines[1:]:
        if not line:
            continue
        key, _, value = line.partition(":")
        headers[key] = value

    return StompFrame(command=command, headers=headers, body=body)
