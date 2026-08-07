# SPDX-FileCopyrightText: 2026 Blender Authors
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Per-instance runtime descriptor registry.

The Blender extension writes a small JSON descriptor per running instance so
the external MCP server can discover this instance's dynamically assigned
bridge endpoint without fixed host/port configuration.

See ``docs/bridge-protocol.md`` and ``docs/instance-descriptor.schema.json``
for the normative contract.
"""

__all__ = (
    "INSTANCE_DIR_NAME",
    "MAX_DESCRIPTOR_BYTES",
    "PROTOCOL_VERSION",
    "SCHEMA_VERSION",
    "new_instance_id",
    "new_token",
    "remove_descriptor",
    "runtime_dir",
    "write_descriptor",
)

import json
import os
import secrets
import sys
import tempfile
import uuid

#: Version of the descriptor file format (bump on breaking descriptor changes).
SCHEMA_VERSION = 1
#: Version of the bridge wire protocol (NUL-delimited JSON over TCP).
PROTOCOL_VERSION = 1

#: Maximum descriptor size; larger files are rejected by the scanner.
MAX_DESCRIPTOR_BYTES = 64 * 1024

INSTANCE_DIR_NAME = "instances"


def runtime_dir() -> str:
    """
    Return the per-user runtime directory for instance descriptors.

    ``BLENDER_MCP_RUNTIME_DIR`` overrides the root for tests and advanced
    deployments. Otherwise the location is platform specific:

    - Windows: ``%LOCALAPPDATA%\\BlenderMCPConnect\\instances\\``
    - macOS: ``~/Library/Caches/BlenderMCPConnect/instances/``
    - Linux: ``$XDG_RUNTIME_DIR/blender-mcp-connect/instances/``,
      falling back to ``$XDG_CACHE_HOME`` then ``~/.cache``.
    """
    override = os.environ.get("BLENDER_MCP_RUNTIME_DIR")
    if override:
        return os.path.join(override, INSTANCE_DIR_NAME)

    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or os.path.join(
            os.path.expanduser("~"), "AppData", "Local")
        return os.path.join(base, "BlenderMCPConnect", INSTANCE_DIR_NAME)

    if sys.platform == "darwin":
        return os.path.join(
            os.path.expanduser("~/Library/Caches/BlenderMCPConnect"),
            INSTANCE_DIR_NAME)

    runtime = os.environ.get("XDG_RUNTIME_DIR")
    if runtime:
        return os.path.join(runtime, "blender-mcp-connect", INSTANCE_DIR_NAME)

    cache = os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache")
    return os.path.join(cache, "blender-mcp-connect", INSTANCE_DIR_NAME)


def new_instance_id() -> str:
    """Return a new UUIDv4 identifying one Blender process instance."""
    return str(uuid.uuid4())


def new_token() -> str:
    """Return a fresh random capability token (never logged or displayed)."""
    return secrets.token_hex(32)


def _descriptor_path(instance_id: str) -> str:
    return os.path.join(runtime_dir(), instance_id + ".json")


def write_descriptor(
        *,
        instance_id: str,
        pid: int,
        host: str,
        port: int,
        token: str,
        blender_version: str,
        extension_version: str,
        blender_executable: str,
        blend_file: str,
) -> str:
    """
    Atomically publish the instance descriptor and return its path.

    Raises ``OSError`` on failure. The caller must treat a descriptor-write
    failure as a startup failure and roll back (close the socket).
    """
    import datetime

    now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    data = {
        "schemaVersion": SCHEMA_VERSION,
        "protocolVersion": PROTOCOL_VERSION,
        "instanceId": instance_id,
        "pid": pid,
        "host": host,
        "port": port,
        "token": token,
        "blenderVersion": blender_version,
        "extensionVersion": extension_version,
        "blenderExecutable": blender_executable,
        "blendFile": blend_file,
        "startedAt": now,
        "updatedAt": now,
    }
    payload = json.dumps(data)
    if len(payload.encode("utf-8")) > MAX_DESCRIPTOR_BYTES:
        raise OSError("Descriptor exceeds {:d} byte limit".format(MAX_DESCRIPTOR_BYTES))

    directory = runtime_dir()
    os.makedirs(directory, mode=0o700, exist_ok=True)
    if os.name != "nt":
        # Best-effort: keep the runtime directory private.
        try:
            os.chmod(directory, 0o700)
        except OSError:
            pass

    path = _descriptor_path(instance_id)
    fd = -1
    tmp_path = ""
    try:
        fd, tmp_path = tempfile.mkstemp(prefix=".tmp-", suffix=".json", dir=directory)
        os.write(fd, payload.encode("utf-8"))
        os.close(fd)
        fd = -1
        if os.name != "nt":
            os.chmod(tmp_path, 0o600)
        os.replace(tmp_path, path)
    except Exception:
        if fd != -1:
            try:
                os.close(fd)
            except OSError:
                pass
        if tmp_path:
            try:
                os.remove(tmp_path)
            except OSError:
                pass
        raise
    return path


def remove_descriptor(instance_id: str) -> bool:
    """
    Remove the descriptor for *instance_id* if it is still owned by it.

    Only deletes the file when its ``instanceId`` matches, so a stale
    descriptor left by an earlier process is never removed by mistake.
    Returns ``True`` when a file was removed.
    """
    path = _descriptor_path(instance_id)
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return False
    if data.get("instanceId") != instance_id:
        return False
    try:
        os.remove(path)
    except OSError:
        return False
    return True
