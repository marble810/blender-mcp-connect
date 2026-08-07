# Changelog

All notable changes to this project are documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and
versions use [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Downstream releases are tagged `connect-vX.Y.Z`. Each release records the
exact upstream Blender Lab MCP baseline commit it is based on.

## [Unreleased]

### Added

- Downstream foundation: `LICENSE` (GPL-3.0-or-later), `NOTICE.md`,
  `SECURITY.md`, `UPSTREAM.md`, `CHANGELOG.md`.
- `upstream-main` mirror branch tracking Blender Lab `main`.

### Changed

- PyPI distribution renamed from `blender-mcp` to `blender-mcp-connect`
  (console script: `blender-mcp-connect`).
- Blender Extension identity renamed: ID `blender_mcp_connect`, name
  `MCP Connect`, maintainer `marble810`.
- Pinned `mcp[cli]>=1.2,<2` to avoid the upstream MCP SDK 2 breakage
  (upstream issue #44).
- Windows Blender CLI subprocesses now use `stdin=subprocess.DEVNULL`
  (upstream issue #42).

### Security

- None yet.

### Upstream Baseline

- `4309a39646e644261624bfcd2bca669b343b7621` — "Fix: screenshot size limit
  didn't account for the JSON envelope"
