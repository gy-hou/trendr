# TrendR → Claude Code 迁移计划（分离 + 休眠）

> 目标：把 TrendR 升级为 **Claude Code + OpenClaw 双 runtime 共存**，后续 Claude Code 成为默认。
> 指导原则：**分离式目录 + 运行时休眠**。共享文件只写一份，运行时专属文件各住各的子目录；激活哪个 runtime，另一份自动闲置。
> 执行者：Sonnet 4.6（在 Claude Code 环境）。

## 关键概念

所有 phase 遵循 **[`plan/structure.md`](./structure.md)** — 那是目录约定的唯一权威。

一句话总结：
- `skills/<name>/` ← `SKILL.md`（共享）、`openclaw.md`（OpenClaw 指令）、`claude-code.md`（Claude Code 指令）
- `agents/<name>/` ← `CONTRACT.md`（共享）、`SOUL.md`（OpenClaw）、`claude-code.md`（Claude Code）
- `runtimes/<runtime>/` ← 该 runtime 专属的 installer / hooks / commands / plugin 清单
- `engine/` ← 完全共享（Python 状态机与 adapter）
- `.claude/`、`.claude-plugin/` ← 安装产物，不是权威源；installer 从 `runtimes/claude-code/` 生成或软链

这样达成的效果：
- OpenClaw 跑时只读 `SOUL.md + skills/*/SKILL.md + skills/*/openclaw.md`，对 `claude-code.md` 视而不见。
- Claude Code 跑时只读 `.claude/agents/*.md + skills/*/SKILL.md + skills/*/claude-code.md`，对 `openclaw.md` 视而不见。
- 删除任一 runtime 的东西 = 删除对应 `runtimes/<name>/` 和各 skill 下的 `<name>.md`；另一边零影响。

## 执行顺序

| Phase | 文件 | 产出 | 触动谁 |
|-------|------|------|-------|
| 0 | [`phase0.md`](./phase0.md) | 差距 inventory + STATUS 追踪表 | 零代码改动 |
| 1 | [`phase1.md`](./phase1.md) | `engine/adapters/claude_code.py` + 路由 + 单测 | 只加新 adapter，OpenClaw 不动 |
| 2 | [`phase2.md`](./phase2.md) | `skills/<name>/claude-code.md` ×8（可选加 `openclaw.md`）+ SKILL.md Runtime Router | 新建兄弟文件为主 |
| 3 | [`phase3.md`](./phase3.md) | `agents/<name>/claude-code.md` ×4（可选 CONTRACT.md） | 新建兄弟文件，SOUL.md 不动 |
| 4 | [`phase4.md`](./phase4.md) | `runtimes/claude-code/commands/` 5 个 slash 模板 | 全新目录 |
| 5 | [`phase5.md`](./phase5.md) | 拆 `install.sh` → 顶层 dispatch + `runtimes/<runtime>/install.sh` × 2；`runtimes/claude-code/plugin.json` | 顶层 installer 变 dispatcher |
| 6 | [`phase6.md`](./phase6.md) | `runtimes/claude-code/hooks/` + `settings.json.example` + `engine/recovery/claude_code_resume.py` | 新增 hooks 目录 |
| 7 | [`phase7.md`](./phase7.md) | 单测 / 契约测试 / e2e smoke / CI workflow | 测试层 |
| 8 | [`phase8.md`](./phase8.md) | runtime 优先级翻转、README/ARCHITECTURE 切 Claude Code first、v2.1.0 | 最后一步 |

## 通用规则（全 phase 适用）

1. **绝不删除现有 OpenClaw 资产**。本次迁移是 "新增 + 分离"，不是替换。phase 8 之前 `./install.sh`（无 flag）默认 OpenClaw 行为不变。
2. **权威源在仓库里；`.claude/` 是产物**。Claude Code 原生路径（`.claude/agents/`、`.claude/commands/`、`.claude-plugin/plugin.json`）统一由 `runtimes/claude-code/install.sh` 生成或软链，不手工编辑。
3. **兄弟文件格式**：skill 和 agent 的 runtime-specific 兄弟文件（`openclaw.md` / `claude-code.md`）顶部必须写 `> 本文件仅在 <runtime> runtime 下被加载；其他 runtime 请读 sibling。`
4. **SKILL.md Runtime Router**：见 `structure.md §3.1`，每个 skill 顶部统一格式。
5. **路径/命名**：文件与目录名用 `claude-code` 连字符；Python 模块例外用 `claude_code`；runtime canonical 值在 `engine/runtime.py`。
6. **每完成一个 phase**：更新 `plan/STATUS.md`（表格 + 遗留 TODO + 验收回执）。
7. **git 提交**：一 phase 一 commit 或一 PR，标题 `phase-N: <short summary>`，描述引用对应 `plan/phaseN.md`。
8. **测试门槛**：phase 1/6/7 需通过 `python -m pytest tests/ -q`；phase 2/3/4/5 需通过 `python -c "from engine.state_machine import ResearchStateMachine"` 冒烟 + `python cli.py --help` 零退出。

## Sonnet 4.6 执行约定

- 每次只做一个 phase，开始前把 `plan/structure.md` 和当前 phase 文件**全文读完**。
- 按 phase 内 "前置 → 步骤 → 验收 → 风险回滚" 顺序推进，不跳步。
- 实现中发现与计划冲突（如现有文件结构已经不一致），先登记到 `plan/STATUS.md` 的"偏差记录"小节，按最小必要改动推进，不要跨 phase 改。
- `plan/` 目录以外的"计划性文档"不动，但允许实现中更新 `STATUS.md`。

## 风险控制

- 单 phase 回滚：`git revert <phase-commit>`，再把 `STATUS.md` 对应行改回 "待开始"。
- 共享文件（`install.sh`、`engine/runtime.py`、`cli.py`）的改动 phase（1、5、8）必须在 PR 描述保留改动前后 diff，便于对照。
- phase 8 必须在 phase 7 测试全绿后才启动；测试没过不翻转 runtime 优先级。
