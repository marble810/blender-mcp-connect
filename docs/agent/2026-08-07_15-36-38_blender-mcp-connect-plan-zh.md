# Blender MCP Connect — 实施计划（中文版）

> 状态：设计已批准；尚未开始实施
> 下游仓库：<https://github.com/marble810/blender-mcp-connect>
> 权威上游：<https://projects.blender.org/lab/blender_mcp>
> 初始上游基线：`4309a39646e644261624bfcd2bca669b343b7621`
> 首个发布目标：`blender-mcp-connect 0.1.0` / 标签 `connect-v0.1.0`

## 1. 目标

构建 **Blender MCP Connect** —— Blender Lab MCP 的一个明确标注为“非官方”的下游发行版，需要做到：

- 保留官方的双进程架构和公开的 MCP 工具面；
- 将外部 stdio MCP Server 发布到 PyPI；
- 通过稳定的 `uvx` 命令从任意目录运行；
- 让 Blender Extension 绑定操作系统分配的 loopback 端口；
- 无需配置 bridge 端口即可发现正确的本地 Blender 实例；
- 消除日常对克隆服务器目录、手工 `pip`、`BLENDER_PATH` 或 bridge 端口配置的依赖；
- 当存在多个 Blender 实例时，宁可失败关闭（fail closed），也不猜测；
- 一旦请求可能已经开始传输，绝不盲目重放 Blender 操作。

目标用户配置：

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

诸如 `directTools` 之类的客户端专属选项，有意从通用示例中排除。

## 2. 权威参考资料

本计划基于官方项目材料：

- 产品页面与安全警告：<https://www.blender.org/lab/mcp-server/>
- 源码仓库：<https://projects.blender.org/lab/blender_mcp>
- 通用 stdio 配置：<https://projects.blender.org/lab/blender_mcp/wiki/Setup>
- Llama.cpp / Streamable HTTP 配置：<https://projects.blender.org/lab/blender_mcp/wiki/Llama.cpp>
- 官方发布页：<https://projects.blender.org/lab/blender_mcp/releases>
- MCP SDK 2 不兼容问题：<https://projects.blender.org/lab/blender_mcp/issues/44>
- 待合并的 MCP SDK 2 迁移：<https://projects.blender.org/lab/blender_mcp/pulls/43>
- Windows 继承 stdin 问题：<https://projects.blender.org/lab/blender_mcp/issues/42>
- Blender 标志/商标指引：<https://www.blender.org/about/logo/>

已核实的官方基线：

```text
MCP Client ⇄ MCP/stdio ⇄ 外部 blender-mcp 进程 ⇄ TCP socket ⇄ Blender Extension
```

官方产品页面要求 Blender 5.1 或更新版本，并警告：LLM 生成的代码会在 Blender 内部执行，且没有任何保护用户数据的防护措施。Blender MCP Connect 必须保留这一警告，且不得把 loopback 认证描述成沙箱。

官方源码与 manifest 声明为 `GPL-3.0-or-later`。下游源码与发布产物必须保持 GPL 合规，并保留上游署名及随附文档的许可声明。

## 3. 产品与兼容性决策

### 3.1 身份

| 项目 | 决策 |
|---|---|
| 产品名 | Blender MCP Connect |
| PyPI 发行名 | `blender-mcp-connect` |
| 控制台命令 | `blender-mcp-connect` |
| Python 导入包 | 保留 `blmcp` |
| MCP 对外服务名 | 初期保留 `blender-mcp` |
| Blender Extension ID | `blender_mcp_connect` |
| Blender Extension 名称 | `MCP Connect` |
| 维护者 | `marble810` |
| 首个下游版本 | `0.1.0` |
| 首个下游标签 | `connect-v0.1.0` |
| 许可证 | `GPL-3.0-or-later` |
| 最低 Blender 版本 | 保留上游下限：Blender 5.1 |

保留 `blmcp` 包名和 MCP 对外服务名，可以最大程度减少分歧，避免不必要的可见协议变化。发行名、CLI、Extension 身份、维护者、支持链接和发布产物必须使用下游品牌。

### 3.2 架构

保留：

```text
MCP Client
    ⇅ stdio（默认）或可选 Streamable HTTP
安装在 PyPI 的外部 MCP Server
    ⇅ 带认证的本地 TCP bridge
Blender MCP Connect Extension
```

不要把 FastMCP 或完整 MCP Server 嵌入 Blender。不要把 PyPI Server wheel 打进 Extension。

### 3.3 多实例

- 0 个健康实例：给出可操作的错误提示。
- 恰好 1 个健康实例：自动选择，并在 stdio Server 生命周期内固定（pin）它。
- 多于 1 个健康实例：失败关闭，要求显式选择。
- 绝不在已固定会话后静默切换到另一个 Blender 进程。

### 3.4 兼容模式

预期兼容矩阵：

| MCP Server | Blender Extension | 模式 |
|---|---|---|
| Connect | Connect | 自动发现 + 认证 bridge |
| Connect | 官方 | 显式 `BLENDER_MCP_HOST` / `BLENDER_MCP_PORT`，传统协议 |
| 官方 | Connect | 仅固定端口传统模式 |
| 官方 | 官方 | 维持官方既有行为 |

首个版本不支持官方 Extension 与 Connect Extension 同时运行，且必须在文档中写明。

## 4. 跨 Forge 下游策略

GitHub 无法把托管在另一个 forge 上的仓库标记为 GitHub fork，因此 `marble810/blender-mcp-connect` 正确显示 `isFork: false`，即使它保留了官方 Git 祖先历史。

使用这些 remote：

```text
origin    https://github.com/marble810/blender-mcp-connect.git
upstream  https://projects.blender.org/lab/blender_mcp.git
```

使用这些分支：

```text
upstream-main  Blender Lab main 的精确镜像
main           经过评审的下游产品分支
feature/*      下游工作分支
```

规则：

1. 绝不把上游变更自动合并进 `main`。
2. 定时/手动工作流可以更新 `upstream-main` 或报告上游漂移。
3. 在发布之后，用 merge commit 把评审过的上游变更合入 `main`；不要改写已发布的下游历史。
4. 不要把 Blender Lab 的发布标签当作下游发布标签重新发布。
5. 使用 `connect-v0.1.0` 之类的下游标签，因为上游已经拥有 `v0.1.0`、`v0.3.0`、`v1.0.0` 等标签。
6. 每次下游发布都要记录确切的 upstream SHA。
7. 只有在向上游提交聚焦的通用修复时，才在 `projects.blender.org` 创建真正的 fork。
8. 只把通用修复 cherry-pick 进上游 PR；不要把下游品牌、PyPI 工作流或产品专属 registry 路径混入无关修复。

建议的手动同步流程：

```bash
git fetch upstream

git switch upstream-main
git reset --hard upstream/main
git push --force-with-lease origin upstream-main

git switch main
git merge --no-ff upstream-main
```

## 5. Bridge 与发现契约

契约必须在实施前写入：

```text
docs/bridge-protocol.md
docs/instance-descriptor.schema.json
```

### 5.1 Descriptor

初始 descriptor 形状：

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

运行时目录：

| 平台 | 目录 |
|---|---|
| Windows | `%LOCALAPPDATA%\BlenderMCPConnect\instances\` |
| macOS | `~/Library/Caches/BlenderMCPConnect/instances/` |
| Linux | `$XDG_RUNTIME_DIR/blender-mcp-connect/instances/` |
| Linux 回退 | `$XDG_CACHE_HOME/blender-mcp-connect/instances/` 或 `~/.cache/blender-mcp-connect/instances/` |

`BLENDER_MCP_RUNTIME_DIR` 可以覆盖根目录，用于测试和高级部署。

Descriptor 要求：

- 先写入临时文件，再用 `os.replace` 发布；
- 在支持权限的平台使用私有目录/文件权限（POSIX 上为 `0700`/`0600`）；
- 只接受普通文件，忽略符号链接；
- 限制最大文件尺寸，初始为 64 KiB；
- 在访问网络前校验必填字段和类型；
- 绝不记录或展示 token；
- PID 和时间戳只作为提示；
- 用 `hello` 交换认证端点身份；
- 安全地忽略损坏、超大、过期、不兼容或身份不匹配的条目。

### 5.2 Bridge 请求

扩展现有 NUL 分隔 JSON 协议，新增：

- `hello`：认证的健康检查、身份识别与协议协商；
- `execute`：既有执行请求，另加 `protocolVersion`、`instanceId` 和 token。

自动发现的端点绝不允许降级为无认证执行。显式配置的传统端点可以为了兼容性沿用官方传统请求格式。

在任何用户可控代码到达执行前，使用恒定时间（constant-time）的 token 比较。

### 5.3 解析优先级

1. `--instance <完整实例ID>`
2. `BLENDER_MCP_INSTANCE`
3. 显式 `BLENDER_MCP_HOST` / `BLENDER_MCP_PORT`
4. 自动扫描 descriptors

`--host` 和 `--port` 已经用于配置可选的 MCP HTTP 监听器，不得复用于 Blender bridge。任何新增的 bridge 参数必须使用无歧义的名称，如 `--blender-instance`、`--blender-host`、`--blender-port`，或者仅通过环境变量提供。

## 6. 禁止重放的请求语义

围绕显式状态重构 bridge 调用：

```text
UNRESOLVED → RESOLVED → CONNECTED → SENDING → SENT → RECEIVING → COMPLETE
```

安全重试仅限于发现探测和确认发生在请求传输开始之前的失败。

一旦 `sendall()` 开始，结果可能未知，因为部分载荷可能已经到达 Blender。以下情况不得重放：

- 部分发送异常；
- 响应超时；
- 等待响应时 EOF；
- 发送后连接重置；
- 发送后收到损坏的响应。

返回明确的诊断信息：

```text
Execution outcome is unknown. The request was not retried.
```

（执行结果未知，请求未重试。）

不要根据工具名称或 MCP `readOnlyHint` 元数据推断重放安全性。exactly-once 执行、请求去重和响应恢复不在 `0.1.0` 范围内。

## 7. 实施阶段

## Phase 0 — 下游基础与可复现基线

任务：

- [ ] 在记录的上游 SHA 上创建并推送 `upstream-main`。
- [ ] 添加 `LICENSE`，包含完整 GPL-3.0-or-later 文本。
- [ ] 添加 `NOTICE.md`、`SECURITY.md`、`UPSTREAM.md` 和 `CHANGELOG.md`。
- [ ] 明确标注：这是非官方下游，与 Blender Foundation 无关联、未获其背书。
- [ ] 保留上游 SPDX 头与随附文档许可声明。
- [ ] 修改下游发行名、CLI、Extension ID/名称/维护者、支持链接和版本。
- [ ] 避免官方 Blender Lab 发布品牌；发布前替换基于官方标志的下游发布素材。
- [ ] 保留官方工具名、schema、`blmcp` 导入包和 MCP 服务名。
- [ ] 补全 PyPI 元数据：readme、license、维护者、项目 URL、classifiers 和 package data。
- [ ] 为 `0.1.0` 固定 `mcp[cli]>=1.2,<2`，避开当前上游的 MCP SDK 2 破坏。
- [ ] 保持 `mcp/pyproject.toml` 与依赖文件同步。
- [ ] 发布前应用或并入 Windows 的 `stdin=subprocess.DEVNULL` 修复。
- [ ] 运行未修改连接架构的测试，建立已知良好的基线。

验收标准：

- 干净的 Python 环境可以安装服务器，且不会解析到 MCP SDK 2。
- stdio Server 能初始化并列出官方工具面。
- 在发现功能开始前，现有非 Blender 测试全部通过。
- 没有任何 manifest 声称下游维护者或支持方是 Blender Lab。
- 发布元数据同时链接下游源码/支持与权威上游。

## Phase 1 — 协议与 descriptor 规范

任务：

- [ ] 编写 `docs/bridge-protocol.md`。
- [ ] 编写 `docs/instance-descriptor.schema.json`。
- [ ] 明确路径解析、原子写入、权限、上限和过期条目处理。
- [ ] 明确 `hello`、认证 `execute`、版本不匹配与传统行为。
- [ ] 明确零/一/多实例选择与会话亲和。
- [ ] 明确禁止重放的状态转换与诊断信息。
- [ ] 添加从文档 schema 派生的单元测试 fixtures。

验收标准：

- 双方 bridge 实现可以仅依据文档构建，无需猜测字段名或优先级。
- Schema fixtures 校验通过。
- 认证失败保证发生在代码执行之前。
- 每种 Server/Extension 配对下的兼容行为都有明确说明。

## Phase 2 — 动态 Blender Extension

主要文件：

```text
addon/blender_mcp_addon/mcp_to_blender_server.py
addon/blender_mcp_addon/__init__.py
addon/blender_mcp_addon/cli.py
addon/blender_mcp_addon/blender_manifest.toml
addon/blender_mcp_addon/instance_registry.py        # 新增
```

任务：

- [ ] 让 Connect Extension 默认使用 `127.0.0.1` 和自动端口 `0`。
- [ ] 保留固定端口传统模式作为高级选项。
- [ ] 用 `getsockname()` 获取并暴露实际端点。
- [ ] 生成进程生命周期的实例 ID，并在 bridge 启动时轮换 token。
- [ ] 仅在 `bind()` 和 `listen()` 成功后才发布 descriptor。
- [ ] 若 descriptor 发布失败，回滚并关闭 socket。
- [ ] 在停止、卸载、正常退出或启动回滚时，只删除属于本实例的 descriptor。
- [ ] 交互模式与后台 Blender 模式的注册行为保持一致。
- [ ] 实现带认证的 `hello` 和 `execute` 处理。
- [ ] 显示实际端口和短实例 ID，绝不显示 token。
- [ ] 在加载/保存事件后刷新 blend 文件元数据，或由 `hello` 返回当前元数据。

验收标准：

- 两个 Blender 进程无需手工配置即可获得不同的可用端口。
- 占用端口 `9876` 不影响自动启动。
- 自动模式只在 `127.0.0.1` 上监听。
- 缺失或错误的 token 无法执行代码。
- 启动、停止、重启、禁用和正常退出时的 descriptor 生命周期正确。

## Phase 3 — Server 发现与会话亲和

主要文件：

```text
mcp/blmcp/tools_helpers/connection.py
mcp/blmcp/tools_helpers/instance_discovery.py       # 新增
mcp/blmcp/__init__.py
```

任务：

- [ ] 仅用标准库实现平台运行时目录解析。
- [ ] 防御式扫描和校验 descriptors。
- [ ] 使用认证 `hello` 探测候选。
- [ ] 实现文档规定的配置优先级。
- [ ] 自动选择恰好一个健康实例。
- [ ] 多个健康实例时失败关闭，并给出有用的实例列表。
- [ ] 支持按完整实例 ID 精确显式选择。
- [ ] 在 stdio Server 生命周期内固定所选实例身份。
- [ ] 仅对同一个固定实例 ID 重新解析变化后的端点。
- [ ] 断线后绝不切换到另一个实例。
- [ ] 增加诊断命令 `--list-instances`，只写入普通终端输出，绝不在服务器运行期间写入 MCP stdio。
- [ ] 保留显式 host/port 与官方 Extension 的兼容。

验收标准：

- 无需 host/port 环境变量即可找到单个 Connect Extension。
- 多个实例绝不会导致任意附加。
- 显式选择只到达请求的实例。
- 过期、损坏、超大、符号链接、不兼容和被伪造的 descriptors 都能安全忽略。
- MCP Server 可以在 Blender 启动前初始化；发现保持惰性（lazy）。

## Phase 4 — 传输可靠性与可执行文件发现

主要文件：

```text
mcp/blmcp/tools_helpers/connection.py
mcp/blmcp/tools_helpers/request_state.py             # 新增，如有必要
mcp/blmcp/tools_helpers/blender_cli.py
```

任务：

- [ ] 区分发现、连接、发送、接收和解析的失败处理。
- [ ] 仅在请求传输可能开始之前允许重试。
- [ ] 对发送后的失败给出明确的“结果未知”错误。
- [ ] 为每个请求状态添加 mock-socket 测试。
- [ ] 对照可能运行更久的 deferred 操作，复核当前 300 秒 socket 超时。
- [ ] 保留显式 `BLENDER_PATH` 为最高优先级。
- [ ] 否则使用已认证所选实例的 `blenderExecutable` 元数据。
- [ ] 仅在所选元数据不可用时，才回退到 `PATH` 中的 `blender`。
- [ ] 对由 stdio MCP Server 启动的 Blender 子进程使用 `stdin=subprocess.DEVNULL`。

验收标准：

- 发送前的连接失败可以重试。
- 部分发送、接收超时、EOF、重置和无效响应路径最多执行一次。
- 在选中健康 Connect 实例时，交互使用和 `_for_cli` 工具不常需要 `BLENDER_PATH`。
- Windows 上的 Blender 子进程不会继承活跃的 MCP stdio 管道。

## Phase 5 — 测试与打包

新增或扩展测试：

- [ ] Windows、macOS、Linux 的运行时目录映射。
- [ ] 原子 descriptor 写入与清理回滚。
- [ ] 支持权限平台的 descriptor 权限。
- [ ] 损坏 JSON、超大文件、符号链接、过期条目和协议不匹配。
- [ ] 执行前的认证。
- [ ] 零、一、多实例选择。
- [ ] 另一个 Blender 启动时的会话亲和。
- [ ] 每个请求状态的重试边界。
- [ ] 固定端口官方兼容。
- [ ] 无环境变量的动态真实 Blender 操作。
- [ ] 端口 `9876` 已被占用。
- [ ] 两个真实 Blender 进程与显式选择。
- [ ] 被强杀的 Blender 留下无害的过期 descriptor。
- [ ] 交互与后台 Extension 模式。
- [ ] 构建 wheel 的元数据、数据文件、许可证和控制台入口点。
- [ ] 通过 `uvx --from <wheel> blender-mcp-connect` 在干净目录运行本地 wheel。

打包目标：

```toml
[project]
name = "blender-mcp-connect"
version = "0.1.0"

[project.scripts]
blender-mcp-connect = "blmcp:main"
```

构建检查：

```bash
python -m build ./mcp --outdir dist
python -m twine check dist/*
```

验收标准：

- 现有官方工具测试保持绿色。
- 新增纯 Python 测试在 Windows、Linux、macOS CI 上通过。
- 发布前至少在 Windows 和 Linux 上通过真实 Blender 冒烟测试。
- wheel 检查确认包含 prompts、API/manual 数据、声明、许可证和入口点。
- Extension ZIP 能在 Blender 5.1+ 安装并发布可发现的端点。

## Phase 6 — CI 与分阶段发布

工作流：

```text
.github/workflows/ci.yml
.github/workflows/upstream-sync.yml
.github/workflows/publish-pypi.yml
.github/workflows/release-extension.yml
```

PyPI Trusted Publisher 目标：

| 字段 | 值 |
|---|---|
| 项目 | `blender-mcp-connect` |
| GitHub 所有者 | `marble810` |
| 仓库 | `blender-mcp-connect` |
| 工作流 | `publish-pypi.yml` |
| 环境 | `pypi` |

发布关卡：

1. 静态检查与单元测试通过。
2. 从干净提交构建 wheel、sdist 和 Extension ZIP。
3. wheel/sdist 通过 `twine check` 和产物内容检查。
4. 本地 wheel 能从空目录通过 `uvx` 运行。
5. GitHub 预发布发布 Extension ZIP 和校验和。
6. Windows 与 Linux 真实 Blender 冒烟测试通过。
7. 包、Extension、changelog、兼容性表和标签版本一致。
8. 创建标签 `connect-v0.1.0`。
9. GitHub OIDC 发布不可变的 PyPI 版本 `0.1.0`。
10. GitHub Release 从预发布提升为稳定版。

首个 Extension 版本通过 GitHub Releases 分发，而非 Blender Lab 仓库或官方 Blender Extensions 列表。

验收标准：

- Pull Request 无法发布包。
- GitHub 中不存储长期 PyPI token。
- 只有受保护的 `pypi` 环境和下游发布标签可以发布。
- 干净机器可以只用文档中的 `uvx` 配置启动外部 Server。

## Phase 7 — 持续上游维护

每次下游发布都要记录：

- 上游基线 SHA；
- 自上次发布以来合并的上游提交；
- 仅下游的提交/功能；
- descriptor schema 版本；
- bridge 协议版本；
- 兼容的 Server 与 Extension 版本范围。

优先把通用修复贡献给上游，包括 SDK 兼容、Windows stdio 子进程处理和通用测试改进。除非 Blender Lab 明确要求，否则把下游发布、品牌、动态 registry 路径和发布自动化保留在本地。

当上游合入了等效修复时，在评审后的同步中移除下游的重复实现。

## 8. 安全要求

- 默认 bridge 只绑定 loopback。
- 动态发现要求认证端点身份。
- Token 是本地能力凭证，不是用户认证，也不是沙箱。
- 以同一 OS 用户身份运行的恶意进程仍可能访问 descriptors 或 Blender 数据。
- 自动发现绝不能启用远程/LAN 访问。
- 显式非 loopback 的传统配置必须给出明确警告。
- 官方关于任意 LLM 生成 Blender Python 的警告必须保持醒目。
- 秘密、完整 token 和敏感 descriptor 内容不得输出到 MCP stdout。
- stdio Server 运行期间所有诊断信息走 stderr，以免污染 JSON-RPC。

## 9. 0.1.0 的明确非目标

- 在 Blender 中嵌入 FastMCP 或完整 MCP Server。
- 把 MCP Server wheel 打包进 Blender Extension。
- 用 HTTP 取代 stdio 作为默认传输。
- 通过 Blender Lab 官方仓库发布。
- 声称与 Blender Foundation 有关联或获其背书。
- 在多个健康 Blender 实例中自动选择。
- 远程/LAN bridge 访问、TLS 或多用户认证。
- 在没有实例时自动启动 Blender。
- exactly-once 执行、请求去重或响应恢复。
- 在传输可能开始后重试。
- 离线首次 `uvx` 安装。
- 添加无关建模工具或改变官方 MCP 工具面。
- 首个版本发布下游 MCPB bundle（除非另行评审）。

## 10. 0.1.0 的完成定义

满足以下所有条件，发布才算完成：

- [ ] 用户在 Blender 5.1+ 安装 Connect Extension。
- [ ] 用户只添加文档中的 `mcp.json` 条目。
- [ ] 无需克隆仓库或本地 Server 路径。
- [ ] 无需手工安装 Python 依赖。
- [ ] 无需配置 bridge 端口。
- [ ] 有健康选中实例时，无需常规 `BLENDER_PATH` 配置。
- [ ] 端口 `9876` 被占用不影响 Connect。
- [ ] 单实例自动发现。
- [ ] 多实例失败关闭，不会修改任意文件。
- [ ] 被发现的端点认证其实例身份。
- [ ] 已发送或部分发送的操作绝不盲目重放。
- [ ] 官方 MCP 工具名和 schema 保持兼容。
- [ ] 显式 host/port 模式仍可用于官方传统互操作。
- [ ] 发布 wheel、sdist、Extension ZIP、源码、许可证、声明和校验和。
- [ ] PyPI 发布使用 GitHub Trusted Publishing。
- [ ] 发布说明标明确切的 Blender Lab 上游提交。

## 11. 当前进度

- [x] 已选定产品名：Blender MCP Connect。
- [x] 已创建公开 GitHub 仓库。
- [x] 已保留官方 Git 历史。
- [x] `origin` 指向 GitHub 下游。
- [x] `upstream` 指向 Blender Projects。
- [x] 已确定初始上游基线。
- [x] 已评审官方架构、安装方式、安全警告、发布与活跃问题。
- [x] 已选定默认方向：PyPI/`uvx` stdio Server + 动态本地 bridge 发现。
- [ ] 已实施 Phase 0 下游基础。
- [ ] 已记录基线测试结果。
- [ ] 已最终确定 descriptor/bridge 协议。
- [ ] 已实现动态 Extension。
- [ ] 已实现 Server 发现。
- [ ] 已实现可靠性状态机。
- [ ] 跨平台与真实 Blender 测试通过。
- [ ] 已配置 PyPI Trusted Publisher。
- [ ] 已发布 `0.1.0`。
