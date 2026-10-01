# 用 Paseo Schedule 自动处理 sync PR —— 分析与设计

- 日期：2026-10-01 10:20 UTC
- 范围：`marble810/blender-mcp-connect` 里由 `upstream-sync` workflow 开出的 PR
- 目标：**新 PR 出现 → 唤起任务 → Agent 处理 → 归档**
- 结论：Paseo schedule 只有 cron（没有事件触发），所以做成「便宜轮询 + 每轮最多干一件事」，
  门禁（纯脚本）判断该不该干活，Agent 只负责解冲突/修 CI/合并，归档由 Paseo 自动完成。

---

## 1. PR 现状分析

### 1.1 这些 PR 是怎么来的

`.github/workflows/upstream-sync.yml` 每天 06:00 UTC 把上游 `lab/blender_mcp` 的 `main`
合并进下游 `main`：

| 情况 | 结果 |
|---|---|
| 干净合并 + 单测通过 | 直接 push 到 `main`（merge commit，带上游 SHA） |
| 冲突 / 测试失败 / push 被拒 | 推 `sync/upstream-<时间戳>` 分支，开 PR，assign 给 owner，**冲突以 marker 形式提交（WIP）** |

即：**PR = 需要人（或 agent）介入的工作台**，不是「代码评审」。

### 1.2 现在积压了什么

| PR | 分支 | 上游 SHA | 状态 | 内容 |
|---|---|---|---|---|
| #13 | `sync/upstream-20261001-063409` | `dbbf836` | OPEN，0 checks | LICENSE 有 4 处冲突标记 |
| #12 | `sync/upstream-20260930-063353` | `dbbf836` | OPEN，0 checks | 与 #13 **内容完全相同** |

`git diff --stat` 两个分支为空 —— 同一天的上游 SHA，被 workflow 连续两天各开了一个 PR。
**重复 PR 是设计里的一个坑**（见 §6.1）。

冲突本体很小：上游 `dbbf836 "Include GPL3+ license"` 与下游各自持有 GPL-3.0 全文，
只差 `https://` vs `http://` 4 处 URL。属于「看一眼就能定」的冲突。

### 1.3 之前是怎么处理的（#11，2026-09-18）

```
69bfd65  github-actions[bot]  WIP: merge upstream ff54e4d (conflicts marked)
9031e31  marble810            fix: resolve upstream sync conflict in addon server
d410149  marble810            fix: resolve upstream sync conflict in mcp/pyproject.toml
2d3166d  marble810            fix: resolve upstream sync conflict in mcp/requirements.txt
73f74fa  marble810            fix: resolve upstream sync conflict in mcp/manifest.json
85293d0  marble810            fix: strip non-pickleable docutils diagnostics
21031d8  marble810            fix: register details RST directive
   ↓
915e3d0  合并（10 个 CI check 全绿，GitHub 默认 merge commit）
```

**这就是要自动化的流程本身**：在 PR 分支上补 `fix:` 提交 → CI 跑起来 → 绿了合掉。
所以任务是可以被脚本 + agent 稳定复现的，不需要发明新流程。

### 1.4 关键约束（决定设计）

1. **容器里没有 python**（`python3`/`pip` 都没有）→ 本地跑不了 `pytest`，
   **CI 是唯一的验证手段**。
2. bot 用 `GITHUB_TOKEN` 推分支/开 PR，**GitHub 不会为它触发 workflow**（防递归），
   所以新 PR 的 `statusCheckRollup` 是空的；**agent 以 marble810 身份 push 才会触发 CI**
   （#11 的 10 个 check 就是这么来的）。
3. `main` 没有 branch protection，`allow_merge_commit: true`，`delete_branch_on_merge: false`
   → `gh pr merge --merge --delete-branch` 可用。
4. gh CLI 在 `/home/paseo/.local/bin/gh`（持久），全局 git 身份和 credential helper 都已配好。

---

## 2. 为什么必须是「轮询」

Paseo schedule 的触发面只有 cron（`paseo schedule create --every/--cron`），没有 webhook/事件；
容器没有公网入口，GitHub 也推不进来。所以：

- 每 30 分钟醒一次，**先跑一次纯脚本门禁**（一次 `gh pr list`，毫秒级），
  没事就一行回复结束 → 大多数轮询的成本 ≈ 一次 bash 调用；
- 每轮最多干一件事（解冲突 **或** 合并），**不等 CI**（等 CI 会占着 agent 十几分钟）；
- 谁来记状态？**不记**。分支提交、check 状态、mergeable 本来就是状态机，
  每轮从 GitHub 重新算。容器重建/状态文件丢失都不会失忆。

---

## 3. 设计总览

```
每 30 分钟   Paseo schedule（new-agent，cwd=/workspace/mabo-blender-mcp-connect）
   │
   ├─ pr-guard.sh（纯脚本，只读 gh）  ── STATE=NONE / WAIT / SKIP_INFLIGHT → 一行回复，结束
   │                                   ── STATE=HUMAN  → 报人工，结束
   │                                   ── STATE=WORK   → 解冲突/修 CI
   │                                   ── STATE=MERGE  → 合并 + 关重复 PR
   │
   ├─ WORK ：paseo workspace create --isolation worktree --mode checkout-branch
   │         → 在 worktree 里改 → git commit → git push origin HEAD:refs/heads/<branch>
   │         → paseo workspace archive <wsid> → 汇报（不等 CI）
   │
   ├─ MERGE：git grep '^<<<<<<<' FETCH_HEAD（确认无残留标记）
   │         → gh pr merge --merge --delete-branch --subject "Sync from Blender Lab MCP main <sha>"
   │         → gh pr close <重复 PR> --comment "Superseded by #N"
   │
   └─ run 结束 → Paseo 自动归档本次 agent + workspace（new-agent 默认 archiveOnFinish=true）
```

### 3.1 门禁状态机（`pr-guard.sh`）

| STATE | 触发条件 | 退出码 | 动作 |
|---|---|---|---|
| `NONE` | 没有 `sync/upstream-*` 开放 PR | 0 | 一行回复 |
| `WAIT` | 有 pending check，或刚推完 fix | 0 | 一行回复 |
| `SKIP_INFLIGHT` | CI 绿但最新 fix < 20 min | 0 | 一行回复（防抢） |
| `WORK` | `merge_conflicts` / `checks_failed` / `tests_failed` / `push_rejected` | 10 | 第 2 步 |
| `MERGE` | 全绿 + 有我们的 fix 提交 | 11 | 第 3 步 |
| `HUMAN` | fix ≥3 轮仍红 / 推了但 CI 没起来 / 绿得莫名 | 12 | 停手报人工 |
| `ERROR` | gh 缺失/网络/仓库路径 | 2 | 报 REASON |

「我们的 fix 提交」按 git 身份 `55498226+marble810@users.noreply.github.com` 统计 ——
不能简单排除 bot，因为 **WIP merge commit 会把上游作者（Campbell Barton 等）的提交也带进 PR 的 commits 列表**，
第一版就是这么误判成 `HUMAN/ci_not_triggered` 的。

### 3.2 Agent 做活的边界

- **只在 Paseo worktree 里动 PR 分支**，产品克隆 `/workspace/blender-mcp-connect` 只允许只读命令；
- 解冲突优先级：上游权威 → 默认取上游；下游有意的产品差异（包名/entry point/registry 路径/
  品牌 readme/NOTICE/PyPI workflow/独立版本号）必须保留；LICENSE 这类法律文本只差 URL 时保留下游版本；
  **判不准就停手**（写进 PR 评论标人工），不猜；
- 不 force push / 不 rebase / 不 amend 已推送提交；
- CI 没绿不许合并；同一 PR 最多修 2 轮（门禁在 ≥3 个 fix 提交时转 HUMAN，天然防死循环）。

### 3.3 「归档」落在哪

| 对象 | 谁归档 | 机制 |
|---|---|---|
| 本轮 schedule 的 agent + workspace | **Paseo 自动** | `new-agent` target 的 `archiveOnFinish` 默认 true；即使 daemon 重启，`recoverInterruptedSchedule` 也会归档掉中断的 run workspace |
| PR 实做用的 worktree | Agent 显式 | `paseo workspace archive <wsid>`（prompt 里要求成功失败都要执行） |
| 残留兜底 | 门禁报告 | `pr-guard.sh` 每轮列 `LEFTOVER=… pr-sync-*`（只看不删，避免误删有未提交改动的 worktree） |

---

## 4. Paseo 能力核对（读的是容器里的实现，不是猜）

| 问题 | 结论 | 依据 |
|---|---|---|
| schedule 能事件触发吗？ | 不能，只有 cron | `paseo schedule create --every/--cron`；`schedule/service.js` 只有 `tick()` |
| 上一轮没跑完，下一轮会叠加吗？ | 不会，直接跳过 | `tick()` 里 `if (this.runningScheduleIds.has(schedule.id)) continue;` |
| run 完会自动归档吗？ | 会（new-agent 默认） | `shouldArchiveScheduleRunWorkspace()`：`agentId === null \|\| (archiveOnFinish ?? true)`；`runSchedule` 的 finally 调 `archiveWorkspace` |
| schedule 能指定 worktree 隔离吗？ | CLI **不能**（只有 `--cwd`） | `cli/dist/commands/schedule/index.js` 无 `--isolation`；MCP 里才有 `isolation`，本环境 pi 没有 paseo MCP |
| `--mode checkout-pr` 能用吗？ | **不能**：daemon 的 PATH 里没有 `gh` | `paseo workspace create --mode checkout-pr` 报 "GitHub CLI (gh) is not installed or in PATH"；`/proc/<daemon>/environ` 的 PATH = `/home/paseo/.pi/agent/bin:/usr/local/{s,}bin:/usr/bin:/bin` |
| `--mode checkout-branch` 能用吗？ | 能（只用 git） | 实测：建 → 在分支上 → `paseo workspace archive` 干净回收 |
| 归档了 worktree，分支会没吗？ | 不会，只删 worktree 目录 | 实测 archive 后 `.paseo/worktrees` 释放 |

---

## 5. 交付物（已就绪）

控制目录 `/workspace/mabo-blender-mcp-connect/`（不是 git 仓库，对齐 `mabo-paseo-discord-bridge` 的做法）：

| 文件 | 作用 |
|---|---|
| `scripts/pr-guard.sh` | 门禁状态机，只读 gh，输出 `STATE/PR/BRANCH/REASON/duplicates/LEFTOVER` |
| `scripts/selftest-pr-guard.sh` | 离线自测：stub `gh` + 6 个 fixture，断言 `WORK/WAIT/MERGE/HUMAN/NONE/SKIP_INFLIGHT` 六条路径（当前 6/6 通过） |
| `scripts/schedule-prompt.txt` | 定时任务的 prompt 正文（可直接 `schedule update --prompt "$(cat …)"`） |
| `README.md` | 任务说明、状态机表、创建/运维命令、已知边界 |

实测（对当前真实 PR）：

```
open-prs  : 2      target: #13 sync/upstream-20261001-063409   upstream: dbbf836
commits   : total=2 our-fix=0 bot=1 head=a382993f (225m ago)
checks    : total=0 pending=0 failed=0
reason-tag: merge_conflicts   conflicts: LICENSE
duplicates: #12 (同一上游 SHA，合并时一起关掉)
STATE=WORK PR=13 REASON=merge_conflicts   (exit 10)
```

## 6. 激活步骤

```bash
cd /workspace/mabo-blender-mcp-connect
paseo schedule create --every 30m \
  --name "blender-mcp-connect PR 轮询" \
  --provider "pi/opencode-go/deepseek-v4.1-flash" --thinking max \
  --cwd /workspace/mabo-blender-mcp-connect \
  "$(cat scripts/schedule-prompt.txt)"
# 立刻验证一轮（可选）：
paseo schedule run-once <schedule-id>
paseo schedule logs <schedule-id>
```

建议的第一次验证：先手动 `bash scripts/pr-guard.sh`（应输出 `STATE=WORK PR=13`），
再 `run-once`，看 agent 是否按第 2 步解掉 LICENSE 冲突并 push；
下一轮 tick 看它是否在 CI 绿后合并 #13 并关掉 #12。

---

## 7. 后续可选改进（不在本次范围）

1. **修 `upstream-sync.yml` 的重复 PR**：开 PR 前先查有没有同上游 SHA 的开放同步 PR，
   有就跳过（或复用旧分支），从源头消灭 #12/#13 这种双开。
2. **让 daemon 能看到 `gh`**：把 `/home/paseo/.local/bin` 加进 daemon 的 PATH
   （或做一个 `/usr/local/bin/gh` 符号链接，但容器重建会丢，要进 Dockerfile）。
   之后 `paseo workspace create --mode checkout-pr` 就能用，PR checkout 更语义化。
3. **把 MERGE 步骤脚本化**：它本来就是确定性的（无 marker + CI 绿 → 合并 → 关重复），
   放进门禁脚本执行可以让「合并」不依赖 LLM 判断；保留 agent 只是为了汇报和兜底。
4. **通知**：现在只有 `paseo schedule logs` / Paseo UI；要即时通知可接已有的 Discord bridge
   （HUMAN 状态下发一条消息）。
5. **扩大处理范围**：目前只碰 `sync/upstream-*`；人开的 PR 一律不动。要扩就把
   `PRG_SYNC_PREFIX` 换成白名单并单独设计评审策略（不要默认自动合并人开的 PR）。

## 8. 风险与边界

| 风险 | 缓解 |
|---|---|
| 无人值守解错冲突 | 只在判据明确时动手；判不准 → PR 评论 + 停手；合并前强制 grep 冲突标记 |
| 死循环修 CI | 门禁 `PRG_MAX_FIX_COMMITS=3` → HUMAN；HUMAN 状态不动手 |
| 抢占人工正在写的分支 | `PRG_INFLIGHT_MINUTES=20` → SKIP_INFLIGHT |
| worktree 泄漏 | agent 显式 archive + 门禁每轮 `LEFTOVER` 报告 |
| 轮询太频繁 | 30 分钟一次 × 每天 48 轮；无活时每轮只有一次 gh 查询 + 一行回复 |
| 合并策略跑偏 | 固定 merge commit（不改写历史），message 与 workflow 自动合并保持一致（记录上游 SHA） |
| 上游/workflow 变化 | 门禁只依赖 PR 的分支名、正文、checks、mergeable，不依赖 workflow 内部实现细节 |
