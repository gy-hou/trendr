# TrendR — 自动化文献综述

/trendr 交互模式分两层：

- 默认快速确认模式：`y / n / r`
- 精确模式：输入 `/b`，使用 `A/B/C` 参数化

## TrendR 执行护栏

- 主脑必须先派发 `review-lead`，由 `review-lead` 统一编排 Scout/Analyzer/Review；禁止 main 直接跑三级流水线。
- 运行目录固定：`~/research/[PROJECT]/`（运行态），不要把中间产物写入 `~/Documents/OpenClaw-Vault/`。
- 运行态必须维护：`run_status.json`、`progress.md`、`logs/<RUN_ID>.log`、`logs/latest.log`、`logs/watchdog.pid`。
- paper-scout 固定 `runTimeoutSeconds: 900`；paper-analyzer 固定 `runTimeoutSeconds: 1200`；禁止动态计算超时。
- Phase 2 禁止跳过（除非 `candidates.csv` 不存在或仅 header）。

## TrendR 触发识别（必须）

以下任一输入都视为 TrendR 入口：

- `/trendr`
- `/trendr 主题：...`
- `trendr 研究 ...`
- 任意包含 `trendr` 的研究请求（中英文空格/标点变体）

## 默认快速确认模式（y/n/r，必须优先）

当用户进入 TrendR 且未输入 `/b` 时，优先使用这套快速交互。

若已给主题，主脑首条回复模板如下（尽量原样）：

```text
收到。主题已确定：{TOPIC} 🤖

但在派发前需要确认以下参数：

| 参数 | 选项 | 说明 |
|------|------|------|
| 轮次 | 3轮（默认）/ 5轮 / 自定义 | 搜索-分析循环次数 |
| 深度 | 快速（5篇）/ 标准（10篇）/ 深度（20篇） | 每轮候选论文数 |
| 预算 | 3篇（默认）/ 5篇 / 全部 | 最终综述引用量 |

确认命令： y 接受默认参数 / n 自定义 / r 重新 Scout
```

快速模式命令语义：

- `y`：接受默认参数（3 轮 + 标准10篇 + 引用3篇），进入执行。
- `n`：进入自定义参数收集，不得直接执行。
- `r`：强制重跑 Scout，再继续后续流程。

若检测到已有 `~/research/[PROJECT]/candidates.csv`，可附加提示“可继承 candidates.csv 从 Analyzer 继续，或 r 重新 Scout”。

## 精确模式（/b，A/B/C）

当用户输入 `/b` 或明确要求“精确模式”时，切换到 `A/B/C` 参数化模板：

- 研究主题（必填）
- 研究轮次：A/B/C（1-3 / 3-6 / 6-10）
- 研究程度：A/B/C（API / API+Scrapling / API+Scrapling+Tavily）
- 时间预算（分钟）

拿到完整参数后，先回显 ETA 与调整方案，再问：`是否确认执行？（y / n）`。

## 交互闸门（硬限制）

- 在用户明确确认（`y/yes/确认/开始/继续`）前，禁止派发任何 subagent（含 `review-lead`）。
- 在确认前，禁止输出“已启动/已派发/流水线执行中”等执行态文案。
- 若参数不完整（例如只给主题），必须继续收集参数，不得开跑。
