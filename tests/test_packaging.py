# SPDX-FileCopyrightText: 2026 Blender Authors
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Packaging metadata tests (no build required).

Verifies the PyPI distribution metadata in ``mcp/pyproject.toml`` and the
Blender extension manifest stay aligned with the downstream identity.

Run with::

    python -m unittest tests.test_packaging -v
"""

__all__ = ()

import os
import re
import tomllib
import unittest

_REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_MCP_PYPROJECT = os.path.join(_REPO_DIR, "mcp", "pyproject.toml")
_MANIFEST_TOML = os.path.join(_REPO_DIR, "addon", "blender_mcp_addon", "blender_manifest.toml")
_MCPB_MANIFEST = os.path.join(_REPO_DIR, "mcp", "manifest.json")
_SERVER_MODULE = os.path.join(_REPO_DIR, "addon", "blender_mcp_addon", "mcp_to_blender_server.py")


class TestPyProject(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        with open(_MCP_PYPROJECT, "rb") as fh:
            cls.data = tomllib.load(fh)

    def test_distribution_name(self) -> None:
        self.assertEqual(self.data["project"]["name"], "blender-mcp-connect")

    def test_console_script(self) -> None:
        self.assertEqual(
            self.data["project"]["scripts"]["blender-mcp-connect"],
            "blmcp:main",
        )

    def test_mcp_sdk_pinned_below_2(self) -> None:
        deps = self.data["project"]["dependencies"]
        self.assertIn("mcp[cli]>=1.2,<2", deps)

    def test_license_gpl(self) -> None:
        self.assertIn("GPL", self.data["project"]["license"]["text"])

    def test_upstream_url(self) -> None:
        urls = self.data["project"]["urls"]
        self.assertIn("projects.blender.org/lab/blender_mcp", urls["Upstream"])


class TestExtensionManifest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        with open(_MANIFEST_TOML, "rb") as fh:
            cls.data = tomllib.load(fh)

    def test_id(self) -> None:
        self.assertEqual(self.data["id"], "blender_mcp_connect")

    def test_name(self) -> None:
        self.assertEqual(self.data["name"], "MCP Connect")

    def test_not_blender_lab(self) -> None:
        self.assertNotEqual(self.data["maintainer"], "Blender Lab")

    def test_version_matches_server(self) -> None:
        with open(_MCP_PYPROJECT, "rb") as fh:
            pyproject = tomllib.load(fh)
        self.assertEqual(self.data["version"], pyproject["project"]["version"])


class TestExtensionVersionConstant(unittest.TestCase):
    def test_extension_version_matches_manifest(self) -> None:
        with open(_MANIFEST_TOML, "rb") as fh:
            manifest = tomllib.load(fh)
        with open(_SERVER_MODULE, "r", encoding="utf-8") as fh:
            source = fh.read()
        match = re.search(r'EXTENSION_VERSION = "([^"]+)"', source)
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), manifest["version"])


if __name__ == "__main__":
    unittest.main()
