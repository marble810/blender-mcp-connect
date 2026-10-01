# pr-watch：每周两次的 PR 检查，没活不起 agent

- 日期：2026-10-01 11:02 UTC
- 关联：`2026-10-01_10-20-05_pr-schedule-design.md`（第一份设计：PR 分析 + 纯 schedule 方案，保留为备选）
- 需求：**每周两次检查 PR；没有新 PR 就不要呼起 agent；有活时 agent 处理完自己归档**
- 结论：这条需求 **Paseo schedule 做不到**（schedule 每一轮必然起一个 agent），
  所以把定时器放进 daemon —— 写了本地插件 `pr-watch`：tick → 跑纯脚本门禁 → 有活才 `paseo run`。

---

## 1. 为什么不是 schedule

| 方案 | 没活时会不会起 agent | 说明 |
|---|---|---|
| Paseo schedule（cron） | **会** | `schedule/service.js` 的 `runSchedule()` 对 `new-agent` target 一定会建 workspace + 起 agent，再把 prompt 发进去；cron 触发点没有「先跑脚本」的位置 |
| 插件 + daemon 定时器 | **不会** | 定时器在插件子进程里，只有门禁说「有活」时才 `paseo run` |

插件的定时器不占 agent、不烧 token；没活的一轮成本 ≈ 一次 `gh pr list`。
第一份文档里的 schedule 方案仍然可用（`scripts/schedule-prompt.txt`），只是每轮会多一个几秒钟的小 agent。

## 2. 机制

```
pr-watch（daemon 里的插件子进程）
   ├─ setInterval 60s → tick()
   │     ├─ 到点了吗？（周一/周四 09:00 Asia/Shanghai，当天错过会补跑）
   │     │   └─ 或者有人 touch 了 state/run-now
   │     ├─ bash scripts/pr-guard.sh   ← 纯脚本，只读 gh
   │     └─ STATE=WORK / MERGE → paseo run --background（cwd=控制目录）
   │           STATE=其它 → 只写日志
   │
   └─ server.on("agent.turn_ended") → 如果这个 agent 是我们起的 → paseo.agents.ref(id).archive()
```

四个设计取舍：

1. **门禁还是那个纯脚本**（`pr-guard.sh`）：无本地状态，状态全从 GitHub 算，容器重建不失忆。
2. **起 agent 用 `paseo run` CLI，不用插件 SDK**：定时器里拿不到 `paseo` API
   （`PluginHandlerContext.paseo` 只在 `server.handle` / hook 上下文里），
   而 CLI 是这台机器上验证过的路径（`paseo-discord-bridge` 也这么起 agent）。
3. **归档用 hook 里的 `paseo`**：`server.on("agent.turn_ended")` 的回调第二参数就是带 `paseo` 的上下文，
   跑完一轮就归档 —— 等价于 schedule 的 `archiveOnFinish`，且不需要循环等待。
4. **一次把活干完**：插件每周只醒两次，所以 agent 的 prompt（`scripts/agent-prompt.txt`）
   要求「解冲突 → push → 等 CI（最多 30 分钟）→ 合并 + 关重复 PR」，而不是「一轮做一件事」。

## 3. 踩到的坑（都已在代码里处理）

| 坑 | 现象 | 处理 |
|---|---|---|
| WIP merge 会把上游提交算进 PR 的 commits | 第一版门禁把 `dbbf836`（Campbell Barton）当成「我们的 fix 提交」，误判成 `HUMAN/ci_not_triggered` | `our-fix` 按 git 身份邮箱统计，不能只排除 bot |
| `gh pr list --json commits` 撞 GraphQL 节点上限 | `This query requests up to 510,100 possible nodes which exceeds the maximum limit of 500,000` | 列表不取 commits，只对目标 PR 单独 `gh pr view --json commits` |
| daemon 的 PATH 里没有 `gh` | `paseo workspace create --mode checkout-pr` 报 `GitHub CLI (gh) is not installed or in PATH` | PR worktree 改用 `--mode checkout-branch`（纯 git，已验证可用） |
| 插件子进程会继承 `PASEO_AGENT_*` | CLI 会忽略 `--cwd`、复用调用者的 workspace | `childEnv()` 里删掉这三个变量（抄 `paseo-discord-bridge` 的做法） |
| daemon 重启 | 定时器丢状态 → 可能一天跑两次或漏跑 | 状态落 `~/.config/pr-watch/state.json`（`lastFiredSlot`），启动时 tick 一次补跑 |
| 上一轮 agent 还在跑 | 两个 agent 抢同一个 PR | `trackedAgents` 非空时本轮直接跳过并记日志 |

## 4. 验证记录

| 验证 | 方式 | 结果 |
|---|---|---|
| 门禁状态机 | `bash scripts/selftest-pr-guard.sh`（stub gh + 6 fixture） | 6/6 通过 |
| 插件周计划逻辑 | `npm run test:slots`（`node --experimental-strip-types`） | 11/11 通过（含跨时区/夏令时） |
| workflow 去重逻辑 | 从 YAML 抽出真实 `run:` 块 + stub gh，跑 5 个场景 | 5/5 通过（同 SHA 跳过、有人改过不关、上游前进关旧开新、main 已吸收关残留、无 PR 开新） |
| 端到端 | 装插件 → 启动即补跑当天 slot（10-01 是周四，已过 09:00）→ 门禁 `STATE=WORK PR=13` → 起了 agent `65d5fe46` | 见下 |

端到端现场（2026-10-01 10:57–11:0x UTC）：

```
[paseo plugin logs pr-watch]
  开始检查（trigger=slot slot=2026-10-01）
  门禁: exit=10 STATE=WORK PR=13 REASON=merge_conflicts
  STATE=WORK → 起了 agent 65d5fe46-45d1-446a-81a3-a65eb27ebaca（PR 处理 #13）
  启动完成：周一/周四 09:00 (Asia/Shanghai)；下一次 2026-10-05T01:00:00.000Z

[agent 65d5fe46 的 timeline]
  建 Paseo worktree（.paseo/worktrees/2jyqzqa5/sync-upstream-20261001-063409）
  解 LICENSE 冲突（两边都是 GPL-3.0 全文，只差 https/http）→ commit → push d9e93f3
  → 我的 push 触发了 CI（bot 开的 PR 本来没有 check）
  → timeout 1800 gh pr checks 13 --watch --interval 30
```

这也验证了第一份文档里的假设：**bot 用 `GITHUB_TOKEN` 开的 PR 不会自动跑 CI，agent 以 marble810 身份 push 才会触发。**

## 5. 顺手治根：upstream-sync.yml 不再重复开 PR

`.github/workflows/upstream-sync.yml` 原来每次运行都新开一个 `sync/upstream-<时间戳>` PR，
上游 SHA 两天没动就攒出 #12 / #13 这种逐字节相同的重复 PR。

新增 `Reconcile existing sync PRs` 一步（在开 PR 之前）：

1. `main` 已经吸收上游（push 成功）→ 关掉残留的同步 PR；
2. 已有同一个上游 SHA 的开放 PR → **不再开新 PR、也不建新分支**，并把同 SHA 的旧 PR 关掉；
3. 上游 SHA 变了 → 关掉旧的（作废），再开新的。

关闭有保护：**分支头提交还是 bot 的 WIP 才关**；有人已经补过提交的分支不关，只打 `::warning::`。
同一时间只保留一个开放同步 PR。已推 `main`：`d456c88`。

## 6. 运维

```bash
paseo plugin ls / logs pr-watch / reload pr-watch      # 状态、日志、改完重载
cat ~/.config/pr-watch/state.json                      # 上次 slot + 最近 20 轮
touch /workspace/mabo-blender-mcp-connect/state/run-now # 立刻检查一次
bash /workspace/mabo-blender-mcp-connect/scripts/pr-guard.sh   # 只看状态
```

可调项在 `/workspace/pr-watch/server/config.ts`：`schedule.weekdays/hour/minute`、provider、thinking、总开关。

## 7. 边界与风险

| 风险 | 缓解 |
|---|---|
| 插件崩了 → 静默不检查 | `paseo plugin ls` 看得到状态，`paseo plugin logs` 看得到历史；daemon 重启会重新加载并补跑当天 slot |
| 无人值守解错冲突 | 门禁只认「能明确判断」的场景；agent 判不准 → 写进 PR 评论 + 停手；合并前强制 `git grep '^<<<<<<<'` |
| 死循环修 CI | 门禁 `PRG_MAX_FIX_COMMITS=3` → `HUMAN`，不再起 agent |
| 抢人工正在写的分支 | `PRG_INFLIGHT_MINUTES=20` → `SKIP_INFLIGHT` |
| agent 起不来 / 归档失败 | 都写 `console.error`（`paseo plugin logs`）并落 `state.json`，不静默 |
| 一周只醒两次 → PR 最多躺 3 天 | 是需求本身；要更快就把 `config.ts` 的 `weekdays` 改成每天或加 `run-now` |
