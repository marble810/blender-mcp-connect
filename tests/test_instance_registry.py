# SPDX-FileCopyrightText: 2026 Blender Authors
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Unit tests for the add-on side instance descriptor registry.

Pure standard-library tests; no Blender required. Run with::

    python -m unittest tests.test_instance_registry -v
"""

__all__ = ()

import json
import os
import sys
import tempfile
import unittest

_REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ADDON_DIR = os.path.join(_REPO_DIR, "addon", "blender_mcp_addon")
if _ADDON_DIR not in sys.path:
    sys.path.insert(0, _ADDON_DIR)

import instance_registry  # noqa: E402


class TestRuntimeDir(unittest.TestCase):
    def test_override_env(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["BLENDER_MCP_RUNTIME_DIR"] = tmp
            try:
                self.assertEqual(
                    instance_registry.runtime_dir(),
                    os.path.join(tmp, instance_registry.INSTANCE_DIR_NAME),
                )
            finally:
                del os.environ["BLENDER_MCP_RUNTIME_DIR"]


class TestWriteRemove(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        os.environ["BLENDER_MCP_RUNTIME_DIR"] = self._tmp.name

    def tearDown(self) -> None:
        del os.environ["BLENDER_MCP_RUNTIME_DIR"]
        self._tmp.cleanup()

    def _write(self, instance_id: str, **overrides) -> str:
        kwargs = {
            "instance_id": instance_id,
            "pid": 1234,
            "host": "127.0.0.1",
            "port": 54321,
            "token": "x" * 64,
            "blender_version": "5.1.0",
            "extension_version": "0.1.0",
            "blender_executable": "C:\\blender.exe",
            "blend_file": "",
        }
        kwargs.update(overrides)
        return instance_registry.write_descriptor(**kwargs)

    def test_write_creates_valid_descriptor(self) -> None:
        instance_id = instance_registry.new_instance_id()
        path = self._write(instance_id)
        self.assertTrue(os.path.isfile(path))
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        self.assertEqual(data["schemaVersion"], instance_registry.SCHEMA_VERSION)
        self.assertEqual(data["protocolVersion"], instance_registry.PROTOCOL_VERSION)
        self.assertEqual(data["instanceId"], instance_id)
        self.assertEqual(data["port"], 54321)
        self.assertEqual(data["host"], "127.0.0.1")
        self.assertTrue(data["startedAt"])
        # No temporary files left behind.
        self.assertEqual(
            [n for n in os.listdir(instance_registry.runtime_dir()) if n.startswith(".tmp-")],
            [],
        )

    def test_remove_only_owned(self) -> None:
        instance_id = instance_registry.new_instance_id()
        self._write(instance_id)
        # Removing with a different ID must not delete the file.
        self.assertFalse(instance_registry.remove_descriptor("00000000-0000-0000-0000-000000000000"))
        self.assertTrue(os.path.isfile(instance_registry._descriptor_path(instance_id)))  # type: ignore[attr-defined]
        # Removing with the matching ID succeeds.
        self.assertTrue(instance_registry.remove_descriptor(instance_id))
        self.assertFalse(os.path.exists(instance_registry._descriptor_path(instance_id)))  # type: ignore[attr-defined]

    def test_remove_missing_is_false(self) -> None:
        self.assertFalse(instance_registry.remove_descriptor("00000000-0000-0000-0000-000000000000"))

    def test_new_token_random(self) -> None:
        a = instance_registry.new_token()
        b = instance_registry.new_token()
        self.assertNotEqual(a, b)
        self.assertEqual(len(a), 64)

    def test_new_instance_id_uuid(self) -> None:
        a = instance_registry.new_instance_id()
        b = instance_registry.new_instance_id()
        self.assertNotEqual(a, b)
        self.assertEqual(len(a), 36)
        self.assertEqual(a.count("-"), 4)


if __name__ == "__main__":
    unittest.main()
