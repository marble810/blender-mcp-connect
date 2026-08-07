# Bridge Protocol Specification

Status: normative for `blender-mcp-connect` 0.1.x
Descriptor schema: [`docs/instance-descriptor.schema.json`](instance-descriptor.schema.json)

## 1. Overview

```
MCP Client ⇄ MCP/stdio ⇄ blender-mcp-connect (external process)
                              ⇅ local TCP, NUL-delimited JSON
                       Blender MCP Connect Extension (in Blender)
```

The Blender Extension binds a loopback TCP socket on an OS-assigned port and
publishes a descriptor file. The external MCP server discovers descriptors,
authenticates with a per-instance token, then relays tool requests.

## 2. Descriptor

### 2.1 Runtime directory

| Platform | Root directory |
|---|---|
| Windows | `%LOCALAPPDATA%\BlenderMCPConnect\instances\` |
| macOS | `~/Library/Caches/BlenderMCPConnect/instances/` |
| Linux | `$XDG_RUNTIME_DIR/blender-mcp-connect/instances/` |
| Linux fallback | `$XDG_CACHE_HOME/blender-mcp-connect/instances/` then `~/.cache/blender-mcp-connect/instances/` |

`BLENDER_MCP_RUNTIME_DIR` overrides the root (tests, advanced use).

### 2.2 File format

- One JSON file per Blender instance, named `<instanceId>.json`.
- Schema: `docs/instance-descriptor.schema.json` (schemaVersion 1).
- Max size 64 KiB. Regular files only; symlinks are ignored.
- POSIX permissions: directory `0700`, file `0600` where supported.

### 2.3 Lifecycle

1. Extension generates `instanceId` (UUIDv4) and a fresh random token on
   every bridge start.
2. `bind()` + `listen()` must succeed **before** the descriptor is written.
3. Descriptor write failure rolls back startup: socket is closed.
4. On stop/unregister/normal exit the extension deletes **only its own**
   descriptor (matched by instanceId).
5. Crashes leave stale descriptors; the MCP server treats PID/timestamps as
   hints only and validates identity via the authenticated `hello` handshake.

### 2.4 Security rules

- Token never appears in logs, UI, or MCP stdout.
- Token comparison uses constant-time comparison.
- Automatic discovery never downgrades to unauthenticated requests.
- A descriptor is a local capability; same-OS-user processes can read it.
  Loopback binding and tokens are **not** a sandbox.

## 3. Wire protocol

Framing: one JSON object per request/response, NUL (`\0`) terminated,
UTF-8 encoded. Same as the official bridge protocol, extended with an
authenticated `hello` and token-carrying `execute`.

### 3.1 `hello` (client → extension)

```json
{"type": "hello", "protocolVersion": 1, "instanceId": "…", "token": "…"}
```

Extension validates:

- `protocolVersion` equals its own; otherwise responds with
  `{"status":"error","message":"Protocol version mismatch …"}`.
- `instanceId` matches the running instance and `token` matches via
  constant-time comparison.

Response:

```json
{
  "status": "ok",
  "result": {
    "protocolVersion": 1,
    "instanceId": "…",
    "blenderVersion": "5.1.0",
    "extensionVersion": "0.1.0",
    "blendFile": "F:\\Projects\\scene.blend"
  }
}
```

Any `status != "ok"` or missing/mismatched `result.instanceId` means the
descriptor is invalid/stale; the candidate is rejected.

### 3.2 `execute` (client → extension)

```json
{
  "type": "execute",
  "code": "…",
  "strict_json": true,
  "protocolVersion": 1,
  "instanceId": "…",
  "token": "…"
}
```

Extension behavior:

1. Validate `protocolVersion` (mismatch → error, no execution).
2. Constant-time compare `token` (failure → error, no execution).
3. Compare `instanceId` (failure → error, no execution).
4. Execute `code` exactly as the official add-on does.

### 3.3 Legacy mode

Explicitly configured legacy endpoints (`BLENDER_MCP_HOST` /
`BLENDER_MCP_PORT` with no matching descriptor) accept the official legacy
`{"type":"execute","code":…,"strict_json":…}` request format without token.
Automatic discovery must never use legacy mode.

## 4. MCP-server-side discovery

Resolution precedence (highest first):

1. `--blender-instance <full-instance-id>`
2. `BLENDER_MCP_INSTANCE`
3. `BLENDER_MCP_HOST` / `BLENDER_MCP_PORT` (legacy explicit mode)
4. Automatic descriptor scan

### 4.1 Scan & probe

- Scan runtime directory, validate schema (size, regular file, fields).
- Probe each candidate with `hello` (short timeout, e.g. 2 s).
- A probe failure or identity mismatch rejects the candidate; the stale
  descriptor is left in place (removed later only after age threshold +
  authoritative failure).

### 4.2 Selection

| Healthy candidates | Behavior |
|---|---|
| 0 | Actionable error: install/enable the Extension and start its bridge. |
| 1 | Select it, pin `instanceId` for the MCP server lifetime. |
| >1 | Fail closed: list short IDs, Blender versions, PIDs, blend-file basenames. Require explicit `--blender-instance` / `BLENDER_MCP_INSTANCE`. |

### 4.3 Session affinity

- After selection, reconnect only to the same `instanceId`.
- If the selected instance exits, do **not** silently switch; require
  explicit reselection or MCP server restart.
- The MCP server initializes lazily: startup works before Blender runs.

## 5. No-replay request semantics

Request states:

```
UNRESOLVED → RESOLVED → CONNECTED → SENDING → SENT → RECEIVING → COMPLETE
```

- Retry allowed only for failures before the `SENDING` state begins
  (discovery probes, connect failures).
- Once `sendall()` starts, the outcome may be unknown (partial payload may
  have reached Blender). Never replay after: partial-send exception,
  response timeout, EOF, reset, malformed response.
- Post-send failures return:
  `Execution outcome is unknown. The request was not retried.`

## 6. Compatibility matrix

| MCP Server | Extension | Mode |
|---|---|---|
| Connect | Connect | Automatic discovery + authenticated bridge |
| Connect | Official | Explicit `BLENDER_MCP_HOST`/`BLENDER_MCP_PORT`, legacy protocol |
| Official | Connect | Fixed-port legacy mode only (not tested, best-effort) |
| Official | Official | Official behavior unchanged |

Running official and Connect extensions simultaneously is unsupported.

## 7. Versioning

- `schemaVersion` bumps on descriptor format changes.
- `protocolVersion` bumps on wire-protocol changes.
- Extension and PyPI server may version independently; mismatch is detected
  at `hello` time with a clear message.
