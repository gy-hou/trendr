---
description: "Run a full TrendR literature-review pipeline"
argument-hint: "\"<topic>\" [--depth A|B|C] [--profile basic|full] [--project-dir PATH]"
allowed-tools: Bash, Read, Write, Agent
---

Run TrendR's v2 state machine on the topic in `$ARGUMENTS`.

Steps (execute literally):

1. Parse `$ARGUMENTS`: first quoted/positional token = topic. Optional flags:
   `--depth` (default B), `--profile` (default basic), `--project-dir`, `--time-budget`.

2. Ensure env: `TRENDR_PLATFORM=claude-code` and set `TRENDR_CC_MODE=native`.

3. Determine project directory:
   - If `--project-dir` provided, use it.
   - Otherwise: `~/research/<slug-of-topic>/` where slug replaces spaces with `-` and lowercases.

4. Start the state machine via Bash (background):
   ```
   Bash: TRENDR_PLATFORM=claude-code TRENDR_CC_MODE=native python {{repo_root}}/cli.py run \
     --topic "<topic>" --depth <DEPTH> --profile <PROFILE> \
     --project-dir <DIR> --platform claude-code --no-watchdog
   ```

5. Poll `<DIR>/claude_code_dispatch.jsonl` for new lines. For every new dispatch record:
   - `op=agent` → spawn the named subagent via `Agent` tool using `subagent_type=<agent_id>`,
     then write `<DIR>/claude_code_completions/<handle>.json` with `{"handle":"<h>","status":"completed","output":"<result>","ended_at":"<ISO>"}`.
   - `op=webfetch` → call `WebFetch(url=..., prompt="return raw body")` and write completion.
   - `op=bash` → call `Bash(command=...)` and write completion.

6. Continue polling until `<DIR>/run_state.json` shows `status` = `completed` | `failed` | `done`.

7. Read `<DIR>/run_state.json` and report final state + artifacts
   (`review.md`, `references.bib`, `matrix.csv`, `verify.json`).

8. If `verify.json` exists and `overall_status != "passed"`, summarize the `issues` array.

Do not fabricate artifacts. Do not skip dispatch polling — the state machine
depends on Claude Code completing each dispatched op.
