# TrendR — 自动化文献综述

/trendr 交互模式：默认快速模式，/b 切精确模式。

## TrendR 执行护栏

- 主脑必须先派发 `review-lead`，由 `review-lead` 统一编排 Scout/Analyzer/Review；禁止 main 直接跑三级流水线。
- 运行目录固定：`~/research/[PROJECT]/`（运行态），不要把中间产物写入 `~/Documents/OpenClaw-Vault/`。
- 运行态必须维护：`run_status.json`、`progress.md`、`logs/<RUN_ID>.log`、`logs/latest.log`、`logs/watchdog.pid`。
- paper-scout 固定 `runTimeoutSeconds: 900`；paper-analyzer 固定 `runTimeoutSeconds: 1200`；禁止动态计算超时。
- Phase 2 禁止跳过（除非 `candidates.csv` 不存在或仅 header）。

## TrendR 触发识别（必须）

以下任一输入都视为 TrendR 入口，统一走“参数收集 + 二次确认”：

- `/trendr`
- `/trendr 主题：...`
- `trendr 研究 ...`
- 任意包含 `trendr` 的研究请求（中英文空格/标点变体）

## /trendr 交互闸门（必须）

- 在参数完整 + 用户确认前，唯一允许动作：收集参数、回显计划、询问确认。
- 确认前禁止派发任何 subagent（含 `review-lead`）。
- 确认前禁止输出执行态文案（“已启动/已派发/流水线执行中”）。
- 参数字段必须完整：
  - 研究主题（必填）
  - 研究轮次（A/B/C）
  - 研究程度（A/B/C）
  - 时间预算（分钟）

参数缺失时必须回复以下模板（尽量原样）：

```text
/trendr 启动！这是参数化研究流程，当前是快速模式，请先选择：
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

- 若仅给主题（如 `/trendr 主题：智能体决策系统` 或 `trendr 研究 智能体决策系统`），仍视为参数不完整。
- 拿到完整参数后，先回显 ETA 与调整方案，并追加：`是否确认执行？（y / n）`。
- 只有用户明确回复 `y`（或 `yes/确认/开始/继续`）后，才允许派发 `review-lead`。
