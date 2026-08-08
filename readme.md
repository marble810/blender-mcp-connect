# Blender MCP Connect

> **Unofficial community downstream** of [Blender Lab MCP](https://projects.blender.org/lab/blender_mcp).
> Not affiliated with or endorsed by the Blender Foundation.
> Upstream baseline: `4309a39646e644261624bfcd2bca669b343b7621`.

## For AI Agents

If you are an AI coding agent (e.g. Claude Code, Cursor, Codex) helping a
user set up Blender MCP Connect, read **[`llm.md`](llm.md)** first. It walks
you through the interactive flow: interviewing the user about their target
Blender → downloading the Extension → installing it → deploying `mcp.json`
→ verifying the connection.

## Overview

A lightweight MCP (Model Context Protocol) server for Blender.
It offers a natural language interface with Blender's Python API,
improving access to documentation, and allowing users to explore
and understand complex setups.

Read the upstream documentation at [blender.org/lab/mcp-server](https://www.blender.org/lab/mcp-server/)

----

The project is deliberately small, maintainable, and does no more than
necessary. It has two components that communicate over a TCP socket:

- A **Blender add-on** that runs inside Blender and executes requests.
- An **MCP server** that runs as a separate process, launched by the
  MCP client (e.g. [Llama.cpp](https://projects.blender.org/lab/blender_mcp/wiki/Llama.cpp)).

The data flow is:
```
MCP Client  ⇐ MCP/stdio ⇒  blender-mcp-connect  ⇐ TCP socket ⇒  Blender Add-on
```


## Installation

### 1. Install the Blender Extension

Blender 5.1 or newer is required.

1. Download [**blender_mcp_connect_0.1.0.zip**](https://github.com/marble810/blender-mcp-connect/releases/download/connect-v0.1.0/blender_mcp_connect_0.1.0.zip)
   from the [GitHub Releases](https://github.com/marble810/blender-mcp-connect/releases) page.
2. In Blender use **Edit → Preferences → Get Extensions → Install from Disk…**
   and select the downloaded ZIP.
3. Enable the **MCP Connect** add-on.

> The official Blender Lab MCP add-on and MCP Connect must not be enabled
> at the same time.

### 2. Configure your MCP client

Add the following entry to your MCP client configuration
(e.g. `mcp.json`, `claude_desktop_config.json`):

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

No repository clone, no server path, no bridge-port configuration and no
`BLENDER_PATH` are required: the extension publishes a per-instance
descriptor and the MCP server discovers it automatically.

## Blender Add-on

Located in ``addon/blender_mcp_addon/``.

A Blender extension that allows the MCP server to communicate with a
running Blender instance. It must be installed and enabled for any of
the MCP tools to work.

The add-on provides a preferences panel for configuring the host, port,
and an optional auto-start setting.

### Functionality Overview

Note that this is intended to be a fairly minimal add-on.

Connectivity
   - Auto-start (optional), is non-blocking any issues can be viewed from the preferences.
   - Configurable polling intervals (active and idle rates) from preferences to avoid excessive overhead.
   - Client timeout protection - stalled connections are evicted.
   - Start/stop operators accessible from the preferences panel.
   - Deferred responses are supported only by the interactive add-on server;
     background mode requires requests to complete synchronously and rejects deferred results.




## MCP Server

Located in ``mcp/blmcp/``, installed as a Python package with the
entry point ``blender-mcp``.

An MCP client launches this process and communicates with it over
stdio. The server connects to the add-on's TCP socket to relay
requests to Blender.

``mcp/blmcp/data/``
   Data files bundled with the package.

   - ``prompts.yml`` provides instructions sent to the LLM at
     connection time.
   - ``api/`` contains Blender Python API reference in RST format.
   - ``manual/`` contains Blender user manual excerpts in RST format.

``mcp/blmcp/tools/``
   Each tool is a single module, auto-discovered at startup.
   Modules ending in ``_toolcode`` contain code that runs inside
   Blender (sent to the addon for execution) and are skipped during
   discovery.

``mcp/blmcp/tools_helpers/``
   Shared utilities used by tools. Tools should not import from each
   other; shared logic lives here instead.


### Tools

See [readme_tools.rst](readme_tools.rst) for the tools the MCP server exposes.
