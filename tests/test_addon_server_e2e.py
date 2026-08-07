# SPDX-FileCopyrightText: 2026 Blender Authors
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""
End-to-end test: add-on bridge server ⇄ descriptor discovery ⇄ MCP client.

Runs the real ``mcp_to_blender_server`` (with a stub ``bpy`` so the add-on
package imports outside Blender) against the real server-side discovery and
``send_code`` client over the wire. No Blender required. Run with::

    python -m unittest tests.test_addon_server_e2e -v
"""

__all__ = ()

import importlib.util
import json
import os
import sys
import tempfile
import threading
import time
import types
import unittest

_REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ADDON_DIR = os.path.join(_REPO_DIR, "addon")
_MCP_DIR = os.path.join(_REPO_DIR, "mcp")

# Minimal ``bpy`` stub so the add-on package can be imported outside Blender.
# All real ``bpy`` use inside the add-on is lazy (function-local imports).
def _install_bpy_stub() -> None:
    bpy = types.ModuleType("bpy")
    bpy_types = types.ModuleType("bpy.types")

    class AddonPreferences:
        pass

    class Operator:
        bl_idname = ""
        bl_label = ""

    class Context:
        pass

    bpy_types.AddonPreferences = AddonPreferences
    bpy_types.Operator = Operator
    bpy_types.Context = Context
    bpy.types = bpy_types

    bpy_props = types.ModuleType("bpy.props")

    def _prop(*_args, **_kwargs):
        return None

    bpy_props.BoolProperty = _prop
    bpy_props.FloatProperty = _prop
    bpy_props.IntProperty = _prop
    bpy_props.StringProperty = _prop
    bpy.props = bpy_props

    bpy_ops = types.ModuleType("bpy.ops")

    def _op_create_function(_module, _func):
        def _op(*_args, **_kwargs):
            return None

        return _op

    bpy_ops._op_create_function = _op_create_function
    bpy.ops = bpy_ops

    sys.modules["bpy"] = bpy
    sys.modules["bpy.types"] = bpy_types
    sys.modules["bpy.props"] = bpy_props
    sys.modules["bpy.ops"] = bpy_ops


class TestAddonServerE2E(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if "bpy" not in sys.modules:
            _install_bpy_stub()
        if _ADDON_DIR not in sys.path:
            sys.path.insert(0, _ADDON_DIR)
        if _MCP_DIR not in sys.path:
            sys.path.insert(0, _MCP_DIR)
        cls.server = importlib.import_module("blender_mcp_addon.mcp_to_blender_server")
        from blmcp.tools_helpers import connection as conn
        cls.connection = conn

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self._old_env: dict[str, str | None] = {}
        for key in ("BLENDER_MCP_RUNTIME_DIR", "BLENDER_MCP_INSTANCE",
                    "BLENDER_MCP_HOST", "BLENDER_MCP_PORT", "BLENDER_PATH"):
            self._old_env[key] = os.environ.pop(key, None)
        os.environ["BLENDER_MCP_RUNTIME_DIR"] = self._tmp.name
        self.connection._selected_instance = None  # type: ignore[attr-defined]
        self._poll_thread: threading.Thread | None = None
        self._stop_poll = False

    def tearDown(self) -> None:
        try:
            self.server.stop()
        except Exception:  # pylint: disable=broad-exception-caught
            pass
        self._stop_poll = True
        if self._poll_thread is not None:
            self._poll_thread.join(timeout=5)
        for key, value in self._old_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self._tmp.cleanup()

    def _start_poll_loop(self) -> None:
        def _loop() -> None:
            while not self._stop_poll:
                try:
                    if self.server.poll():
                        pass
                except Exception:  # pylint: disable=broad-exception-caught
                    pass
                time.sleep(0.005)

        self._poll_thread = threading.Thread(target=_loop, daemon=True)
        self._poll_thread.start()

    def test_auto_discovery_execute_roundtrip(self) -> None:
        host, port = self.server.start("127.0.0.1", 0)
        self.assertEqual(host, "127.0.0.1")
        self.assertNotEqual(port, 0)
        self._start_poll_loop()

        # Descriptor published on disk.
        from blender_mcp_addon import instance_registry
        entries = [n for n in os.listdir(instance_registry.runtime_dir()) if n.endswith(".json")]
        self.assertEqual(len(entries), 1)
        self.assertTrue(entries[0].startswith(self.server.instance_id()))

        # Client auto-discovers with no host/port configuration.
        response = self.connection.send_code("result = {'sum': 2 + 2}", strict_json=True)
        self.assertEqual(response["status"], "ok")
        self.assertEqual(response["result"], {"sum": 4})

    def test_wrong_token_rejected(self) -> None:
        host, port = self.server.start("127.0.0.1", 0)
        self._start_poll_loop()
        import socket as socket_module

        def _send(raw: dict[str, object]) -> dict[str, object]:
            s = socket_module.create_connection((host, port), timeout=3)
            try:
                s.sendall((json.dumps(raw) + "\0").encode("utf-8"))
                buf = bytearray()
                while b"\0" not in buf:
                    chunk = s.recv(65536)
                    if not chunk:
                        break
                    buf.extend(chunk)
                return json.loads(buf.partition(b"\0")[0].decode("utf-8"))
            finally:
                s.close()

        response = _send({
            "type": "execute",
            "code": "result = 1",
            "strict_json": True,
            "protocolVersion": 1,
            "instanceId": self.server.instance_id(),
            "token": "x" * 64,
        })
        self.assertEqual(response["status"], "error")
        self.assertIn("Authentication failed", response["message"])

        # Legacy request without token must be rejected in automatic mode.
        response = _send({"type": "execute", "code": "result = 1", "strict_json": True})
        self.assertEqual(response["status"], "error")
        self.assertIn("requires", response["message"])

    def test_stop_removes_descriptor(self) -> None:
        self.server.start("127.0.0.1", 0)
        from blender_mcp_addon import instance_registry
        directory = instance_registry.runtime_dir()
        self.assertEqual(len([n for n in os.listdir(directory) if n.endswith(".json")]), 1)
        self.server.stop()
        self.assertEqual([n for n in os.listdir(directory) if n.endswith(".json")], [])


if __name__ == "__main__":
    unittest.main()
