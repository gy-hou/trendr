---
description: "Resume a paused or failed TrendR run"
argument-hint: "<project-dir>"
allowed-tools: Bash, Read, Write, Agent
---

1. Validate:
   - `<project-dir>` is provided in `$ARGUMENTS`.
   - `<project-dir>/run_state.json` exists and `version == 2`.

2. Invoke:
   ```
   Bash: TRENDR_PLATFORM=claude-code TRENDR_CC_MODE=native python {{repo_root}}/cli.py resume <project-dir> --platform claude-code
   ```

3. Poll `<project-dir>/claude_code_dispatch.jsonl` and satisfy ops exactly like `/tr research` (step 5):
   - `op=agent` → `Agent` tool → write completion
   - `op=webfetch` → `WebFetch` → write completion
   - `op=bash` → `Bash` → write completion

4. Continue until `run_state.json` reaches terminal state.

5. Summarize outcome: final state, artifacts written, any `verify.json` issues.
