# TrendR — Future: Claude Code 每日 Cron 自动化方案

> 本文档描述如何让 TrendR 在 Claude Code runtime 下实现每日定时、无人值守的自动化运行。
> 当前状态：**设计阶段**（v2.1.x 预期实现）。已有基础设施：SessionStart/Stop/SubagentStop hooks、dispatch-completion loop、`claude -p` 无头模式。

---

## 1. 两种自动化路径对比

| 路径 | 适用场景 | 成熟度 | 备注 |
|------|---------|--------|------|
| **OpenClaw cron**（当前可用） | 长期稳定、无人值守、多任务并行 | ✅ 生产可用 | `supervisor.py` 已内置看门狗 |
| **Claude Code headless**（本文目标） | 统一到 Claude Code 工具链、利用 subagent hooks | 🚧 设计中 | 依赖 `claude -p` 非交互模式 |

---

## 2. Claude Code 无头模式原理

Claude Code 支持通过 `claude -p "<prompt>"` 以非交互方式执行一次性任务：

```bash
claude -p "Run TrendR hotspots scan, write results to ~/research/daily-hotspots/"
```

结合 `--output-format json` 和 `--max-turns` 参数可控制行为：

```bash
claude \
  --output-format json \
  --max-turns 50 \
  -p "$(cat scripts/prompts/daily_hotspots.txt)"
```

关键特性：
- 继承 `~/.claude/settings.json` 的 hooks 配置 → SessionStart/Stop 仍会触发
- `CLAUDE_CODE_*` 环境变量在子进程中可见 → `ClaudeCodeAdapter` 自动选 native mode
- 退出码 0 = 成功，非 0 = 错误，可被 cron/launchd 捕获
- stdout 为 JSON（`--output-format json`）或纯文本，可 pipe 到日志

---

## 3. 每日定时方案

### 3.1 macOS launchd（推荐，macOS）

launchd 比 cron 更可靠，支持网络依赖、失败重试、日志持久化。

**Step 1** — 创建 prompt 脚本：

```bash
# scripts/prompts/daily_research.txt
Run TrendR daily research automation:
1. Read skills/platform-hotspots/claude-code.md
2. Collect today's AI hotspots from GitHub Trending, Hacker News, Reddit r/MachineLearning
3. Write report to ~/research/daily-$(date +%Y-%m-%d)/hotspots_report.md
4. If any hotspot score > 4, run /tr research "<top topic>" --depth A --time-budget 10
5. Write run_state.json with status=completed when done
```

**Step 2** — 创建 launchd plist：

```xml
<!-- ~/Library/LaunchAgents/ai.trendr.daily.plist -->
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>ai.trendr.daily</string>

  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>-c</string>
    <string>
      cd /path/to/trendr && \
      export TRENDR_PLATFORM=claude-code && \
      export TRENDR_CC_MODE=native && \
      claude --output-format json --max-turns 80 \
        -p "$(cat scripts/prompts/daily_research.txt)" \
        >> ~/research/logs/daily-$(date +%Y-%m-%d).log 2>&1
    </string>
  </array>

  <key>StartCalendarInterval</key>
  <dict>
    <key>Hour</key>   <integer>8</integer>
    <key>Minute</key> <integer>30</integer>
  </dict>

  <!-- 网络可用后才运行 -->
  <key>NetworkState</key>
  <true/>

  <key>StandardOutPath</key>
  <string>/Users/mac/.trendr/launchd-daily.log</string>
  <key>StandardErrorPath</key>
  <string>/Users/mac/.trendr/launchd-daily-err.log</string>

  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key>
    <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
    <key>HOME</key>
    <string>/Users/mac</string>
  </dict>
</dict>
</plist>
```

**Step 3** — 加载：

```bash
launchctl load ~/Library/LaunchAgents/ai.trendr.daily.plist
launchctl start ai.trendr.daily     # 立即测试
launchctl list | grep trendr        # 查看状态
```

### 3.2 Linux cron（服务器/CI）

```cron
# crontab -e
# 每天 08:30 运行
30 8 * * * cd /path/to/trendr && \
  TRENDR_PLATFORM=claude-code \
  TRENDR_CC_MODE=native \
  claude --output-format json --max-turns 80 \
    -p "$(cat scripts/prompts/daily_research.txt)" \
    >> ~/research/logs/daily-$(date +\%Y-\%m-\%d).log 2>&1

# 每周一 09:00 运行深度综述
0 9 * * 1 cd /path/to/trendr && \
  TRENDR_PLATFORM=claude-code \
  claude -p "Run TrendR full literature review on topic: $(cat ~/.trendr/weekly_topic.txt) --depth B" \
    >> ~/research/logs/weekly-$(date +\%Y-\%m-\%d).log 2>&1
```

### 3.3 GitHub Actions（云端，跨设备）

```yaml
# .github/workflows/daily_research.yml
name: TrendR Daily

on:
  schedule:
    - cron: '30 0 * * *'   # UTC 00:30 = 北京时间 08:30
  workflow_dispatch:         # 手动触发

jobs:
  daily-hotspots:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install Claude Code CLI
        run: npm install -g @anthropic-ai/claude-code

      - name: Authenticate
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: echo "authenticated via API key"

      - name: Run daily hotspots
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          TRENDR_PLATFORM: claude-code
          TRENDR_CC_MODE: subprocess   # CI 环境用 subprocess mode
        run: |
          claude --output-format json --max-turns 60 \
            -p "$(cat scripts/prompts/daily_research.txt)"

      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        with:
          name: daily-research-${{ github.run_id }}
          path: ~/research/daily-*/
```

---

## 4. SessionStart Hook 与 Resume 机制

每次 `claude` 启动（含 `claude -p` 无头调用）都会触发 `SessionStart` hook：

```
claude -p "..." 启动
    │
    ▼ SessionStart hook 执行
    │   → 扫描 ~/research/*/run_state.json
    │   → 找到 status=paused/running 的 run
    │   → 注入 additionalContext: "TrendR: 1 run pending. /tr resume <dir>"
    ▼
claude 接收 context，自动恢复上次中断的 run
```

这意味着：
- 机器重启 / 手动中断后，下次定时触发会自动 resume 上次未完成的任务
- 无需额外的 resume 脚本
- `Stop` hook 写 `heartbeat.json`，记录最后状态

---

## 5. 完整的每日自动化 Prompt 模板

存放于 `scripts/prompts/` 目录，供 cron/launchd 调用：

### `scripts/prompts/daily_hotspots.txt`

```
You are running TrendR automated daily hotspots collection.
Runtime: claude-code. Mode: unattended.

Steps:
1. Read skills/platform-hotspots/claude-code.md
2. Start Chrome CDP: bash scripts/start-chrome-cdp.sh
3. Collect hotspots from: GitHub Trending, Hacker News, Reddit r/MachineLearning
4. For JS-heavy sites (Zhihu, X): use scripts/cdp_browse.py with CDP
5. Write ~/research/daily-YYYY-MM-DD/hotspots_report.md
6. Write ~/research/daily-YYYY-MM-DD/run_state.json with status=completed
7. Exit cleanly.

Do not ask for confirmation. Do not wait for user input.
If any source fails, mark skipped_with_reason and continue.
```

### `scripts/prompts/weekly_review.txt`

```
You are running TrendR automated weekly literature review.
Runtime: claude-code. Mode: unattended.
Topic: read from ~/.trendr/weekly_topic.txt

Steps:
1. Read skills/paper-scout/claude-code.md
2. Search 3 sources via CDP browser (arXiv, HF Papers, Semantic Scholar web)
3. Score and deduplicate candidates, write candidates.csv
4. Read skills/paper-analyzer/claude-code.md — extract notes for top 8 papers
5. Read skills/review-writer/claude-code.md — write review.md
6. Read skills/verifier/claude-code.md — verify top 3 citations, write verify.json
7. Write run_state.json with status=completed

Do not ask for confirmation. Time budget: 20 minutes.
```

---

## 6. 看门狗与失败恢复

### Claude Code 模式下的 watchdog

`engine/watchdog.py` 在检测到 `CLAUDE_CODE_*` 环境变量时进入 **passive mode**（不抢 hook 的工作）：

```python
# engine/watchdog.py
if any(k.startswith("CLAUDE_CODE_") for k in os.environ):
    logger.info("hooks detected, watchdog running in passive mode")
    # 只监控 heartbeat，不主动注入
```

当 heartbeat 超过阈值（默认 10 分钟无更新），watchdog 触发：
1. 写 `run_state.json.status = "paused"`
2. 下次 launchd/cron 触发时，SessionStart hook 发现 pending run 并 resume

### 手动 resume

```bash
# 查看所有 pending runs
python3 cli.py status

# Resume 指定 run
python3 cli.py resume ~/research/marl-trading-2026-04-17 --platform claude-code
# 或在 Claude Code 中：
/tr resume ~/research/marl-trading-2026-04-17
```

---

## 7. 实施路线图

| 阶段 | 内容 | 预计版本 |
|------|------|---------|
| **v2.1.x（现在）** | `claude -p` 手动触发可用；hooks 已部署；SessionStart resume 已工作 | ✅ |
| **v2.2（近期）** | `scripts/prompts/` 目录 + launchd plist 模板提交到仓库 | 🚧 |
| **v2.2（近期）** | `scripts/setup_cron.sh` 一键配置每日任务 | 🚧 |
| **v2.3（中期）** | GitHub Actions workflow 模板（云端无服务器调度） | 🔲 |
| **v2.3（中期）** | 结果自动推送：Telegram / 邮件 / Obsidian daily note | 🔲 |
| **v2.x（长期）** | Marketplace 发布后，`claude /plugin install trendr` + GUI 调度配置 | 🔲 |

---

## 8. 关键限制与风险

| 风险 | 说明 | 缓解 |
|------|------|------|
| `claude -p` token 消耗 | 无头运行每次消耗完整上下文 | 设置 `--max-turns` 上限；Depth A 优先 |
| CDP 浏览器未启动 | cron 启动时 Chrome 可能未运行 | `scripts/start-chrome-cdp.sh` 内置幂等检测 |
| Google Scholar 反爬 | 无真实 Cookie 的 session 被 CAPTCHA 阻断 | 优先 arXiv + HF Papers；GScholar 标 `skipped` |
| arXiv API + 网页双重访问限速 | 同 session 内先调 API 再访网页会被限速 | Depth A 只用网页端（CDP），不调 API |
| 无头模式下 hooks 依赖路径 | `CLAUDE_PLUGIN_ROOT` 未设置时 fallback 到 `$(pwd)` | launchd plist 中显式 `cd /path/to/trendr` |

---

## 参考

- `runtimes/claude-code/settings.json.example` — hooks 配置模板
- `engine/recovery/claude_code_resume.py` — SessionStart context 生成
- `engine/watchdog.py` — passive mode 实现
- `scripts/start-chrome-cdp.sh` — CDP 启动（含 `--remote-allow-origins=*`）
- `scripts/cdp_browse.py` — 统一 CDP 浏览器采集入口
- `docs/CLAUDE_CODE_ADAPTER.md` — dispatch-completion 协议详解
