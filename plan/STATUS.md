# TrendR → Claude Code 迁移状态

最后更新：2026-04-17 by phase-8

| Phase | 状态 | commit | 备注 |
|-------|------|--------|------|
| 0 | 已完成 | — | 审计产出 `plan/inventory.md` |
| 1 | 已完成 | — | `engine/adapters/claude_code.py`，cli routing，13 tests green |
| 2 | 已完成 | — | `skills/*/claude-code.md` × 8，Runtime Router 更新，test_skill_contracts 扩展 |
| 3 | 已完成 | — | `agents/*/claude-code.md` × 4 + `CONTRACT.md` × 4 |
| 4 | 已完成 | — | `runtimes/claude-code/commands/` 6 个模板 + `render-commands.sh` |
| 5 | 已完成 | — | installer 分离，plugin.json，dispatcher |
| 6 | 已完成 | — | 3 hooks + `engine/recovery/claude_code_resume.py` + `settings.json.example`，19 tests green |
| 7 | 已完成 | — | 5 新测试文件 + snapshots + CI workflow，239 tests green |
| 8 | 已完成 | — | CC 为主 runtime，优先级翻转，docs/README/ARCH/ROADMAP 更新，v2.1.0 |

## 遗留 TODO

- (empty)

## 回滚指引

- phase N 回滚：`git revert <sha>`，再把 `STATUS.md` 表里该 phase 的状态改回"待开始"。
