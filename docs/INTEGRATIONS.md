# Integrations

## Runtime adapters
TrendR core orchestration is runtime-agnostic and can be connected through thin adapters.

Current adapter-facing boundary:
- state machine owns control logic
- adapter owns platform-specific dispatch/IO behavior
- file contracts remain stable across runtimes

## External tools
External tools are optional and used to extend surrounding workflows, not redefine core identity.

Common integration roles:
- retrieval/search augmentation
- bibliography/reference workflow augmentation
- storage/archive or workspace integration

## Integration boundaries
Integration boundary rules:
- core remains `recoverable literature review harness`
- integrations are optional and replaceable
- sidecar modules must not change core state-machine semantics
- verification and artifact contracts stay authoritative in the core loop

## Planned integrations
Planned direction focuses on engineering cleanliness rather than feature sprawl:
- cleaner adapter contracts and capability detection
- deeper runtime parity across supported platforms
- optional connectors for external retrieval/bibliography pipelines
- optional trend-intake connectors with strict sidecar boundaries
