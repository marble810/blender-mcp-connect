# Release Checklist

Staged release procedure for `blender-mcp-connect`. Each release is tagged
`connect-vX.Y.Z` and must record the exact upstream Blender Lab MCP baseline
commit (see `UPSTREAM.md`).

## Before starting

- [ ] `main` merged with the intended upstream baseline; `git log` recorded.
- [ ] `CHANGELOG.md` updated (Added/Changed/Security/Upstream Baseline).
- [ ] Version aligned across:
  - `mcp/pyproject.toml`
  - `addon/blender_mcp_addon/blender_manifest.toml`
  - `addon/blender_mcp_addon/mcp_to_blender_server.py` (`EXTENSION_VERSION`)
  - `mcp/manifest.json`
- [ ] No manifest claims Blender Lab as maintainer/support owner.

## Local verification

- [ ] `python -m unittest tests.test_mcp_server tests.test_packaging \
      tests.test_instance_registry tests.test_connection \
      tests.test_addon_server_e2e -v` all green.
- [ ] `python -m build ./mcp --outdir dist`
- [ ] `python -m twine check dist/*`
- [ ] Wheel contents inspected (blmcp, data/prompts.yml, data/api, data/manual,
      entry point `blender-mcp-connect = blmcp:main`).
- [ ] Clean-directory smoke test:
      `uvx --from ./dist/blender_mcp_connect-X.Y.Z-py3-none-any.whl \
      blender-mcp-connect --list-instances`
- [ ] Extension ZIP assembled and installable in Blender 5.1+.

## Real-Blender smoke tests (Windows and Linux)

- [ ] No environment variables: single instance auto-discovered.
- [ ] Port 9876 occupied: Connect still starts.
- [ ] Two Blender processes: fails closed, lists instances.
- [ ] `BLENDER_MCP_INSTANCE=<id>` reaches the intended `.blend`.
- [ ] Hard-killed Blender leaves a harmless stale descriptor.
- [ ] Interactive and background (`--command blender_mcp`) modes publish and
      remove descriptors.
- [ ] Official legacy mode: `BLENDER_MCP_HOST`/`BLENDER_MCP_PORT` + fixed port
      extension still works.

## GitHub / PyPI

- [ ] GitHub Actions CI green on Windows/Linux/macOS.
- [ ] Tag `connect-vX.Y.Z` created on `main`.
- [ ] `publish-pypi.yml` (environment `pypi`, Trusted Publishing) publishes
      immutable PyPI version `X.Y.Z`.
- [ ] `release-extension.yml` attaches the Extension ZIP + SHA256SUMS.txt to a
      GitHub prerelease.
- [ ] GitHub prerelease promoted to stable after all smoke tests pass.
- [ ] `UPSTREAM.md` / release notes record the upstream baseline SHA.
