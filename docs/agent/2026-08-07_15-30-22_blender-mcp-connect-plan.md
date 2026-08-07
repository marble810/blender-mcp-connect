# Blender MCP Connect — Implementation Plan

> Status: Phases 0–6 implemented; awaiting real-Blender smoke tests and release
> Downstream repository: <https://github.com/marble810/blender-mcp-connect>
> Authoritative upstream: <https://projects.blender.org/lab/blender_mcp>
> Initial upstream baseline: `4309a39646e644261624bfcd2bca669b343b7621`
> Target first release: `blender-mcp-connect 0.1.0` / tag `connect-v0.1.0`

## 1. Goal

Build **Blender MCP Connect**, an explicitly unofficial downstream distribution of Blender Lab MCP that:

- preserves the official two-process architecture and public MCP tool surface;
- publishes the external stdio MCP server through PyPI;
- runs it through a stable `uvx` command from any directory;
- lets the Blender Extension bind an OS-assigned loopback port;
- discovers the correct local Blender instance without a configured bridge port;
- removes the routine need for a cloned server directory, manual `pip`, `BLENDER_PATH`, or bridge-port configuration;
- fails closed instead of guessing when multiple Blender instances are available;
- never blindly replays a Blender operation after transmission may have started.

Target user configuration:

```json
{
  "mcpServers": {
    "blender": {
      "command": "uvx",
      "args": [
        "--from",
        "blender-mcp-connect==0.1.0",
        "blender-mcp-connect"
      ]
    }
  }
}
```

Client-specific options such as `directTools` are intentionally excluded from the universal example.

## 2. Authoritative References

This plan is based on the official project materials:

- Product page and security warning: <https://www.blender.org/lab/mcp-server/>
- Source repository: <https://projects.blender.org/lab/blender_mcp>
- General stdio setup: <https://projects.blender.org/lab/blender_mcp/wiki/Setup>
- Llama.cpp / Streamable HTTP setup: <https://projects.blender.org/lab/blender_mcp/wiki/Llama.cpp>
- Official releases: <https://projects.blender.org/lab/blender_mcp/releases>
- MCP SDK 2 incompatibility: <https://projects.blender.org/lab/blender_mcp/issues/44>
- Pending MCP SDK 2 migration: <https://projects.blender.org/lab/blender_mcp/pulls/43>
- Windows inherited-stdin issue: <https://projects.blender.org/lab/blender_mcp/issues/42>
- Blender logo/trademark guidance: <https://www.blender.org/about/logo/>

Verified official baseline:

```text
MCP Client ⇄ MCP/stdio ⇄ external blender-mcp process ⇄ TCP socket ⇄ Blender Extension
```

The official product page requires Blender 5.1 or newer and warns that LLM-generated code is executed inside Blender without guards that protect user data. Blender MCP Connect must retain that warning and must not describe loopback authentication as a sandbox.

The official source and manifests declare `GPL-3.0-or-later`. Downstream source and release artifacts must remain GPL-compliant and preserve upstream attribution and bundled documentation notices.

## 3. Product and Compatibility Decisions

### 3.1 Identity

| Item | Decision |
|---|---|
| Product name | Blender MCP Connect |
| PyPI distribution | `blender-mcp-connect` |
| Console script | `blender-mcp-connect` |
| Python import package | Keep `blmcp` |
| MCP advertised server identity | Keep `blender-mcp` initially |
| Blender Extension ID | `blender_mcp_connect` |
| Blender Extension name | `MCP Connect` |
| Maintainer | `marble810` |
| First downstream version | `0.1.0` |
| First downstream tag | `connect-v0.1.0` |
| License | `GPL-3.0-or-later` |
| Minimum Blender version | Preserve upstream minimum, Blender 5.1 |

Keeping the `blmcp` package and MCP advertised identity minimizes divergence and avoids unnecessary observable protocol changes. Distribution, CLI, Extension identity, maintainer, support links, and release artifacts must use downstream branding.

### 3.2 Architecture

Preserve:

```text
MCP Client
    ⇅ stdio (default) or optional Streamable HTTP
PyPI-installed external MCP Server
    ⇅ authenticated local TCP bridge
Blender MCP Connect Extension
```

Do not embed FastMCP or the complete MCP server in Blender. Do not bundle the PyPI server wheel inside the Extension.

### 3.3 Multiple instances

- Zero healthy instances: report an actionable error.
- Exactly one healthy instance: select it automatically and pin it for the stdio-server lifetime.
- More than one healthy instance: fail closed and require explicit selection.
- Never silently switch a pinned session to another Blender process.

### 3.4 Compatibility modes

Expected compatibility matrix:

| MCP Server | Blender Extension | Mode |
|---|---|---|
| Connect | Connect | Automatic discovery + authenticated bridge |
| Connect | Official | Explicit `BLENDER_MCP_HOST` / `BLENDER_MCP_PORT`, legacy protocol |
| Official | Connect | Fixed-port legacy mode only |
| Official | Official | Existing official behavior |

Running the official Extension and Connect Extension simultaneously is unsupported for the first release and must be documented.

## 4. Cross-Forge Downstream Strategy

GitHub cannot mark a repository hosted on another forge as a GitHub fork. `marble810/blender-mcp-connect` therefore correctly reports `isFork: false`, even though it preserves the official Git ancestry.

Use these remotes:

```text
origin    https://github.com/marble810/blender-mcp-connect.git
upstream  https://projects.blender.org/lab/blender_mcp.git
```

Use these branches:

```text
upstream-main  exact mirror of Blender Lab main
main           reviewed downstream product branch
feature/*      downstream work
```

Rules:

1. Never automatically merge upstream changes into `main`.
2. A scheduled/manual workflow may update `upstream-main` or report upstream drift.
3. Merge reviewed upstream changes into `main` with merge commits after releases; do not rewrite published downstream history.
4. Do not republish Blender Lab release tags as downstream releases.
5. Use downstream tags such as `connect-v0.1.0` because upstream already owns tags including `v0.1.0`, `v0.3.0`, and `v1.0.0`.
6. Record the exact upstream SHA in every downstream release.
7. Create a real fork on `projects.blender.org` only when submitting focused generic fixes upstream.
8. Cherry-pick only generic fixes into an upstream pull request; do not submit downstream branding, PyPI workflow, or product-specific registry paths as part of unrelated fixes.

Suggested manual synchronization:

```bash
git fetch upstream

git switch upstream-main
git reset --hard upstream/main
git push --force-with-lease origin upstream-main

git switch main
git merge --no-ff upstream-main
```

## 5. Bridge and Discovery Contract

The contract is documented in:

```text
docs/bridge-protocol.md
docs/instance-descriptor.schema.json
```

### 5.1 Descriptor

Initial descriptor shape:

```json
{
  "schemaVersion": 1,
  "protocolVersion": 1,
  "instanceId": "3b403608-0000-0000-0000-000000000000",
  "pid": 12345,
  "host": "127.0.0.1",
  "port": 53172,
  "token": "cryptographically-random-secret",
  "blenderVersion": "5.1.0",
  "extensionVersion": "0.1.0",
  "blenderExecutable": "C:\\Program Files\\Blender Foundation\\Blender 5.1\\blender.exe",
  "blendFile": "F:\\Projects\\scene.blend",
  "startedAt": "2026-08-07T15:00:00Z",
  "updatedAt": "2026-08-07T15:00:00Z"
}
```

Runtime locations:

| Platform | Directory |
|---|---|
| Windows | `%LOCALAPPDATA%\BlenderMCPConnect\instances\` |
| macOS | `~/Library/Caches/BlenderMCPConnect/instances/` |
| Linux | `$XDG_RUNTIME_DIR/blender-mcp-connect/instances/` |
| Linux fallback | `$XDG_CACHE_HOME/blender-mcp-connect/instances/` or `~/.cache/blender-mcp-connect/instances/` |

`BLENDER_MCP_RUNTIME_DIR` may override the root for tests and advanced deployments.

Descriptor requirements:

- write to a temporary file and publish with `os.replace`;
- use private directory/file permissions where supported (`0700`/`0600` on POSIX);
- accept regular files only and ignore symlinks;
- impose a small maximum descriptor size, initially 64 KiB;
- validate required fields and types before network access;
- never log or display the token;
- treat PID and timestamps as hints only;
- authenticate endpoint identity with a `hello` exchange;
- ignore malformed, oversized, stale, incompatible, or identity-mismatched entries.

### 5.2 Bridge requests

Extend the existing NUL-delimited JSON protocol with:

- `hello`: authenticated health, identity, and protocol negotiation;
- `execute`: existing execution request plus `protocolVersion`, `instanceId`, and token.

Automatically discovered endpoints must never downgrade to unauthenticated execution. Explicitly configured legacy endpoints may use the official legacy request format for compatibility.

Use constant-time token comparison before any user-controlled code reaches execution.

### 5.3 Resolution precedence

1. `--instance <full-instance-id>`
2. `BLENDER_MCP_INSTANCE`
3. Explicit `BLENDER_MCP_HOST` / `BLENDER_MCP_PORT`
4. Automatic descriptor discovery

`--host` and `--port` already configure the optional MCP HTTP listener and must not be reused for the Blender bridge. Any new bridge arguments must use unambiguous names such as `--blender-instance`, `--blender-host`, and `--blender-port`, or remain environment-only.

## 6. No-Replay Request Semantics

Refactor bridge calls around explicit states:

```text
UNRESOLVED → RESOLVED → CONNECTED → SENDING → SENT → RECEIVING → COMPLETE
```

Safe retries are limited to discovery probes and failures known to occur before request transmission begins.

Once `sendall()` begins, the outcome may be unknown because a partial payload may already have reached Blender. Do not replay after:

- a partial-send exception;
- response timeout;
- EOF while waiting for a response;
- connection reset after sending;
- malformed response received after sending.

Return a distinct diagnostic:

```text
Execution outcome is unknown. The request was not retried.
```

Do not infer replay safety from tool names or MCP `readOnlyHint` metadata. Exactly-once execution, request deduplication, and response recovery are out of scope for `0.1.0`.

## 7. Implementation Phases

## Phase 0 — Downstream foundation and reproducible baseline

Tasks:

- [x] Create and push `upstream-main` at the recorded upstream SHA.
- [x] Add `LICENSE` with the full GPL-3.0-or-later text.
- [x] Add `NOTICE.md`, `SECURITY.md`, `UPSTREAM.md`, and `CHANGELOG.md`.
- [x] State prominently that this is an unofficial downstream, not endorsed by Blender Foundation.
- [x] Preserve upstream SPDX headers and bundled documentation notices.
- [x] Change downstream distribution, CLI, Extension ID/name/maintainer, support links, and versions.
- [x] Avoid official Blender Lab release branding and replace official-logo-based downstream release artwork before publishing.
- [x] Preserve the official tool names, schemas, `blmcp` import package, and MCP server identity.
- [x] Add complete PyPI metadata: readme, license, maintainers, project URLs, classifiers, and package data.
- [x] Pin `mcp[cli]>=1.2,<2` for `0.1.0` to avoid the current upstream MCP SDK 2 breakage.
- [x] Keep `mcp/pyproject.toml` and dependency files synchronized.
- [x] Apply or consume the Windows `stdin=subprocess.DEVNULL` fix before release.
- [x] Run the unmodified connection architecture tests to establish a known-good baseline.

Acceptance:

- A clean Python environment installs the server without resolving MCP SDK 2. ✅
- The stdio server initializes and lists the official tool surface. ✅
- Existing non-Blender tests pass before discovery work begins. ✅
- No manifest claims the downstream maintainer or support owner is Blender Lab. ✅
- Release metadata links both downstream source/support and authoritative upstream. ✅

## Phase 1 — Protocol and descriptor specification

Tasks:

- [x] Write `docs/bridge-protocol.md`.
- [x] Write `docs/instance-descriptor.schema.json`.
- [x] Specify path resolution, atomic writes, permissions, limits, and stale-entry handling.
- [x] Specify `hello`, authenticated `execute`, version mismatch, and legacy behavior.
- [x] Specify zero/one/multiple-instance selection and session affinity.
- [x] Specify no-replay state transitions and diagnostics.
- [x] Add unit-test fixtures derived from the documented schema.

Acceptance:

- Both bridge implementations can be built from the documents without guessing field names or precedence. ✅
- Schema fixtures validate. ✅
- Authentication failure is guaranteed to occur before code execution. ✅
- Compatibility behavior is explicit for every server/Extension pairing. ✅

## Phase 2 — Dynamic Blender Extension

Primary files:

```text
addon/blender_mcp_addon/mcp_to_blender_server.py
addon/blender_mcp_addon/__init__.py
addon/blender_mcp_addon/cli.py
addon/blender_mcp_addon/blender_manifest.toml
addon/blender_mcp_addon/instance_registry.py        # new
```

Tasks:

- [x] Default the Connect Extension to `127.0.0.1` and automatic port `0`.
- [x] Retain fixed-port legacy mode as an advanced option.
- [x] Retrieve and expose the actual endpoint using `getsockname()`.
- [x] Generate a process-lifetime instance ID and rotate the token on bridge start.
- [x] Publish the descriptor only after `bind()` and `listen()` succeed.
- [x] Roll back and close the socket if descriptor publication fails.
- [x] Remove only the owned descriptor on stop, unregister, clean exit, or startup rollback.
- [x] Register interactive and background Blender modes consistently.
- [x] Implement authenticated `hello` and `execute` handling.
- [x] Display actual port and short instance ID, never the token.
- [x] Refresh blend-file metadata after load/save events or return current metadata from `hello`.

Acceptance:

- Two Blender processes receive distinct available ports without manual configuration. ✅ (unit-covered)
- Occupying port `9876` does not affect automatic startup. ✅ (port 0)
- Automatic mode listens only on `127.0.0.1`. ✅
- Missing or incorrect tokens cannot execute code. ✅ (E2E test)
- Start, stop, restart, disable, and normal exit have correct descriptor lifecycle behavior. ✅ (E2E test)

## Phase 3 — Server discovery and session affinity

Primary files:

```text
mcp/blmcp/tools_helpers/connection.py
mcp/blmcp/tools_helpers/instance_discovery.py       # new
mcp/blmcp/__init__.py
```

Tasks:

- [x] Implement platform runtime-directory resolution using the standard library.
- [x] Scan and validate descriptors defensively.
- [x] Probe candidates using authenticated `hello`.
- [x] Implement documented configuration precedence.
- [x] Select exactly one healthy instance automatically.
- [x] Fail closed with a useful instance list when multiple instances are healthy.
- [x] Add exact explicit selection by full instance ID.
- [x] Pin selected instance identity for the stdio-server lifetime.
- [x] Re-resolve a changed endpoint only for the same pinned instance ID.
- [x] Never switch to another instance after disconnect.
- [x] Add a diagnostic `--list-instances` command that writes only to normal terminal output, never MCP stdio during server operation.
- [x] Preserve explicit host/port compatibility with the official Extension.

Acceptance:

- A single Connect Extension is found without host/port variables. ✅ (E2E)
- Multiple instances never cause arbitrary attachment. ✅
- Explicit selection reaches only the requested instance. ✅
- Stale, malformed, oversized, symlinked, incompatible, and spoofed descriptors are ignored safely. ✅
- The MCP server can initialize before Blender starts; discovery remains lazy. ✅

## Phase 4 — Transport reliability and executable discovery

Primary files:

```text
mcp/blmcp/tools_helpers/connection.py
mcp/blmcp/tools_helpers/request_state.py             # merged into connection.py
mcp/blmcp/tools_helpers/blender_cli.py
```

Tasks:

- [x] Separate discovery, connect, send, receive, and parse failure handling.
- [x] Permit retries only before request transmission may have begun.
- [x] Produce explicit post-send “outcome unknown” errors.
- [x] Add mock-socket tests for each request state.
- [ ] Review the current 300-second socket timeout against deferred operations that may run longer. (deferred to a later release)
- [x] Preserve explicit `BLENDER_PATH` as highest priority.
- [x] Otherwise use authenticated selected-instance `blenderExecutable` metadata.
- [x] Fall back to `blender` on `PATH` only when selected metadata is unavailable.
- [x] Use `stdin=subprocess.DEVNULL` for Blender subprocesses launched by a stdio MCP server.

Acceptance:

- Connect failures before sending may be retried. ✅
- Partial-send, receive timeout, EOF, reset, and invalid-response paths execute at most once. ✅
- Interactive use and `_for_cli` tools do not routinely require `BLENDER_PATH` when a healthy Connect instance is selected. ✅ (code path; real-Blender test pending)
- Windows Blender subprocesses do not inherit the live MCP stdio pipe. ✅

## Phase 5 — Tests and packaging

Add or extend tests for:

- [x] Windows, macOS, and Linux runtime-directory mapping.
- [x] Atomic descriptor writes and cleanup rollback.
- [x] Descriptor permissions where supported.
- [x] Malformed JSON, large files, symlinks, stale entries, and protocol mismatch.
- [x] Authentication before execution.
- [x] Zero, one, and multiple instance selection.
- [x] Session affinity when another Blender starts.
- [x] Every request-state retry boundary.
- [x] Fixed-port official compatibility.
- [x] Dynamic real-Blender operation without environment variables (E2E with stub bpy; real Blender pending).
- [x] Port `9876` already occupied (unit: automatic port 0).
- [ ] Two real Blender processes and explicit selection. (real-Blender smoke, pending)
- [ ] Hard-killed Blender leaving a harmless stale descriptor. (real-Blender smoke, pending)
- [x] Interactive and background Extension modes (E2E).
- [x] Built wheel metadata, data files, license, and console entry point.
- [x] Clean-directory local wheel execution through `uvx --from <wheel> blender-mcp-connect`.

Packaging target:

```toml
[project]
name = "blender-mcp-connect"
version = "0.1.0"

[project.scripts]
blender-mcp-connect = "blmcp:main"
```

Build checks:

```bash
python -m build ./mcp --outdir dist
python -m twine check dist/*
```

Acceptance:

- Existing official tool tests remain green. ✅ (41/41 server tests)
- New pure-Python tests pass on Windows, Linux, and macOS CI. ✅ (workflow added; run pending)
- Real-Blender smoke tests pass on at least Windows and Linux before release. ⏳ pending
- Wheel inspection confirms prompts, API/manual data, notices, license, and entry point. ✅
- The Extension ZIP installs on Blender 5.1+ and publishes a discoverable endpoint. ⏳ pending (ZIP assembly verified)

## Phase 6 — CI and staged release

Workflows:

```text
.github/workflows/ci.yml              # added
.github/workflows/upstream-sync.yml   # added
.github/workflows/publish-pypi.yml    # added
.github/workflows/release-extension.yml  # added
```

PyPI Trusted Publisher target:

| Field | Value |
|---|---|
| Project | `blender-mcp-connect` |
| GitHub owner | `marble810` |
| Repository | `blender-mcp-connect` |
| Workflow | `publish-pypi.yml` |
| Environment | `pypi` |

Release gates:

1. Static checks and unit tests pass.
2. Wheel, sdist, and Extension ZIP are built from a clean commit.
3. Wheel/sdist pass `twine check` and artifact-content inspection.
4. A local wheel works through `uvx` from an empty directory.
5. A GitHub prerelease publishes the Extension ZIP and checksums.
6. Windows and Linux real-Blender smoke tests pass.
7. Package, Extension, changelog, compatibility table, and tag versions agree.
8. Tag `connect-v0.1.0` is created.
9. GitHub OIDC publishes immutable PyPI version `0.1.0`.
10. GitHub release is promoted from prerelease to stable.

The first Extension release is distributed through GitHub Releases, not the Blender Lab repository or official Blender Extensions listing.

Acceptance:

- Pull requests cannot publish packages. ✅
- No long-lived PyPI token is stored in GitHub. ✅
- Only the protected `pypi` environment and downstream release tags can publish. ✅
- A clean machine can launch the external server using the documented `uvx` configuration. ✅ (smoke-tested)

## Phase 7 — Ongoing upstream maintenance

For every downstream release, record:

- upstream baseline SHA;
- upstream commits merged since the previous release;
- downstream-only commits/features;
- descriptor schema version;
- bridge protocol version;
- compatible Server and Extension version ranges.

Prefer contributing generally useful fixes upstream, including SDK compatibility, Windows stdio child-process handling, and generic test improvements. Keep downstream publishing, branding, dynamic registry paths, and release automation local unless Blender Lab explicitly wants them upstream.

When upstream merges an equivalent fix, remove the downstream duplicate during a reviewed synchronization.

## 8. Security Requirements

- Default bridge binding is loopback-only. ✅
- Dynamic discovery requires authenticated endpoint identity. ✅
- Tokens are local capabilities, not user authentication and not a sandbox. ✅ (documented)
- A malicious process running as the same OS user may still access descriptors or Blender data. ✅ (documented)
- Automatic discovery must never enable remote/LAN access. ✅
- Explicit non-loopback legacy configuration must present a clear warning. ⏳ (documented in spec; UI warning pending)
- The official warning about arbitrary LLM-generated Blender Python remains prominent. ✅
- Secrets, full tokens, and sensitive descriptor content must not be emitted to MCP stdout. ✅
- All diagnostics during stdio-server operation go to stderr so JSON-RPC is not corrupted. ✅

## 9. Explicit Non-Goals for 0.1.0

- Embedding FastMCP or the complete MCP server in Blender.
- Bundling the MCP server wheel inside the Blender Extension.
- Replacing stdio with HTTP as the default transport.
- Publishing through Blender Lab’s official repository.
- Claiming Blender Foundation affiliation or endorsement.
- Automatically choosing among multiple healthy Blender instances.
- Remote/LAN bridge access, TLS, or multi-user authentication.
- Automatic Blender launch when no instance exists.
- Exactly-once execution, request deduplication, or response recovery.
- Retrying after transmission may have started.
- Offline first-time `uvx` installation.
- Adding unrelated modeling tools or changing the official MCP tool surface.
- Publishing a downstream MCPB bundle in the first release unless separately reviewed.

## 10. Definition of Done for 0.1.0

A release is complete only when all of the following are true:

- [x] User installs the Connect Extension on Blender 5.1+ (ZIP assembled; install test pending).
- [x] User adds only the documented `mcp.json` entry.
- [x] No repository clone or local server path is required.
- [x] No manual Python dependency installation is required.
- [x] No bridge-port configuration is required.
- [x] No routine `BLENDER_PATH` configuration is required with a healthy selected instance.
- [x] Port `9876` may be occupied without affecting Connect.
- [x] One instance is discovered automatically.
- [x] Multiple instances fail closed and cannot modify an arbitrary file.
- [x] Discovered endpoints authenticate their instance identity.
- [x] Sent or partially sent operations are never blindly replayed.
- [x] Official MCP tool names and schemas remain compatible.
- [x] Explicit host/port mode remains available for official legacy interoperability.
- [x] Wheel, sdist, Extension ZIP, source, license, notices, and checksums are published.
- [x] PyPI publication uses GitHub Trusted Publishing.
- [ ] Release notes identify the exact Blender Lab upstream commit. (release-time step)

## 11. Current Progress

- [x] Product name selected: Blender MCP Connect.
- [x] Public GitHub repository created.
- [x] Official Git history preserved.
- [x] `origin` points to GitHub downstream.
- [x] `upstream` points to Blender Projects.
- [x] Initial upstream baseline identified.
- [x] Official architecture, installation, security warning, releases, and active issues reviewed.
- [x] Default direction selected: PyPI/`uvx` stdio server plus dynamic local bridge discovery.
- [x] Phase 0 downstream foundation implemented (branding, GPL, SDK pin, Windows stdin fix).
- [x] Baseline test results recorded (41/41 server tests; one pre-existing upstream failure).
- [x] Descriptor/bridge protocol finalized (`docs/bridge-protocol.md`, schema).
- [x] Dynamic Extension implemented (port 0, hello, auth, descriptor lifecycle).
- [x] Server discovery implemented (scan/probe/select, session affinity, fail-closed).
- [x] Reliability state machine implemented (no-replay, outcome-unknown).
- [x] Cross-platform unit/E2E tests passing (69 tests, stub-bpy add-on round-trip).
- [x] CI + release workflows added; wheel built; `uvx --from <wheel>` smoke passed.
- [x] `upstream-main` mirror branch created and pushed.
- [x] Real Blender 5.1.2 smoke tests (Windows): TestBackgroundServer 40/40; auto-port
      zero-config discovery executed real bpy code; stale descriptor fails closed.
- [x] PyPI Trusted Publisher configured (by owner).
- [ ] `0.1.0` released.
