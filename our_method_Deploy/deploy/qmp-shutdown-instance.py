#!/usr/bin/env python3
"""Request a bounded ACPI shutdown from one QEMU instance over QMP."""

from __future__ import annotations

import json
import socket
import sys
import time
from pathlib import Path


def receive(stream: socket.socket) -> dict:
    data = b""
    while b"\n" not in data:
        chunk = stream.recv(65536)
        if not chunk:
            raise RuntimeError("QMP socket closed before a complete response")
        data += chunk
    return json.loads(data.splitlines()[0])


def send(stream: socket.socket, command: str) -> None:
    stream.sendall(json.dumps({"execute": command}).encode() + b"\r\n")


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: qmp-shutdown-instance.py QMP_SOCKET", file=sys.stderr)
        return 64
    path = Path(sys.argv[1])
    if not path.exists():
        return 0
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as stream:
        stream.settimeout(5)
        stream.connect(str(path))
        receive(stream)
        send(stream, "qmp_capabilities")
        receive(stream)
        send(stream, "system_powerdown")
    deadline = time.monotonic() + 90
    while path.exists() and time.monotonic() < deadline:
        time.sleep(1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
