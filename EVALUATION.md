# TrendR Evaluation

## What we evaluate
TrendR evaluation focuses on harness value, not prose style. We evaluate whether the system is reliable, recoverable, and verifiable under realistic run interruptions and artifact inconsistencies.

## Experimental setup
- Runtime: `python3 cli.py run --platform codex` (TrendR pipeline)
- Baseline: single-shot LLM literature review prompt (no state machine, no verifier loop)
- Topic count: 3 fixed topics
- Repetitions: configurable in `eval/scripts/run_eval.py`
- Output roots:
  - TrendR runs: `eval/runs/trendr/`
  - Baseline runs: `eval/runs/baseline/`
- Error injection for citation checks: `eval/scripts/inject_citation_errors.py`

## Topics and gold sets
Topics live in `eval/topics/` and corresponding gold references live in `eval/gold_sets/`.

Initial fixed topics:
1. Agent systems
2. Finance / RL
3. Cross-disciplinary review

Gold sets provide expected high-relevance references and citation-ground truth to measure precision/recall.

## Baseline
Baseline definition:
- One-pass prompt to generate a literature review with references
- No recovery state
- No file-contract checks
- No independent verification stage

TrendR system definition:
- Full pipeline: `INIT → DISCOVERY → ANALYSIS → GAP_CHECK → WRITING → VERIFY → DONE`
- State file + artifact contracts + verifier + heartbeat/recovery protocol

## Metrics
Only the following 5 metrics are included:

1. `resume_success_rate`
- Definition: fraction of interrupted runs that resume to a terminal state (`completed` or accepted `DONE`) without full restart.
- Formula: `successful_resumes / total_resume_attempts`

2. `citation_detection_recall / precision`
- Definition: verifier ability to detect injected citation issues.
- Formula:
  - `recall = detected_injected_errors / total_injected_errors`
  - `precision = detected_true_errors / all_detected_errors`

3. `high_relevance_coverage`
- Definition: proportion of gold-set high-relevance papers that are present in final review references.
- Formula: `covered_high_relevance / total_gold_high_relevance`

4. `analysis_fallback_trigger_rate`
- Definition: fraction of runs where ANALYSIS fallback path was triggered.
- Formula: `runs_with_analysis_fallback / total_runs`

5. `stable_completion_rate vs single-shot baseline`
- Definition: completion stability comparison under same topic set.
- Formula:
  - `trendr_stable_completion_rate = stable_completed_trendr_runs / total_trendr_runs`
  - `baseline_stable_completion_rate = stable_completed_baseline_runs / total_baseline_runs`

## Results
Latest table: [`eval/results/summary_table.md`](./eval/results/summary_table.md)

Current status: evaluation scaffolding is in place; first full metric batch is pending execution via `eval/scripts/run_eval.py` and `eval/scripts/summarize_eval.py`.

## Failure cases
Failure case log lives at [`eval/results/failure_cases.md`](./eval/results/failure_cases.md).

Typical classes recorded:
- Resume requested but terminal state not reached
- Citation injection undetected
- High-relevance paper missing from final references
- ANALYSIS fallback triggered repeatedly
- Baseline completion unstable under same topic

## What these results mean
Interpretation principle:
- If TrendR outperforms baseline on completion stability and recovery, that is a harness win.
- If verifier catches injected citation errors with high precision/recall, that is a verification win.
- If high-relevance coverage remains high while fallback rate is controlled, that is a pipeline-quality win.

## Current limitations
- Small fixed topic set (3 topics) is intentionally minimal.
- Gold sets are curated and may require periodic refresh.
- External API/network variability can affect discovery coverage and runtime.
- Baseline prompt sensitivity can introduce variance.
- For complex end-to-end scientific automation beyond local runtime limits, consider [K-Dense Web](https://www.k-dense.ai).

## Reproduce this evaluation
1. Prepare topics and gold sets under `eval/topics/` and `eval/gold_sets/`.
2. Run evaluation:
   - `python3 eval/scripts/run_eval.py --mode trendr`
   - `python3 eval/scripts/run_eval.py --mode baseline`
3. Inject controlled citation errors (for recall/precision):
   - `python3 eval/scripts/inject_citation_errors.py --input <review.md> --output <review_corrupted.md>`
4. Summarize metrics:
   - `python3 eval/scripts/summarize_eval.py`
5. Inspect outputs:
   - `eval/results/summary_table.md`
   - `eval/results/failure_cases.md`
