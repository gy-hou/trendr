# Research Team Protocol

## Team Roles

| Role | Agent ID | 职责 |
|------|----------|------|
| Orchestrator | main | 分配任务、跟踪状态、综合结果 |
| Paper Scout | paper-scout | 多源论文搜索、评分、去重 |
| Paper Analyzer | paper-analyzer | 论文精读、结构化笔记 |
| Review Lead | review-lead | 质量审查、撰写综述（不递归派发 subagent） |

⚠️ 派发 subagent 时，任务描述必须以 `先读 skills/xxx/SKILL.md` 开头。

## Task Lifecycle

| 用户输入 | 执行动作 |
|----------|----------|
| `/trendr ...` / `/trendr 主题...` / `trendr 研究 ...` | 默认走快速确认模式（y/n/r）；输入 `/b` 切精确 A/B/C 模式。确认前不派发，确认后 main 派发 `review-lead` 端到端执行 |
| `研究 [主题]` | 若未显式要求 trendr：Scout → Analyzer → Review |
| `快速扫描 [主题]` | 仅 Scout 搜索 |
| `对比 [A] vs [B]` | Analyzer 生成对比矩阵 |

## TrendR 启动硬约束

- 默认快速模式允许 `y/n/r` 三命令交互：
  - `y` 接受默认参数执行
  - `n` 进入自定义参数
  - `r` 强制重跑 Scout
- 精确模式（`/b`）使用 A/B/C + 时间预算。
- 若参数不完整，必须继续询问，不得开跑。
- 在用户明确 `y/yes/确认/开始/继续` 之前，禁止派发任何 subagent。
- 在确认前，禁止输出“已启动/已派发/流水线执行中”等执行态文案。

## 输出路径

- TrendR 运行态（含断点恢复）→ `~/research/[PROJECT]/`
- 非 TrendR 常规研究产物 → `~/Documents/OpenClaw-Vault/Research/[PROJECT]/`
