<div align="center">
  <h1>Blender MCP Connect</h1>
  <p><strong>基于官方 Blender MCP 的安装连接优化版：免装 MCP Server、免配端口，自动、安全连接 Blender。</strong></p>
  <p><em>An install-and-connect optimized fork of the official Blender MCP tool—no MCP Server install or port setup, with automatic, authenticated Blender connection.</em></p>
</div>

> **Unofficial community downstream** of [Blender Lab MCP](https://projects.blender.org/lab/blender_mcp).
> Not affiliated with or endorsed by the Blender Foundation.
> Upstream baseline: `4309a39646e644261624bfcd2bca669b343b7621`.

## Let AI Install It for You

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

----

# 中文版说明

> 中文版仅供参考，以英文原版为准。
> 本文档使用 wikilink 导航：`[[#小节标题|显示名]]` 跳转到本文档内的小节，`[[文件名]]` 跳转到仓库内的其他文件。

## 目录

- [[#让AI帮你装|让AI帮你装]]
- [[#概述|概述]]
- [[#安装|安装]]
- [[#Blender 插件|Blender 插件]]
- [[#MCP 服务器|MCP 服务器]]

## 让AI帮你装

如果你是帮助用户配置 Blender MCP Connect 的 AI 编程智能体（如 Claude Code、Cursor、Codex），请先阅读 **[[llm.md]]**。它会引导你走完完整交互流程：访谈用户确认目标 Blender → 下载扩展 → 安装 → 部署 `mcp.json` → 验证连接。

## 概述

Blender 的轻量级 MCP（Model Context Protocol）服务器。它以自然语言接口对接 Blender 的 Python API，改善对文档的访问，帮助用户探索和理解复杂场景。

上游文档见 [blender.org/lab/mcp-server](https://www.blender.org/lab/mcp-server/)

----

项目刻意保持小巧、可维护，不做多余的事。它由两个通过 TCP socket 通信的组件构成：

- **Blender 插件**：运行在 Blender 内部，执行请求。
- **MCP 服务器**：独立进程，由 MCP 客户端启动（例如 [Llama.cpp](https://projects.blender.org/lab/blender_mcp/wiki/Llama.cpp)）。

数据流：

```
MCP 客户端  ⇐ MCP/stdio ⇒  blender-mcp-connect  ⇐ TCP socket ⇒  Blender 插件
```

## 安装

### 1. 安装 Blender 扩展

需要 Blender 5.1 或更高版本。

1. 从 [GitHub Releases](https://github.com/marble810/blender-mcp-connect/releases) 页面下载 [**blender_mcp_connect_0.1.0.zip**](https://github.com/marble810/blender-mcp-connect/releases/download/connect-v0.1.0/blender_mcp_connect_0.1.0.zip)。
2. 在 Blender 中执行 **编辑 → 偏好设置 → 获取扩展 → 从磁盘安装…**，选择下载的 ZIP。
3. 启用 **MCP Connect** 插件。

> 官方 Blender Lab MCP 插件与 MCP Connect 不能同时启用。

### 2. 配置你的 MCP 客户端

将以下条目加入你的 MCP 客户端配置（例如 `mcp.json`、`claude_desktop_config.json`）：

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

无需克隆仓库、无需服务器路径、无需配置桥接端口、也无需 `BLENDER_PATH`：扩展会发布每个实例的描述符，MCP 服务器会自动发现它。

## Blender 插件

位于 ``addon/blender_mcp_addon/``。

一个 Blender 扩展，让 MCP 服务器能与运行中的 Blender 实例通信。必须安装并启用它，任何 MCP 工具才能工作。

插件提供偏好设置面板，可配置主机、端口和可选的自动启动设置。

### 功能概览

注意：这有意保持为一个极简插件。

连接性
- 自动启动（可选），非阻塞，任何问题都可在偏好设置中查看。
- 可配置轮询间隔（活跃与空闲速率），避免不必要的开销。
- 客户端超时保护——停滞的连接会被剔除。
- 偏好设置面板中提供启动/停止操作符。
- 延迟响应仅由交互式插件服务器支持；后台模式要求请求同步完成，并拒绝延迟结果。

## MCP 服务器

位于 ``mcp/blmcp/``，以 Python 包形式安装，入口点为 ``blender-mcp``。

MCP 客户端启动该进程并通过 stdio 与之通信。服务器连接插件的 TCP socket，将请求转发到 Blender。

``mcp/blmcp/data/``
   随包分发的数据文件。

   - ``prompts.yml`` 提供连接时发送给 LLM 的指令。
   - ``api/`` 包含 RST 格式的 Blender Python API 参考。
   - ``manual/`` 包含 RST 格式的 Blender 用户手册摘录。

``mcp/blmcp/tools/``
   每个工具是单一模块，启动时自动发现。以 ``_toolcode`` 结尾的模块包含在 Blender 内部运行的代码（发送给插件执行），发现阶段会跳过。

``mcp/blmcp/tools_helpers/``
   工具共用的工具函数。工具之间不应互相导入；共享逻辑放在这里。

### 工具

参见 [[readme_tools.rst]]（MCP 服务器暴露的工具列表）。
