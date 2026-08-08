# LLM Agent Guide — Setting Up Blender MCP Connect

This guide is for **AI coding agents** helping a user install and configure
[Blender MCP Connect](https://github.com/marble810/blender-mcp-connect).

Follow it step by step. **Ask the user before doing anything surprising** —
installing software, modifying their MCP client configuration, or launching
Blender are user-owned actions. Do not run the full flow unattended.

The flow is:

```text
Interview user → Download Extension ZIP → Install in Blender → Deploy mcp.json → Verify
```

## Requirements (verify early)

| Requirement | Check |
|---|---|
| Blender **5.1 or newer** | `blender --version` or ask the user |
| `uv` installed | `uv --version` (needed for `uvx`) |
| MCP-capable client | Claude Desktop / Claude Code / Cursor / other |

Blender MCP Connect is an **unofficial downstream** of Blender Lab MCP. If
the user already has the official Blender Lab MCP add-on installed, tell them
both must not be enabled at the same time.

---

## Step 0 — Interview the user

Ask interactively (do not assume):

1. **Which Blender do they want to drive?**
   - Which version? (must be ≥ 5.1)
   - Where is the Blender executable?
   - Managed by a launcher? (e.g. Blender Launcher keeps builds under its
     library folder — search for `blender.exe`, don't guess)
2. **Which MCP client?** This decides where `mcp.json` goes (Step 3).
3. **Interactive or headless?** Interactive uses the add-on's preferences
   panel; headless uses `blender --background --command blender_mcp`.

If the user has multiple Blender versions, ask which one is the target — the
extension installs into that specific Blender instance's user configuration.

---

## Step 1 — Download the Extension ZIP

Latest release:

```text
https://github.com/marble810/blender-mcp-connect/releases/download/connect-v0.1.0/blender_mcp_connect_0.1.0.zip
```

Use the [GitHub Releases](https://github.com/marble810/blender-mcp-connect/releases)
page for newer versions and the matching `SHA256SUMS.txt`.

```bash
# Linux/macOS
curl -fL -o blender_mcp_connect.zip \
  https://github.com/marble810/blender-mcp-connect/releases/download/connect-v0.1.0/blender_mcp_connect_0.1.0.zip

# Windows PowerShell
Invoke-WebRequest -OutFile blender_mcp_connect.zip `
  https://github.com/marble810/blender-mcp-connect/releases/download/connect-v0.1.0/blender_mcp_connect_0.1.0.zip
```

Verify the SHA-256 against `SHA256SUMS.txt` from the release. If the user
prefers, let them download it manually.

---

## Step 2 — Install the Extension in Blender

**GUI (recommended for users):**

1. Open the target Blender 5.1+.
2. **Edit → Preferences → Get Extensions → Install from Disk…**
3. Select the downloaded ZIP.
4. Enable the **MCP Connect** add-on.

**CLI (scriptable):**

```bash
blender --background --factory-startup --online-mode \
  --command extension install-file <path-to-zip> --repo user_default --enable
```

Verify installation:

```bash
blender --background --command extension list | grep blender_mcp_connect
```

Then start the bridge server:
- Interactive: enable the add-on (auto-start is on by default) or press
  **Start MCP Bridge Server** in the preferences.
- Headless: `blender --background <file.blend> --command blender_mcp`
  (defaults to an OS-assigned port; pass `--port 0` explicitly if needed).

The add-on writes a per-instance descriptor (Windows:
`%LOCALAPPDATA%\BlenderMCPConnect\instances\`) that enables automatic
discovery — **no port configuration is needed**.

---

## Step 3 — Deploy `mcp.json`

Universal entry (no server path, no bridge port, no `BLENDER_PATH`):

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

Client-specific locations:

| Client | File |
|---|---|
| Claude Desktop | `claude_desktop_config.json` (macOS: `~/Library/Application Support/Claude/`, Windows: `%APPDATA%\Claude\`) |
| Claude Code | `.mcp.json` (project) or `~/.claude.json` (user); or `claude mcp add blender -- uvx --from blender-mcp-connect==0.1.0 blender-mcp-connect` |
| Cursor | `.cursor/mcp.json` (project) or user MCP settings |

First run downloads the server via `uvx` (requires network). Pin the exact
version (`==0.1.0`) in the config; do not use an unpinned `uvx` invocation.

---

## Step 4 — Verify

1. Blender is running with the add-on enabled and the bridge started.
2. From a terminal (outside the MCP session):

```bash
blender-mcp-connect --list-instances
```

   Should show one instance with `ok` status.

3. In the MCP client, ask a simple question, e.g. *"List the objects in the
   current Blender scene."* — the agent should call `get_objects_summary`.

---

## Troubleshooting

| Symptom | Cause / Fix |
|---|---|
| `No Blender MCP Connect instance was found` | Extension not installed/enabled or bridge not started. Start it, then retry. |
| `Multiple healthy Blender instances were found` | Several Blender processes are running. Set `BLENDER_MCP_INSTANCE=<full instance id>` (see `--list-instances`) or close the extra instance. The server never guesses. |
| `The selected Blender instance is no longer reachable` | Blender was closed. Restart the MCP server (or re-select the instance). The server never silently switches projects. |
| `Execution outcome is unknown. The request was not retried.` | The connection failed after the request may have been sent. Ask the user to check Blender; do **not** blindly retry destructive operations. |
| Extension shows `stale` in `--list-instances` | A crashed Blender left a descriptor behind. Harmless; it is ignored and can be deleted from the runtime directory. |
| Port binding errors on Windows (legacy fixed-port mode) | Windows Hyper-V excluded ranges (e.g. 9784–9883) can block ports like 9876. Automatic mode (port 0) avoids this entirely. |
| `Protocol version mismatch` | Server and extension versions disagree. Upgrade both. |

Security note: the bridge executes LLM-generated code inside Blender. Loopback
binding + tokens are local capability checks, **not** a sandbox. Keep the
official warning: use a VM or a system without sensitive data if needed.

---

## Non-goals

- Do **not** configure the official Blender Lab MCP add-on or server in the
  same session.
- Do **not** change `blender_manifest.toml`, tool schemas, or bridge protocol
  details while helping — this guide is for setup only.
- Do **not** host or re-upload the extension ZIP elsewhere; link to the
  official release.
