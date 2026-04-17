# TrendR Engine

## Goal
The engine layer exists to provide control and reliability for the literature-review pipeline. It is not a feature layer.

## Modularization scope
TrendR engine is split into 5 responsibility groups:

1. `engine/states/`
- State constants
- Agent bindings
- Timeout and threshold configuration

2. `engine/transitions/`
- Guard conditions for exits
- Transition policies (gap loop, verify write-back)
- State-to-state rule dispatch

3. `engine/executors/`
- Per-phase execution entrypoints:
  - discovery
  - analysis
  - gap_check
  - writing
  - verify
  - orchestrator-owned init/done

4. `engine/artifacts/`
- Canonical artifact paths
- Artifact schemas
- File IO helpers
- File-contract validation adapter

5. `engine/recovery/`
- Heartbeat hooks
- Resume request handling
- Retry bookkeeping
- Watchdog wiring

## Coordinator contract (`engine/state_machine.py`)
`ResearchStateMachine` should be a thin coordinator that only does:
- load current state
- evaluate transition guard
- invoke executor
- persist state updates
- trigger recovery hooks

Target public API:
- `step()`
- `run()`
- `resume()`

## Migration order
To reduce risk, migration follows this sequence:
1. Extract state constants and config (`engine/states/`)
2. Extract transition rules and guards (`engine/transitions/`)
3. Extract artifact paths/contracts (`engine/artifacts/`)
4. Extract recovery logic (`engine/recovery/`)
5. Extract executor implementations (`engine/executors/`)

## Current phase
Current repository state is Phase 1-plus scaffolding:
- `engine/states/` is active and imported by `engine/state_machine.py`
- `step()/run()/resume()` coordinator API is available
- `transitions/`, `artifacts/`, `recovery/`, `executors/` directories are scaffolded for incremental extraction without behavior break

## Non-goals
- No new product features in engine modularization
- No change in product positioning
- No change in research pipeline semantics
