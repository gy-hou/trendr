# Outputs

## Core artifacts
- `candidates.csv`: discovery candidate pool.
- `matrix.csv`: structured analysis matrix.
- `gap_report.md`: coverage gap signal and loop-back basis.
- `review.md`: final review content.
- `verify.json`: independent verification report.

## State files
- `run_state.json`: machine-readable state, history, counters.
- `progress.md`: human-readable progress snapshot.
- `heartbeat.json`: liveness and stage heartbeat.
- `resume_request.json`: watchdog-triggered resume request.

## Verification outputs
- `verify.json.pass`: pass/fail decision.
- `verify.json.issues`: issue list for fix rounds.
- `verify.json.checks`: per-check breakdown.

## Artifact meanings
- DISCOVERY completion depends on `candidates.csv`.
- ANALYSIS completion depends on `notes/` and `matrix.csv`.
- GAP_CHECK depends on `gap_report.md`.
- WRITING depends on `review.md` and `references.bib`.
- VERIFY depends on `verify.json`.

## Where to inspect failures
- First check `run_state.json.current_state`.
- Then inspect `progress.md` and `heartbeat.json` for stall signals.
- Use `logs/latest.log` for execution details.
- For verification failures, inspect `verify.json` directly.
