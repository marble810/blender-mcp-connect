# SPDX-FileCopyrightText: 2026 Blender Authors
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Socket client for communicating with the Blender add-on.

Used by MCP "tools" that send-code to the Blender add-on.

Endpoint resolution precedence (see ``docs/bridge-protocol.md``):

1. ``BLENDER_MCP_INSTANCE`` (explicit instance selection).
2. Explicit ``BLENDER_MCP_HOST`` / ``BLENDER_MCP_PORT`` (legacy mode).
3. Automatic descriptor discovery.

No-replay semantics: requests may only be retried when the failure happened
before transmission began. Once ``sendall()`` starts, the execution outcome
may be unknown and the request is never blindly replayed.
"""

__all__ = (
    "get_connection_params",
    "resolve_endpoint",
    "send_code",
)

import json
import os
import socket

from . import instance_discovery

_DEFAULT_HOST = "127.0.0.1"
_DEFAULT_PORT = 9876
_TIMEOUT = 300.0
_RECV_BUFFER_SIZE = 65536

# Session affinity: the selected healthy instance, pinned for the lifetime
# of this MCP server process.
_selected_instance: instance_discovery.DiscoveredInstance | None = None

# Distinguish post-send failures from pre-send failures so callers can
# present an accurate "outcome unknown" diagnostic.
_OUTCOME_UNKNOWN_MESSAGE = (
    "Execution outcome is unknown. The request was not retried."
)


def get_connection_params() -> tuple[str, int]:
    """
    Return the bridge endpoint, resolving configuration and discovery.

    Backwards-compatible: returns ``(host, port)``. Raises
    ``ConnectionError`` when no usable Blender instance can be found.
    """
    resolved = resolve_endpoint()
    return resolved["host"], resolved["port"]


def resolve_endpoint() -> dict[str, object]:
    """
    Resolve the bridge endpoint according to the documented precedence.

    Returns a dict with keys ``host``, ``port`` and ``instance`` (the pinned
    ``DiscoveredInstance`` or ``None`` for legacy mode).
    """
    global _selected_instance

    # 1. Explicit instance selection (env; `--blender-instance` sets this).
    explicit_id = os.environ.get("BLENDER_MCP_INSTANCE")
    if explicit_id:
        instance = instance_discovery.select_instance(explicit_id)
        if instance is None:
            raise ConnectionError(
                "No healthy Blender instance with ID {!r} was found. "
                "Start/enable the MCP Connect extension in Blender first.".format(explicit_id)
            )
        _selected_instance = instance
        return {
            "host": instance.host,
            "port": instance.port,
            "instance": instance,
        }

    # 2. Explicit legacy host/port.
    legacy = _legacy_params()
    if legacy is not None:
        host, port = legacy
        # If the legacy endpoint matches a healthy descriptor, upgrade to
        # the authenticated protocol; otherwise stay in legacy mode.
        for instance in instance_discovery.discover_instances():
            if instance.host == host and instance.port == port:
                response = instance_discovery.probe_instance(instance)
                result = response.get("result") if isinstance(response, dict) else None
                if (
                    response is not None
                    and response.get("status") == "ok"
                    and isinstance(result, dict)
                    and result.get("instanceId") == instance.instance_id
                ):
                    _selected_instance = instance
                    return {
                        "host": instance.host,
                        "port": instance.port,
                        "instance": instance,
                    }
                break
        _selected_instance = None
        return {"host": host, "port": port, "instance": None}

    # 3. Automatic discovery with session affinity.
    if _selected_instance is not None:
        response = instance_discovery.probe_instance(_selected_instance)
        result = response.get("result") if isinstance(response, dict) else None
        if (
            response is not None
            and response.get("status") == "ok"
            and isinstance(result, dict)
            and result.get("instanceId") == _selected_instance.instance_id
        ):
            return {
                "host": _selected_instance.host,
                "port": _selected_instance.port,
                "instance": _selected_instance,
            }
        # The pinned instance is gone. Never silently switch to another.
        raise ConnectionError(
            "The selected Blender instance ({:s}) is no longer reachable. "
            "Restart the MCP server or set BLENDER_MCP_INSTANCE to "
            "re-select an instance.".format(_selected_instance.instance_id)
        )

    healthy = instance_discovery.healthy_instances()
    if not healthy:
        raise ConnectionError(
            "No Blender MCP Connect instance was found. "
            "Install and enable the MCP Connect extension in Blender and "
            "start its local bridge server."
        )
    if len(healthy) == 1:
        _selected_instance = healthy[0]
        return {
            "host": healthy[0].host,
            "port": healthy[0].port,
            "instance": healthy[0],
        }

    # Multiple healthy instances: fail closed, never guess.
    lines = [
        "Multiple healthy Blender instances were found; refusing to guess. "
        "Set BLENDER_MCP_INSTANCE to one of:",
    ]
    for instance in healthy:
        lines.append(
            "  {:s}  Blender {:s}  {:s}  PID {:d}".format(
                instance.instance_id,
                instance.blender_version or "?",
                os.path.basename(instance.blend_file) if instance.blend_file else "(no file)",
                _descriptor_pid(instance),
            )
        )
    raise ConnectionError("\n".join(lines))


def _descriptor_pid(instance: instance_discovery.DiscoveredInstance) -> int:
    """Read the PID hint from the descriptor (hint only, never authoritative)."""
    try:
        with open(instance.descriptor_path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return 0
    pid = data.get("pid")
    return pid if isinstance(pid, int) else 0


def _legacy_params() -> tuple[str, int] | None:
    host = os.environ.get("BLENDER_MCP_HOST")
    port = os.environ.get("BLENDER_MCP_PORT")
    if host is None and port is None:
        return None
    return host or _DEFAULT_HOST, int(port or str(_DEFAULT_PORT))


def _send_request(host: str, port: int, request: dict[str, object]) -> dict[str, object]:
    """
    Send one request and await the NUL-delimited JSON response.

    Raises ``ConnectionError`` for all failures. Failures after
    ``sendall`` began are marked with ``_OUTCOME_UNKNOWN_MESSAGE``.
    """
    payload = (json.dumps(request) + "\0").encode("utf-8")
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(_TIMEOUT)
            sock.connect((host, port))

            try:
                sock.sendall(payload)
            except OSError as ex:
                # Transmission may have partially reached Blender.
                raise ConnectionError(
                    "{:s} (send failed: {:s})".format(_OUTCOME_UNKNOWN_MESSAGE, str(ex))
                ) from ex

            buf = bytearray()
            while True:
                chunk = sock.recv(_RECV_BUFFER_SIZE)
                if not chunk:
                    break
                buf.extend(chunk)
                if b"\0" in buf:
                    break
    except ConnectionError:
        raise
    except ConnectionRefusedError as ex:
        raise ConnectionError(
            "Cannot connect to Blender at {:s}:{:d}. "
            "Ensure Blender is running with the MCP addon enabled and the server started.".format(host, port)
        ) from ex
    except socket.timeout as ex:
        raise ConnectionError(
            "{:s} (Blender connection timed out at {:s}:{:d})".format(_OUTCOME_UNKNOWN_MESSAGE, host, port)
        ) from ex
    except OSError as ex:
        # NOTE: intentionally not catching `Exception` here.
        # Callers use `ConnectionError` to trigger a fallback path;
        # a broader catch would mask real bugs as connection failures.
        raise ConnectionError(
            "Socket error communicating with Blender at {:s}:{:d}: {:s}".format(host, port, str(ex))
        ) from ex

    if not buf:
        raise ConnectionError(
            "{:s} (empty response from Blender)".format(_OUTCOME_UNKNOWN_MESSAGE)
        )

    # Parse only up to the first null byte delimiter.
    line, _sep, _rest = buf.partition(b"\0")
    try:
        response: dict[str, object] = json.loads(line.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as ex:
        raise ConnectionError(
            "{:s} (invalid response from Blender at {:s}:{:d}: {:s})".format(
                _OUTCOME_UNKNOWN_MESSAGE, host, port, str(ex)
            )
        ) from ex
    return response


def send_code(code: str, strict_json: bool) -> dict[str, object]:
    """
    Send Python code to the Blender add-on socket server for execution.

    Returns the full response dict from the add-on containing
    ``status`` (``"ok"`` or ``"error"``), ``result`` (on success),
    ``message`` (on error), and optionally ``stdout``/``stderr``
    captured during execution.

    Raises ``ConnectionError`` when Blender is unreachable or
    returns an invalid response. Requests are never replayed after
    transmission may have begun.
    """
    resolved = resolve_endpoint()
    host = str(resolved["host"])
    port = int(resolved["port"])
    instance = resolved["instance"]

    request: dict[str, object] = {
        "type": "execute",
        "code": code,
        "strict_json": strict_json,
    }
    if instance is not None:
        # Authenticated protocol for discovered endpoints.
        request["protocolVersion"] = instance_discovery.PROTOCOL_VERSION
        request["instanceId"] = instance.instance_id
        request["token"] = instance.token

    return _send_request(host, port, request)
