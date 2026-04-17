---
description: "TrendR dispatcher — run research, hotspots, status, resume, template"
argument-hint: "<subcommand> ..."
allowed-tools: Bash
---

Route `$ARGUMENTS` first token to the matching subcommand:

| Subcommand | Alias | Description |
|-----------|-------|-------------|
| research | run, 研究 | Full literature review pipeline |
| hotspots | hot, 热点 | Cross-platform AI hotspot collection |
| status | — | Show latest run status |
| resume | — | Resume a paused or failed run |
| template | — | Initialize hotspots template |

If `$ARGUMENTS` is empty or equals `help`, print the table above and exit.

Otherwise, read `.claude/commands/tr/<subcommand>.md` and execute it with the remaining `$ARGUMENTS`.
