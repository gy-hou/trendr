# Reference

## Command reference
- Run: `python3 cli.py run --topic "<topic>" --platform <runtime>`
- Status: `python3 cli.py status <project_dir>`
- Resume: `python3 cli.py resume <project_dir> --platform <runtime>`
- Optional hotspots: `python3 cli.py hotspots --project-dir <dir>`
- Evaluation: `python3 eval/scripts/run_eval.py ...`

## Config reference
- Runtime: `--platform` or `TRENDR_PLATFORM`
- Depth: `--depth A|B|C`
- Budget: `--time-budget`
- Discovery thresholds: `--min-papers --target-papers --min-rounds --max-rounds`
- Profile: `--profile lite|basic|full`

## File map
- Core engine: `engine/`
- Runtime adapters: `engine/adapters/`
- State machine coordinator: `engine/state_machine.py`
- Evaluation assets: `eval/`
- Skills: `skills/`
- Tests: `tests/`

## Related docs
- [`docs/USAGE.md`](./USAGE.md)
- [`docs/OUTPUTS.md`](./OUTPUTS.md)
- [`docs/TROUBLESHOOTING.md`](./TROUBLESHOOTING.md)
- [`docs/ENGINE.md`](./ENGINE.md)
- [`docs/HOTSPOTS.md`](./HOTSPOTS.md)
- [`docs/INTEGRATIONS.md`](./INTEGRATIONS.md)
- [`EVALUATION.md`](../EVALUATION.md)
- [`ARCHITECTURE.md`](../ARCHITECTURE.md)
- [`ROADMAP.md`](../ROADMAP.md)
