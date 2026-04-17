# Platform Hotspots

## What it is
Platform Hotspots is an optional signal-intake and context-enrichment module. It is not the core product identity of TrendR.

## When to use it
Use hotspots when you need:
- early topic hints before deep literature discovery
- public-discussion context to complement academic sources
- fast cross-check of whether a theme is emerging outside papers

## Supported sources
TrendR supports two hotspot lanes:
- Browser workflow lane (session-aware, JS-heavy capable)
- CLI Lite lane (HTTP-first, stability-oriented)

Typical sources include:
- Zhihu
- Xiaohongshu
- X
- Reddit
- YouTube
- GitHub Trending
- Hacker News
- Product Hunt

## Setup
Recommended setup boundary:
- Keep hotspots isolated from the core literature-review run state.
- Use dedicated browser/session configuration for login-gated platforms.
- Existing local users can keep `bash scripts/start-chrome-cdp.sh` and continue using the legacy `19222 + cdp-automation` store.
- Only for a new user should you create a separate agent Chrome store, for example: `TRENDR_CDP_USER=<user-key> bash scripts/start-chrome-cdp.sh`.
- Keep browser calls pinned to `profile: cdp`; do not run with an empty browser profile.
- Tell the user they can sign in inside that dedicated agent Chrome to the sites they want TrendR to query later.
- Treat collected hotspot outputs as auxiliary signals, not primary evidence.

## CLI / workflow
Workflow outline:
1. Prepare hotspot configuration and session context.
2. Run hotspots collection in Browser lane or Lite lane.
3. Feed summarized signals into topic refinement or gap-check context.

For CLI commands and runtime-specific steps, use the operational docs and skill files:
- `skills/platform-hotspots/SKILL.md`
- `skills/chrome-cdp-setup/SKILL.md`

## Output artifacts
Typical hotspot outputs:
- `hotspots_raw.json`
- `hotspots_summary.json`
- `hotspots_report.md`

These artifacts are optional sidecar outputs and separate from the core harness artifacts.
They should also record which dedicated CDP user/store was used and remind the user where to log in on first use.

## Limits
- Source availability and page structure can change frequently.
- Login/session state can affect extraction reliability.
- Dedicated agent Chrome stores should only contain low-risk research accounts, not banking or payment accounts.
- Hotspot data reflects discussion dynamics, not citation-grade evidence.
