---
description: "Collect cross-platform AI hotspots via TrendR Lite"
argument-hint: "[--topic \"<label>\"] [--per-source-limit N]"
allowed-tools: Bash, Read, Write, WebFetch, WebSearch, Agent
---

Run TrendR Lite hotspots:

1. Parse `$ARGUMENTS`. Default topic = "AI agents and LLM ecosystem".
   Optional: `--per-source-limit` (default 20).

2. Invoke:
   ```
   Bash: TRENDR_PLATFORM=claude-code python {{repo_root}}/cli.py hotspots <flags>
   ```

3. For JS-heavy sources the runner may request page evaluations.
   In Claude Code, use this priority:
   - MCP chrome server (`mcp__chrome__navigate` + `mcp__chrome__evaluate`)
   - `WebFetch` (static content / JSON APIs)
   - `WebSearch`
   - Mark the source `skipped_with_reason: "JS rendering unavailable"`

4. Read `skills/platform-hotspots/claude-code.md` for per-platform extraction instructions.

5. After completion, summarize top items per platform from the output files:
   `<project_dir>/hotspots_summary.md` and `<project_dir>/hotspots_report.md`.
