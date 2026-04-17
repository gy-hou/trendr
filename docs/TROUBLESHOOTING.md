# Troubleshooting

## Common failure cases
- Run stalls in a state without transition.
- Required artifacts are missing.
- Verifier does not pass after writing.
- Runtime/adapter dispatch errors.

## Resume and recovery
- Check `run_state.json.status` and `current_state`.
- Check `heartbeat.json.updated_at` freshness.
- Resume command:
```bash
python3 cli.py resume <project_dir> --platform <runtime>
```
- If `resume_request.json` exists, watchdog has requested a recovery retry.

## Missing artifacts
- Missing `candidates.csv`: DISCOVERY likely incomplete.
- Missing `matrix.csv` or `notes/`: ANALYSIS failed or fallback incomplete.
- Missing `gap_report.md`: GAP_CHECK failed.
- Missing `review.md`: WRITING failed.
- Missing `verify.json`: VERIFY failed.

Inspection order:
- `run_state.json`
- `progress.md`
- `logs/latest.log`

## Verification failures
- Open `verify.json` and inspect `pass`, `issues`, `checks`.
- Fix citation/claim/taxonomy issues in review/reference artifacts.
- Resume or rerun after fixes.
- If fix rounds reached the cap, inspect `run_state.json.fix_rounds`.

## Adapter/runtime issues
- Check CLI stderr and adapter logs first.
- Check `heartbeat.json` and `run_state.json` for timeout/stall pattern.
- Explicitly set `--platform` to avoid runtime auto-detection mismatch.
- If runtime-specific path fails, validate with `--platform cli` first.
