---
description: "Show status of the latest TrendR run"
argument-hint: "[project-dir]"
allowed-tools: Bash, Read
---

1. If `$ARGUMENTS` is empty, find the latest project directory via:
   ```
   Bash: ls -td ~/research/*/run_state.json 2>/dev/null | head -1
   ```
   Use the parent directory of that file as `<project-dir>`.

2. If `$ARGUMENTS` provides a path, use it as `<project-dir>`.

3. Invoke:
   ```
   Bash: python {{repo_root}}/cli.py status <project-dir>
   ```

4. Read and display:
   - Last 20 lines of `<project-dir>/progress.md` (if it exists)
   - Contents of `<project-dir>/heartbeat.json` (if it exists)
   - `current_state` and `status` fields from `<project-dir>/run_state.json`
