# TrendR Improve Plan (Phased)

## 1. 目标与范围

本计划把 TrendR 明确分为三档产品，并分阶段落地，目标是：

1. 降低上手门槛（先用热点监控，再进研究流水线）。
2. 提升核心链路稳定性（状态机、验证、恢复、可观测性）。
3. 让 Full 能力可选叠加，而不是默认复杂化。

三档定义：

- Tier 1: `Lite / Hotspots`  
  平台热点抓取与摘要，不运行文献综述状态机。
- Tier 2: `Basic / Research`  
  标准研究流水线：`DISCOVERY -> ANALYSIS -> GAP_CHECK -> WRITING -> VERIFY`。
- Tier 3: `Full / Research+Ops`  
  在 Basic 基础上叠加深挖、知识库、外部工具集成。

---

## 2. 里程碑概览

| 阶段 | 目标 | 预计时长 | 里程碑 |
|---|---|---:|---|
| Phase 0 | 规格冻结与接口设计 | 2-3 天 | profile 规范冻结 |
| Phase 1 | Tier 1 落地（Lite） | 4-6 天 | `hotspots` 子命令可独立运行 |
| Phase 2 | Tier 2 稳定化（Basic） | 1-2 周 | 端到端成功率与恢复能力达标 |
| Phase 3 | Tier 3 集成（Full） | 1-2 周 | Full 依赖可插拔上线 |
| Phase 4 | 发布与迁移 | 3-5 天 | 文档、安装器、兼容策略完成 |

---

## 3. 分阶段执行计划

## Phase 0 - 规格冻结

### 目标
- 定义统一 profile 模型：`lite | basic | full`。
- 明确每档能力边界、输出契约、依赖矩阵。

### 任务
- 在 CLI 增加 profile 参数规范：
  - `cli.py run --profile basic|full`
  - 新增 `cli.py hotspots --profile lite`（或 `cli.py run --profile lite` 的子路径）。
- 产出 profile 契约文档（输入、输出、状态文件差异）。
- 确认向后兼容策略（默认值、旧参数映射）。

### 验收标准
- 评审通过一份 profile 规格文档。
- 不改业务逻辑，仅完成参数与契约冻结。

---

## Phase 1 - Tier 1 (Lite / Hotspots)

### 目标
- 把热点监控从“附加能力”升级为独立第一档产品。

### 任务
- 新建热点链路执行器（不依赖 state machine 主链）。
- 输出统一产物：
  - `hotspots_raw.json`
  - `hotspots_report.md`
  - `hotspots_summary.json`
- 给 `platform-hotspots` 增加失败降级策略：
  - Chrome CDP 不可用时回退 web 搜索摘要。
- 增加最小调度能力（按天/按小时触发可选）。

### 涉及文件（建议）
- `cli.py`
- `engine/` 下新增 `hotspots_runner.py`（或同等模块）
- `skills/platform-hotspots/SKILL.md`
- `README.md`, `README_EN.md`

### 验收标准
- 无研究链路依赖时可单独完成热点报告。
- 失败可降级并返回结构化错误，不中断进程。

---

## Phase 2 - Tier 2 (Basic / Research) 稳定化

### 目标
- 把 Basic 作为主力稳定版本，优先保证“稳定完成”。

### 已完成（本轮）
- 预算硬中断改为软预算模式（不再硬跳阶段）。
- ANALYSIS 失败时可兜底产出最小 `notes/matrix`。
- VERIFY 在 notes 缺失时升级为 error，且增加本地确定性校验落盘。
- 两个 P0 已处理：
  - 移除 openclaw adapter CLI 模式 `shell=True` 注入面。
  - watchdog 时间戳容错，避免守护进程因脏数据崩溃。

### 后续任务
- 增加“远端验证失败 -> 本地验证兜底”失败路径指标埋点。
- fallback 产物改为“合并模式”而非覆盖。
- 增加状态机幂等恢复测试（中断/重启/重复 resume）。

### 验收标准
- 基础端到端成功率 >= 90%（受限网络环境下）。
- `resume` 后 1 次内恢复率 >= 95%。
- 关键状态转移与验证路径有单测覆盖。

---

## Phase 3 - Tier 3 (Full / Research+Ops)

### 目标
- 让 Full 能力“可插拔”，不污染 Basic 主链。

### 任务
- 定义 Full 插件层接口（Scrapling、Obsidian、Zotero、PDF 等）。
- 每个 Full 组件支持：
  - 能力探测（available/unavailable）
  - 失败降级（不阻断主链）
  - 明确日志与状态标注
- 增加 Full profile 依赖检查器与 preflight 报告。

### 验收标准
- Full 功能失效时自动降级到 Basic，不导致 run fail。
- Full 组件在 `run_state` 中有可观测状态。

---

## Phase 4 - 发布与迁移

### 目标
- 对外发布三档模型并完成迁移。

### 任务
- 更新安装器：
  - `install.sh --profile lite|basic|full`
- 更新文档：
  - README 首页三档引导
  - CLI 示例按档位分组
- 增加迁移指引：
  - 旧命令到新命令映射
  - 旧 run 目录兼容规则

### 验收标准
- 新用户 5 分钟内可跑通 Lite 或 Basic。
- 旧用户命令不崩（至少有兼容提示和自动映射）。

---

## 4. 技术债与风险清单

- 风险 A：三档共用代码耦合过高。  
  处理：先抽 profile router，再分执行器，禁止在一个 executor 里写三档分支。

- 风险 B：Full 依赖造成安装复杂度上升。  
  处理：安装器强制“按档安装”，默认 Basic，不再默认提示全部组件。

- 风险 C：状态机与热点链路混用导致模型混乱。  
  处理：Lite 保持独立，不进入研究状态机。

- 风险 D：网络不稳定影响评估。  
  处理：区分“逻辑成功率”和“外部网络成功率”两类指标。

---

## 5. 执行顺序建议（实际开工）

1. 先落地 Phase 0（冻结 profile 契约，最多 3 天）。
2. 立即做 Phase 1（Lite），快速形成第一档可发布能力。
3. 并行推进 Phase 2 中剩余稳定性任务（以 Basic 为主线）。
4. 最后做 Phase 3 的 Full 插件化，再进入 Phase 4 发布。

---

## 6. 里程碑检查点（管理视角）

- Checkpoint A（Phase 0 结束）  
  能否明确回答“每一档到底做什么、不做什么”。

- Checkpoint B（Phase 1 结束）  
  Lite 是否可独立演示并可日更运行。

- Checkpoint C（Phase 2 结束）  
  Basic 是否达到“可持续自动跑”的稳定性。

- Checkpoint D（Phase 3/4 结束）  
  Full 是否真正“加能力不加脆弱性”。

