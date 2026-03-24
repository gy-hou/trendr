---
name: trendr-watchdog
description: 运行时监督器。监控 run_status/progress/log 活跃度，发现卡住后自动向 owner session 注入断点续跑指令。
metadata: {"openclaw": {}}
---

# TrendR Watchdog Skill

用于修复多 agent 运行时的“会话分裂/提前停转”问题：
- 子会话完成但主会话未续接
- 状态文件长时间不刷新
- Phase 文件已产出但 orchestration 没推进

> 使用前完整阅读本文件。
> 核心守夜逻辑在 `supervisor.py`；`watchdog.py` 保留为兼容旧启动命令的入口。

## 前置条件

- `python3` 可用
- `openclaw` CLI 可用
- 当前任务目录使用 `~/research/[PROJECT]/`

## 启动流程（建议）

1. 启动前先拿当前主会话 ID，写入 `run_status.json.owner_session_id`
2. 启动 watchdog 常驻进程（后台）
3. 任务结束（completed/failed）后，停止 watchdog

## 启动命令模板

```bash
exec: PROJECT="[PROJECT]" && RUN_ID="[RUN_ID]" && SESSION_ID="[OWNER_SESSION_ID]" && \
  mkdir -p "$HOME/research/$PROJECT/logs" && \
  nohup python3 "$HOME/.openclaw/workspace/skills/trendr-watchdog/supervisor.py" \
    --project "$PROJECT" \
    --run-id "$RUN_ID" \
    --session-id "$SESSION_ID" \
    --poll-sec 60 \
    --idle-timeout-sec 600 \
    --phase-mismatch-grace-sec 180 \
    --artifact-complete-grace-sec 1800 \
    --resume-cooldown-sec 300 \
    --heartbeat-sec 300 \
    --max-resume 12 \
    >> "$HOME/research/$PROJECT/logs/watchdog.out" 2>&1 & \
  echo $! > "$HOME/research/$PROJECT/logs/watchdog.pid"
```

默认行为：
- 每 60 秒轮询一次
- 10 分钟无活动触发自动续接
- 若检测到“文件已到下一阶段、phase 未推进”，3 分钟后即触发续接
- 若 `review.md + references.bib` 稳定 30 分钟，视为研究已完成并停止守夜
- 每 5 分钟写一条 watchdog 心跳到 run log

## 停止命令模板

```bash
exec: PROJECT="[PROJECT]" && PID_FILE="$HOME/research/$PROJECT/logs/watchdog.pid" && \
  if [ -f "$PID_FILE" ]; then kill "$(cat "$PID_FILE")" 2>/dev/null || true; fi
```

## 产物

- `~/research/[PROJECT]/logs/supervisor_[RUN_ID].json`：监督状态（注入次数、最近注入原因、停止原因）
- `~/research/[PROJECT]/logs/overnight_report_[RUN_ID].md`：夜间守护报告（停机原因、当前 phase、建议下一步）
- `~/research/[PROJECT]/logs/overnight_report.md`：最新一份夜间守护报告镜像
- `~/research/[PROJECT]/logs/watchdog.out`：watchdog 运行输出
- `~/research/[PROJECT]/logs/[RUN_ID].log`：追加 watchdog 心跳/注入事件
- `~/research/[PROJECT]/logs/latest.log`：自动同步

## 断点续接判定（幂等）

- `candidates.csv + search_log.md` 存在：判定 Phase 1 可推进
- `matrix.csv + notes/*.md` 存在：判定 Phase 2 可推进
- `review.md + references.bib` 存在：判定可直接收尾

若文件已存在，续接指令会要求“跳过重复工作”。
