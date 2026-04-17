# TrendR Roadmap

## Near-term
Research quality:
- better discovery ranking and dedup quality
- stronger citation checking in verifier workflows
- improved gap analysis consistency
- expand evaluation coverage for fixed topic sets

Control-plane maturity:
- stabilize step/run/resume coordinator boundaries
- complete state_machine modular extraction into dedicated packages
- strengthen recovery policies for interrupted/stale runs
- improve run-level observability signals and summaries

Ecosystem / integrations:
- harden runtime adapter contracts
- keep hotspot intake isolated as optional extension
- improve integration docs and boundary checks for external tools

## Mid-term
Research quality:
- improve high-relevance recall across domains
- strengthen claim-to-evidence traceability
- broaden evaluation datasets and failure-case taxonomy

Control-plane maturity:
- multi-run scheduling primitives
- planner/memory interface boundaries for orchestration
- richer retry and fallback policy controls
- structured observability export for run diagnostics

Ecosystem / integrations:
- deeper OpenClaw runtime alignment
- cleaner portability for codex/claude-code/cli adapters
- optional bibliography/retrieval connectors under strict contract boundaries

## Long-term
Research quality:
- robust quality controls for large-scale recurring reviews
- continuous evaluation loops tied to gold-set refresh workflows

Control-plane maturity:
- mature control-plane semantics for long-horizon research runs
- policy-driven orchestration with auditable state transitions

Ecosystem / integrations:
- modular integration ecosystem around the core harness
- optional signal-intake connectors with explicit risk boundaries

## Out of scope
- Repositioning TrendR as a generic content generator
- Treating hotspots or integrations as a second primary product
- Replacing core file contracts with opaque ad-hoc outputs
- Shipping integrations that bypass verifier or recovery controls
