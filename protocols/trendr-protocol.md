# TrendR — 自动化文献综述

主入口：`/tr`（兼容旧入口 `/trendr`）。

## TrendR 执行护栏

- 主脑必须先派发 `review-lead`，由 `review-lead` 统一编排 Scout/Analyzer/Review；禁止 main 直接跑三级流水线。
- 如果项目目录存在 `run_state.json`（`version: 2`），由状态机驱动，`review-lead` 只执行当前 state 的任务，不自己管理 Phase 推进。
- 运行目录固定：`~/research/[PROJECT]/`（运行态），不要把中间产物写入 `~/Documents/OpenClaw-Vault/`。
- 运行态必须维护：`run_status.json`、`progress.md`、`logs/<RUN_ID>.log`、`logs/latest.log`、`logs/watchdog.pid`。
- paper-scout 固定 `runTimeoutSeconds: 900`；paper-analyzer 固定 `runTimeoutSeconds: 1200`；禁止动态计算超时。
- Phase 2 禁止跳过（除非 `candidates.csv` 不存在或仅 header）。

## TrendR 触发识别（必须）

以下任一输入都视为 TrendR 入口：

- `/tr`
- `/tr 主题：...`
- `/trendr`（兼容）
- `/trendr 主题：...`（兼容）
- `trendr 研究 ...` / `tr 研究 ...`
- 任意包含 `trendr` 的研究请求（中英文空格/标点变体）

## 参数化计划（必须）

- `/tr` 默认进入快速模式；若用户输入 `/b`，切换到精确模式。
- `/tr` 首条交互必须使用以下模板（尽量原样）：

```text
/tr 启动！这是参数化研究流程，当前是快速模式，请先选择：
（若要进入精确模式调整，输入：/b)

1) 研究主题（必填）
2) 研究轮次：A/B/C
   - A = 1-3 轮（轻量）
   - B = 3-6 轮（标准）
   - C = 6-10 轮（深度）

3) 研究程度：A/B/C
   - A = API 标准检索（快）
   - B = API + Scrapling（更全）
   - C = API + Scrapling + Tavily（常规最强）

4) 时间预算（分钟）

示例：主题：RL 多智能体做市；B / B / 60
```

- 若任务包含以下约束，必须先做可行性估算再执行：
  - 研究主题（必填，一句话）
  - 源头规模（A=20-30 / B=30-50 / C=50-100）
  - 研究轮次（A=1-3 / B=3-6 / C=6-10）
  - 深度（A=轻度 / B=中度 / C=深度）
  - 时间预算（分钟）
- 若用户只给了 A/B/C 和时间、未给研究主题：先追问主题，不得直接进入 ETA 计算。
- 首条交互必须包含“研究主题”问题，并给出示例回复格式：`主题：xxx；B / B / B / 30`。
- 估算公式：`eta = 8 + source_factor + round_factor + depth_factor`
  - `source_factor`: A=10, B=22, C=40
  - `round_factor`: A=8, B=20, C=35
  - `depth_factor`: A=0, B=10, C=20
- 若预算 < `eta * 0.7`，自动调整（先降轮次，再降源头规模），并把调整原因写入日志。
- ETA 回显后必须追加：`是否确认执行？（y / n）`。

## 交互闸门（硬限制）

- 在用户明确确认（`y/yes/确认/开始/继续`）前，禁止派发任何 subagent（含 `review-lead`）。
- 在确认前，禁止输出“已启动/已派发/流水线执行中”等执行态文案。
- 若参数不完整（例如只给主题），必须继续收集参数，不得开跑。

## v2 心跳协议（heartbeat.json）

- v2 运行态额外维护 `~/research/[PROJECT]/heartbeat.json`，作为活跃 agent 的文件心跳。
- `heartbeat.json` 至少包含四个字段：`agent`、`state`、`updated_at`、`message`。
- 当前 state 的执行者必须持续刷新 `heartbeat.json`；watchdog 通过 `heartbeat.json` + `run_state.json` 联合判断是否卡死。
- 若 `heartbeat.json` 长时间不更新，或 `run_state.json.current_state` 与产物进度明显脱节，由 watchdog 写入 `resume_request.json` 请求续接。
- 排查运行异常时，优先检查 `run_state.json`、`heartbeat.json`、`logs/latest.log` 三个文件是否一致。

## v2 Verify Phase（自动）

- v2 状态机固定包含 `VERIFY` 阶段：`WRITING` 完成后，不直接进入 `DONE`，而是自动调用 `verifier` agent。
- `verifier` 读取 `review.md`、`references.bib`、`candidates.csv`、`matrix.csv`、`notes/*.md`，输出 `verify.json`。
- `verify.json.pass = true` 时，状态机进入 `DONE`；`verify.json.pass = false` 时，状态机回退到 `WRITING` 进行修复（最多 2 轮）。
- `review-lead` 不负责手动决定是否跳过验证，也不负责自行宣布“已完成”；是否完成以 `VERIFY` 结果和状态机转换为准。
