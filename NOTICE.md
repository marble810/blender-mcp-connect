# NOTICE

## Project

**Blender MCP Connect** is an **unofficial community downstream** of the
[Blender Lab MCP](https://projects.blender.org/lab/blender_mcp) project.

It is **not affiliated with, endorsed by, or sponsored by** the Blender
Foundation or the Blender Lab.

## Upstream

- Upstream repository: <https://projects.blender.org/lab/blender_mcp>
- Upstream documentation: <https://www.blender.org/lab/mcp-server/>
- Initial downstream baseline commit: `4309a39646e644261624bfcd2bca669b343b7621`

## License

This project is licensed under the **GPL-3.0-or-later** license, matching the
upstream Blender Lab MCP project. See `LICENSE` for the full license text.

All source files retain their original upstream SPDX headers:

```text
SPDX-FileCopyrightText: 2026 Blender Authors
SPDX-License-Identifier: GPL-3.0-or-later
```

Bundled documentation (Blender Python API reference and Blender user manual
excerpts under `mcp/blmcp/data/`) retains its original copyright and license
notices and is distributed unmodified for reference purposes.

## Security Warning

The MCP server executes LLM-generated code inside Blender without guards that
protect user data from removal or transmission to a remote location. To keep
your data safe it is recommended to use a virtual machine, or a system without
access to sensitive information.
