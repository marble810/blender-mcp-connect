# Blender MCPB Extension

## Description
A lightweight MCP (Model Context Protocol) server for Blender.

Allows LLM assistants to interact with a running Blender instance – inspecting scenes, executing Python code, rendering, and navigating the interface.

## Features
It supports running arbitrary Python code within Blender. This allows for advanced scene analysis and debugging. It also contains the complete API and user manual as resources, helping the LLM to access the latest version of both documentations.

## Installation

The MCP Server is published to PyPI as `blender-mcp-connect` and is
installed via `uvx` (or `pip install blender-mcp-connect`).

It requires an add-on in Blender for this to work:

### Add-on

* Download [**blender_mcp_connect_0.1.0.zip**](https://github.com/marble810/blender-mcp-connect/releases/download/connect-v0.1.0/blender_mcp_connect_0.1.0.zip)
  from the [GitHub Releases](https://github.com/marble810/blender-mcp-connect/releases)
  page.
* In Blender 5.1+ use **Edit → Preferences → Get Extensions → Install from Disk…**
  and select the downloaded ZIP.
* Enable the **MCP Connect** add-on.

> **Note:** this is an unofficial community downstream of Blender Lab MCP.
> Do not install both the official Blender Lab MCP add-on and MCP Connect at
> the same time; they would both try to serve the same bridge role.

### MCP client configuration

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

## Examples

You can find more examples in the [documentation](https://www.blender.org/lab/mcp-server/).

### Example 1: Data-block renaming: fix types

**Demo file**: [Pebble Scattering](https://www.blender.org/download/demo/geometry-nodes/fields/pebble_scattering.blend)

**User prompt**: "With the current open Blender file fix the name of all the data-blocks to remove typos. Report back which data-blocks got fixed."

**Expected behaviour:**
- `GRP-rocks` → `GRP-pebble` [optionally, this is more opiniated]
- `LGT-Lights` → `LGT-lights`
- `Compositing Nodetree` → `Compositing Node Tree`

### Example 2: Querying data relations using natural language

**Demo file**: [Pebble Scattering](https://www.blender.org/download/demo/geometry-nodes/fields/pebble_scattering.blend)

**User prompt**: "Which objects are using the following material: pebbles"

**Expected behaviour:**
7 objects:
- `GEO-pebble`
- `GEO-pebble.001`
- `GEO-pebble.002`
- `GEO-pebble.003`
- `GEO-pebble.004`
- `GEO-pebble.005`
- `GEO-pebble.006`

### Example 3: Querying data relations using natural language

**Demo file**: [Classroom](https://download.blender.org/demo/test/classroom.zip)

**User prompt**: "Analyze the scene and list the outliers: objects with highest polygon count but smaller size from the camera point of view."

**Expected behavior:**
An analysis that consider the final amount of polygons after the object modifiers are applied. This usually happens by getting the object from the dependency graph.

The biggest outliers are: `coat 1` and `alphabet`.

Depending on whether or not the RENDER context was used (as oppose to the VIEWPORT context), the biggest outlier (`coat 1`) may show 37k or 74k polygons. This is the only object that has a modifier which is only used for rendering. Every other object should report the same poly-count regardless of the context.

## Privacy Policy
See our privacy policy: https://www.blender.org/privacy-policy/

## Support
For issues: https://projects.blender.org/lab/blender_mcp/issues
