# Research Team Protocol

## Team Roles

| Role | Agent ID | 职责 |
|------|----------|------|
| Orchestrator | main | 分配任务、跟踪状态、综合结果 |
| Paper Scout | paper-scout | 多源论文搜索、评分、去重 |
| Paper Analyzer | paper-analyzer | 论文精读、结构化笔记 |
| Review Lead | review-lead | 质量审查、撰写综述（不递归派发 subagent） |
| Verifier | verifier | 独立验证引用真实性、claim 支撑、覆盖率与分类一致性 |

⚠️ 派发 subagent 时，任务描述必须以 `先读 skills/xxx/SKILL.md` 开头。

## v2 协作补充

- 若项目目录存在 `run_state.json` 且 `version = 2`，团队按状态机协作：main 负责启动，`review-lead` 只执行当前 state 对应任务，`verifier` 只在 `VERIFY` 阶段运行。
- v2 下 Phase 推进不再由 `review-lead` 自行判断，而以 `run_state.json`、artifact validators 和状态机出口条件为准。

## Task Lifecycle

| 用户输入 | 执行动作 |
|----------|----------|
| `/tr ...` / `/tr 主题...` / `/trendr ...` / `trendr 研究 ...` | 统一先参数化交互收集并二次确认；确认前不派发，确认后 main 派发 `review-lead` 端到端执行 |
| `研究 [主题]` | 若未显式要求 trendr：Scout → Analyzer → Review |
| `快速扫描 [主题]` | 仅 Scout 搜索 |
| `对比 [A] vs [B]` | Analyzer 生成对比矩阵 |

## TrendR 启动硬约束

- 主入口为 `/tr`（兼容旧入口 `/trendr`）。
- `/tr` 默认进入参数化快速模式，`/b` 切精确模式（A/B/C + 时间预算）。
- 若参数不完整，必须继续询问，不得开跑。
- 在用户明确 `y/yes/确认/开始/继续` 之前，禁止派发任何 subagent。
- 在确认前，禁止输出“已启动/已派发/流水线执行中”等执行态文案。

## 输出路径

- TrendR 运行态（含断点恢复）→ `~/research/[PROJECT]/`
- 非 TrendR 常规研究产物 → `~/Documents/OpenClaw-Vault/Research/[PROJECT]/`

## v2 File Contracts（简要）

- `candidates.csv`：必须带 header，最少包含 `paper_id,title,authors,year,source,relevance_score,url`；`paper_id` 视为主键，不得重复。
- `verify.json`：由 `verifier` 在 `VERIFY` 阶段输出；顶层至少包含 `pass`、`run_id`、`checked_at`、`summary`、`checks`。
- `verify.json.checks`：按检查项分组，常见 key 包括 `citation_existence`、`citation_reality`、`claim_support`、`coverage`、`taxonomy_consistency`、`bib_quality`。
- 每个 check 对象应至少包含 `pass`、`severity`、`details`、`issues`；其中 `severity=error` 的失败会阻塞完成，`warning` 只记录不阻塞。
