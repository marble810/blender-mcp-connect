# SECURITY

## Security Warning

The Blender MCP server executes **LLM-generated Python code directly inside
Blender** without a sandbox that protects user data. A malicious or confused
model (or a malicious MCP client) can delete files, send data to remote
locations, or otherwise damage your system.

To keep your data safe, follow the official upstream guidance:

- Use a virtual machine, or
- Use a system without access to sensitive information.

Loopback binding and per-instance tokens are **local capability
authentication**, not a security sandbox. A malicious process running as the
same operating-system user may still access descriptors or Blender data.

## Local Connection Model

- The bridge binds to `127.0.0.1` (loopback) only by default.
- The Blender Extension writes a per-instance descriptor containing a random
  token into a private per-user runtime directory.
- The external MCP server authenticates with that token before any code is
  executed.
- Automatic discovery never enables remote/LAN access. Explicit non-loopback
  legacy configuration prints a clear warning.

## Reporting a Vulnerability

This is a community downstream project. Report issues at:

- GitHub Issues: <https://github.com/marble810/blender-mcp-connect/issues>

Do **not** report downstream-specific vulnerabilities to the Blender
Foundation; for issues affecting the official upstream project itself, report
them at <https://projects.blender.org/lab/blender_mcp/issues> instead.
