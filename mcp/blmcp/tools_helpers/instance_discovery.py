# SPDX-FileCopyrightText: 2026 Blender Authors
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Automatic discovery of Blender MCP Connect instances.

The Blender extension publishes one JSON descriptor per running instance
(see ``docs/bridge-protocol.md``). This module scans the runtime directory,
validates descriptors defensively, probes candidates with an authenticated
``hello`` handshake, and applies the documented selection rules.
"""

__all__ = (
    "DiscoveredInstance",
    "PROTOCOL_VERSION",
    "discover_instances",
    "healthy_instances",
    "probe_instance",
    "runtime_dir",
    "select_instance",
)

import json
import os
import socket
import sys
from typing import NamedTuple

#: Bridge wire protocol version (must match the extension side).
PROTOCOL_VERSION = 1

#: Maximum descriptor size; larger files are rejected.
MAX_DESCRIPTOR_BYTES = 64 * 1024

#: Short timeout for `hello` probes (Blender may be busy, so be generous
#: enough to not misclassify a busy-but-healthy session as dead).
HELLO_TIMEOUT = 2.0

#: List of descriptor fields required for a candidate to be usable.
_REQUIRED_FIELDS = (
    "schemaVersion",
    "protocolVersion",
    "instanceId",
    "pid",
    "host",
    "port",
    "token",
)


class DiscoveredInstance(NamedTuple):
    """
    A validated instance descriptor from disk.

    ``host``/``port``/``token`` are hints from disk; identity is only
    considered confirmed after a successful authenticated ``hello`` probe.
    """

    instance_id: str
    host: str
    port: int
    token: str
    descriptor_path: str
    blender_version: str
    extension_version: str
    blender_executable: str
    blend_file: str


def runtime_dir() -> str:
    """
    Return the per-user runtime directory for instance descriptors.

    Mirrors the extension-side resolution in
    ``addon/blender_mcp_addon/instance_registry.py``:
    ``BLENDER_MCP_RUNTIME_DIR`` overrides the root, otherwise the platform
    default is used (Windows ``%LOCALAPPDATA%``, macOS ``~/Library/Caches``,
    Linux ``$XDG_RUNTIME_DIR``/``$XDG_CACHE_HOME``).
    """
    override = os.environ.get("BLENDER_MCP_RUNTIME_DIR")
    if override:
        return os.path.join(override, "instances")

    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or os.path.join(
            os.path.expanduser("~"), "AppData", "Local")
        return os.path.join(base, "BlenderMCPConnect", "instances")

    if sys.platform == "darwin":
        return os.path.join(
            os.path.expanduser("~/Library/Caches/BlenderMCPConnect"),
            "instances")

    runtime = os.environ.get("XDG_RUNTIME_DIR")
    if runtime:
        return os.path.join(runtime, "blender-mcp-connect", "instances")

    cache = os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache")
    return os.path.join(cache, "blender-mcp-connect", "instances")


def _validate_descriptor(path: str) -> dict[str, object] | None:
    """
    Validate a descriptor file defensively.

    Returns the parsed dict, or ``None`` when the file is malformed,
    oversized, not a regular file, a symlink, or missing required fields.
    """
    try:
        st = os.stat(path)
    except OSError:
        return None
    if not st.st_mode & 0o170000 == 0o100000:  # regular file only
        return None
    if os.path.islink(path):
        return None
    if st.st_size > MAX_DESCRIPTOR_BYTES:
        return None
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    for field in _REQUIRED_FIELDS:
        if field not in data:
            return None
    if not isinstance(data["instanceId"], str) or len(data["instanceId"]) != 36:
        return None
    if not isinstance(data["port"], int) or not (1 <= data["port"] <= 65535):
        return None
    if not isinstance(data["host"], str):
        return None
    if not isinstance(data["token"], str) or len(data["token"]) < 32:
        return None
    if data.get("schemaVersion") != 1:
        return None
    if data.get("protocolVersion") != PROTOCOL_VERSION:
        return None
    return data


def discover_instances() -> list[DiscoveredInstance]:
    """
    Scan the runtime directory and return all syntactically valid descriptors.

    This performs no network access; health is determined by ``probe_instance``.
    """
    directory = runtime_dir()
    try:
        entries = os.listdir(directory)
    except OSError:
        return []

    result: list[DiscoveredInstance] = []
    for name in entries:
        if not name.endswith(".json"):
            continue
        path = os.path.join(directory, name)
        data = _validate_descriptor(path)
        if data is None:
            continue
        result.append(DiscoveredInstance(
            instance_id=str(data["instanceId"]),
            host=str(data["host"]),
            port=int(data["port"]),
            token=str(data["token"]),
            descriptor_path=path,
            blender_version=str(data.get("blenderVersion", "")),
            extension_version=str(data.get("extensionVersion", "")),
            blender_executable=str(data.get("blenderExecutable", "")),
            blend_file=str(data.get("blendFile", "")),
        ))
    return result


def probe_instance(instance: DiscoveredInstance) -> dict[str, object] | None:
    """
    Authenticated ``hello`` probe.

    Returns the parsed response dict, or ``None`` when the endpoint is
    unreachable or the identity/token is rejected. The response's
    ``result.instanceId`` must match the descriptor's instance ID; callers
    must verify that themselves.
    """
    request = json.dumps({
        "type": "hello",
        "protocolVersion": PROTOCOL_VERSION,
        "instanceId": instance.instance_id,
        "token": instance.token,
    }) + "\0"
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(HELLO_TIMEOUT)
            sock.connect((instance.host, instance.port))
            sock.sendall(request.encode("utf-8"))
            buf = bytearray()
            while b"\0" not in buf:
                chunk = sock.recv(65536)
                if not chunk:
                    break
                buf.extend(chunk)
                if len(buf) > MAX_DESCRIPTOR_BYTES:
                    return None
    except OSError:
        return None
    line, _sep, _rest = buf.partition(b"\0")
    try:
        response = json.loads(line.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    if not isinstance(response, dict):
        return None
    return response


def healthy_instances() -> list[DiscoveredInstance]:
    """
    Return descriptors whose authenticated ``hello`` probe confirms the
    expected instance identity.
    """
    healthy: list[DiscoveredInstance] = []
    for instance in discover_instances():
        response = probe_instance(instance)
        if response is None or response.get("status") != "ok":
            continue
        result = response.get("result")
        if not isinstance(result, dict):
            continue
        if result.get("instanceId") != instance.instance_id:
            continue
        healthy.append(instance)
    return healthy


def select_instance(instance_id: str) -> DiscoveredInstance | None:
    """
    Return the healthy instance matching *instance_id*, or ``None``.

    Exact match only; never falls back to another instance.
    """
    for instance in discover_instances():
        if instance.instance_id != instance_id:
            continue
        response = probe_instance(instance)
        if response is None or response.get("status") != "ok":
            return None
        result = response.get("result")
        if isinstance(result, dict) and result.get("instanceId") == instance_id:
            return instance
        return None
    return None
