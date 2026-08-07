# SPDX-FileCopyrightText: 2026 Blender Authors
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Unit tests for server-side instance discovery and connection resolution.

Uses a fake authenticated bridge server (plain sockets) so no Blender is
required. Run with::

    python -m unittest tests.test_connection -v
"""

__all__ = ()

import json
import os
import socket
import sys
import tempfile
import threading
import unittest

_REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_MCP_DIR = os.path.join(_REPO_DIR, "mcp")
if _MCP_DIR not in sys.path:
    sys.path.insert(0, _MCP_DIR)

from blmcp.tools_helpers import connection, instance_discovery  # noqa: E402


class FakeBridge:
    """
    Minimal authenticated bridge server speaking the Connect protocol.

    Responds to ``hello`` and ``execute`` with NUL-delimited JSON.
    """

    def __init__(self, instance_id: str, token: str, *, require_auth: bool = True) -> None:
        self.instance_id = instance_id
        self.token = token
        self.require_auth = require_auth
        self.requests: list[dict[str, object]] = []
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind(("127.0.0.1", 0))
        self.sock.listen(4)
        self.host, self.port = self.sock.getsockname()
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()

    def _serve(self) -> None:
        while True:
            try:
                conn, _addr = self.sock.accept()
            except OSError:
                return
            try:
                conn.settimeout(5)
                buf = bytearray()
                while b"\0" not in buf:
                    chunk = conn.recv(4096)
                    if not chunk:
                        return
                    buf.extend(chunk)
                request = json.loads(buf.partition(b"\0")[0].decode("utf-8"))
                self.requests.append(request)
                response = self._respond(request)
                conn.sendall((json.dumps(response) + "\0").encode("utf-8"))
            except (OSError, ValueError):
                pass
            finally:
                conn.close()

    def _authenticated(self, request: dict[str, object]) -> bool:
        if not self.require_auth:
            return True
        return (
            request.get("protocolVersion") == instance_discovery.PROTOCOL_VERSION
            and request.get("instanceId") == self.instance_id
            and request.get("token") == self.token
        )

    def _respond(self, request: dict[str, object]) -> dict[str, object]:
        if request.get("type") == "hello":
            if not self._authenticated(request):
                return {"status": "error", "message": "Authentication failed"}
            return {
                "status": "ok",
                "result": {
                    "protocolVersion": instance_discovery.PROTOCOL_VERSION,
                    "instanceId": self.instance_id,
                    "blenderVersion": "5.1.0",
                    "extensionVersion": "0.1.0",
                    "blendFile": "",
                },
            }
        if request.get("type") == "execute":
            if not self._authenticated(request):
                return {"status": "error", "message": "Authentication failed"}
            return {"status": "ok", "result": {"executed": str(request.get("code"))}}
        return {"status": "error", "message": "Unknown request type"}

    def close(self) -> None:
        """
        Stop accepting and join the serve thread.

        On POSIX, closing a listener while another thread blocks in
        ``accept()`` does not wake it (the thread still holds the fd), so
        the port keeps accepting connections. ``shutdown()`` wakes the
        blocked accept; joining then releases the fd for good.
        """
        try:
            self.sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        self.sock.close()
        self._thread.join(timeout=5)


class _DescriptorEnv:
    def __init__(self, testcase: unittest.TestCase) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self._testcase = testcase
        self._old_env: dict[str, str | None] = {}
        for key in (
            "BLENDER_MCP_RUNTIME_DIR",
            "BLENDER_MCP_INSTANCE",
            "BLENDER_MCP_HOST",
            "BLENDER_MCP_PORT",
            "BLENDER_PATH",
        ):
            self._old_env[key] = os.environ.pop(key, None)
        os.environ["BLENDER_MCP_RUNTIME_DIR"] = self._tmp.name

    def cleanup(self) -> None:
        for key, value in self._old_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self._tmp.cleanup()

    def write_descriptor(self, bridge: FakeBridge, *, pid: int = 9999) -> None:
        os.makedirs(instance_discovery.runtime_dir(), exist_ok=True)
        path = os.path.join(instance_discovery.runtime_dir(), bridge.instance_id + ".json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump({
                "schemaVersion": 1,
                "protocolVersion": 1,
                "instanceId": bridge.instance_id,
                "pid": pid,
                "host": bridge.host,
                "port": bridge.port,
                "token": bridge.token,
                "blenderVersion": "5.1.0",
                "extensionVersion": "0.1.0",
                "blenderExecutable": "C:\\blender.exe",
                "blendFile": "F:\\scene.blend",
                "startedAt": "2026-08-07T00:00:00Z",
            }, fh)


class TestDiscovery(unittest.TestCase):
    def setUp(self) -> None:
        self._env = _DescriptorEnv(self)
        self._bridges: list[FakeBridge] = []
        # Reset session affinity between tests.
        connection._selected_instance = None  # type: ignore[attr-defined]

    def tearDown(self) -> None:
        for bridge in self._bridges:
            bridge.close()
        self._env.cleanup()

    def _bridge(self, instance_id: str, token: str | None = None) -> FakeBridge:
        bridge = FakeBridge(instance_id, token or ("t" * 64))
        self._bridges.append(bridge)
        return bridge

    def test_single_instance_auto_discovery(self) -> None:
        bridge = self._bridge("11111111-1111-1111-1111-111111111111")
        self._env.write_descriptor(bridge)

        resolved = connection.resolve_endpoint()
        self.assertEqual(resolved["host"], "127.0.0.1")
        self.assertEqual(resolved["port"], bridge.port)
        self.assertIsNotNone(resolved["instance"])

        response = connection.send_code("1 + 1", strict_json=True)
        self.assertEqual(response["status"], "ok")
        # The execute request must carry the authenticated fields.
        request = bridge.requests[-1]
        self.assertEqual(request["type"], "execute")
        self.assertEqual(request["instanceId"], bridge.instance_id)
        self.assertEqual(request["token"], bridge.token)
        self.assertEqual(request["protocolVersion"], instance_discovery.PROTOCOL_VERSION)

    def test_zero_instances_error(self) -> None:
        with self.assertRaises(ConnectionError) as ctx:
            connection.resolve_endpoint()
        self.assertIn("No Blender MCP Connect instance", str(ctx.exception))

    def test_multiple_instances_fail_closed(self) -> None:
        a = self._bridge("22222222-2222-2222-2222-222222222222")
        b = self._bridge("33333333-3333-3333-3333-333333333333")
        self._env.write_descriptor(a)
        self._env.write_descriptor(b)

        with self.assertRaises(ConnectionError) as ctx:
            connection.resolve_endpoint()
        message = str(ctx.exception)
        self.assertIn("Multiple healthy Blender instances", message)
        self.assertIn(a.instance_id, message)
        self.assertIn(b.instance_id, message)

    def test_explicit_instance_selection(self) -> None:
        a = self._bridge("44444444-4444-4444-4444-444444444444")
        b = self._bridge("55555555-5555-5555-5555-555555555555")
        self._env.write_descriptor(a)
        self._env.write_descriptor(b)

        os.environ["BLENDER_MCP_INSTANCE"] = b.instance_id
        resolved = connection.resolve_endpoint()
        self.assertEqual(resolved["port"], b.port)

        response = connection.send_code("result = 42", strict_json=True)
        self.assertEqual(response["status"], "ok")
        self.assertEqual(b.requests[-1]["instanceId"], b.instance_id)
        self.assertNotIn(a.requests, [])

    def test_explicit_missing_instance_error(self) -> None:
        os.environ["BLENDER_MCP_INSTANCE"] = "66666666-6666-6666-6666-666666666666"
        with self.assertRaises(ConnectionError) as ctx:
            connection.resolve_endpoint()
        self.assertIn("66666666", str(ctx.exception))

    def test_stale_and_malformed_descriptors_ignored(self) -> None:
        bridge = self._bridge("77777777-7777-7777-7777-777777777777")
        self._env.write_descriptor(bridge)

        directory = instance_discovery.runtime_dir()
        # Malformed JSON.
        with open(os.path.join(directory, "bad.json"), "w", encoding="utf-8") as fh:
            fh.write("{not json")
        # Wrong schema version.
        with open(os.path.join(directory, "old.json"), "w", encoding="utf-8") as fh:
            json.dump({
                "schemaVersion": 99,
                "protocolVersion": 1,
                "instanceId": "88888888-8888-8888-8888-888888888888",
                "pid": 1,
                "host": "127.0.0.1",
                "port": 1,
                "token": "t" * 64,
            }, fh)
        # No token.
        with open(os.path.join(directory, "notoken.json"), "w", encoding="utf-8") as fh:
            json.dump({"schemaVersion": 1, "protocolVersion": 1}, fh)

        discovered = instance_discovery.discover_instances()
        self.assertEqual([d.instance_id for d in discovered], [bridge.instance_id])

    def test_legacy_explicit_host_port(self) -> None:
        # A legacy endpoint that does not match any descriptor uses the
        # official unauthenticated request format.
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        legacy_port = listener.getsockname()[1]

        captured: list[dict[str, object]] = []

        def _serve_legacy() -> None:
            conn, _addr = listener.accept()
            conn.settimeout(5)
            buf = bytearray()
            while b"\0" not in buf:
                chunk = conn.recv(4096)
                if not chunk:
                    return
                buf.extend(chunk)
            captured.append(json.loads(buf.partition(b"\0")[0].decode("utf-8")))
            conn.sendall((json.dumps({"status": "ok", "result": {}}) + "\0").encode("utf-8"))
            conn.close()

        thread = threading.Thread(target=_serve_legacy, daemon=True)
        thread.start()

        os.environ["BLENDER_MCP_HOST"] = "127.0.0.1"
        os.environ["BLENDER_MCP_PORT"] = str(legacy_port)
        try:
            response = connection.send_code("1 + 1", strict_json=True)
            self.assertEqual(response["status"], "ok")
            self.assertEqual(captured[0]["type"], "execute")
            # No authentication fields in legacy mode.
            self.assertNotIn("token", captured[0])
            self.assertNotIn("protocolVersion", captured[0])
        finally:
            listener.close()

    def test_session_affinity_not_switched(self) -> None:
        a = self._bridge("99999999-9999-9999-9999-999999999999")
        self._env.write_descriptor(a)
        resolved = connection.resolve_endpoint()
        self.assertEqual(resolved["port"], a.port)

        # The pinned instance dies; a new one appears but must not be chosen.
        a.close()
        b = self._bridge("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
        self._env.write_descriptor(b)
        with self.assertRaises(ConnectionError) as ctx:
            connection.resolve_endpoint()
        self.assertIn("no longer reachable", str(ctx.exception))
        self.assertIn(a.instance_id, str(ctx.exception))


class TestNoReplay(unittest.TestCase):
    def test_post_send_failure_marks_outcome_unknown(self) -> None:
        # Server accepts the connection but closes before responding.
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        port = listener.getsockname()[1]

        def _serve_and_drop() -> None:
            conn, _addr = listener.accept()
            conn.recv(4096)
            conn.close()

        thread = threading.Thread(target=_serve_and_drop, daemon=True)
        thread.start()

        try:
            with self.assertRaises(ConnectionError) as ctx:
                connection._send_request(  # type: ignore[attr-defined]
                    "127.0.0.1", port, {"type": "execute", "code": "x", "strict_json": True})
            self.assertIn("Execution outcome is unknown", str(ctx.exception))
        finally:
            listener.close()


if __name__ == "__main__":
    unittest.main()
