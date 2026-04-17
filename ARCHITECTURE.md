# TrendR v2 — Architecture Specification

> **TrendR is a research-agent harness system, evolving toward a domain-specific agent OS.**
>
> Designed by Claude Opus 4.6. Implementation target: Codex 5.4 as code assistant.
> Date: 2026-04-01

---

## Positioning

TrendR has three layers, built bottom-up:

| Layer | What it is | Status |
|-------|-----------|--------|
| **Workflow** | Search → Analyze → Write review | v1 ✅ done |
| **Harness** | Watchdog, anti-forgetting, file contracts, fallback chains | v1 ✅ done |
| **Agent OS** | Unified runtime, memory, verification, state machine as control plane | v2 🚧 this spec |

v1's shell is a workflow. v1's skeleton is already a harness. v2 turns the harness into a proper control plane — the first real step toward agent OS territory.

We are **not** claiming to be an agent OS yet. We are building the infrastructure that makes that transition possible.

---

## Design Thesis

TrendR v1 proved that **LLM agents need playbooks, not libraries**. But the harness (watchdog, contracts, fallbacks) is welded to OpenClaw's runtime. v2 extracts the harness into a **platform-agnostic engine** so it can be the foundation for whatever runtime comes next.

The core abstraction: a **research state machine** that governs the pipeline. The state machine is pure logic — it doesn't know what platform drives it. Platform-specific code lives in thin adapters that implement a fixed interface.

> **Future direction (not in v2 scope):** Source-level integration with Claude Code to build a true research agent OS. That requires deep coupling with Claude Code internals, not just tool mapping. v2 builds the engine that future integration will wrap.

### What Changes

| Layer | v1 | v2 |
|-------|----|----|
| Orchestration | OpenClaw sessions_spawn hardcoded in SOUL.md | State machine + platform adapters |
| State tracking | run_status.json (ad-hoc schema) | Typed state file with transition log |
| Verification | Self-assessed checklist | Independent verifier agent |
| Skills | Monolithic SKILL.md files | Same files, but read by adapters not agents directly |
| Watchdog | OpenClaw-only supervisor.py | Platform-agnostic heartbeat protocol |

### What Stays

- SKILL.md files as knowledge artifacts (API handbook, extraction selectors, writing templates)
- SOUL.md files as agent personality definitions
- File-based contracts between phases (CSV, MD, BibTeX)
- 9 academic APIs, 9 platform hotspot sources
- Anti-forgetting triple-redundancy pattern

---

## 1. Research State Machine

### 1.1 States

```
                    ┌──────────────────────────────────┐
                    │                                  │
  ┌──────┐    ┌────▼────┐    ┌──────────┐    ┌───────┴──┐    ┌─────────┐    ┌──────────┐    ┌────────┐
  │ INIT │───►│DISCOVERY│───►│ ANALYSIS │───►│ GAP_CHECK │───►│ WRITING │───►│ VERIFY   │───►│ DONE   │
  └──────┘    └────┬────┘    └──────────┘    └───────┬──┘    └─────────┘    └──────────┘    └────────┘
                   │                                 │
                   │              ┌───────────────────┘
                   │              │ (gaps found)
                   └──────────────┘
```

Each state has:
- **Entry condition**: what files/data must exist to enter
- **Exit condition**: what artifacts must exist to leave
- **Responsible agent**: who executes this phase
- **Timeout**: max wall-clock time before escalation

### 1.2 State Definitions

```yaml
states:
  INIT:
    artifacts_in: []
    artifacts_out:
      - run_state.json     # machine-readable state
      - progress.md        # human-readable progress
      - logs/{RUN_ID}.log  # run log
    agent: orchestrator
    timeout_sec: 60
    transitions:
      - to: DISCOVERY
        when: run_state.json exists AND status == "running"

  DISCOVERY:
    artifacts_in:
      - run_state.json
    artifacts_out:
      - candidates.csv     # columns: paper_id, title, authors, year, source, relevance_score, abstract_snippet, url
      - search_log.md      # queries used, per-source hit counts, failures
    agent: paper-scout
    timeout_sec: 900
    transitions:
      - to: ANALYSIS
        when: discovery_rounds >= min_rounds AND row_count >= target_papers
      - to: DISCOVERY          # retry with expanded queries
        when: discovery_rounds < min_rounds OR (row_count < target_papers AND retry_count < max_retries)
      - to: ANALYSIS
        when: retry_count >= max_retries AND row_count >= 1   # force-advance with partial pool

  ANALYSIS:
    artifacts_in:
      - candidates.csv
    artifacts_out:
      - notes/{paper_id}.md   # one per analyzed paper
      - matrix.csv            # columns: paper_id, method, dataset, metric, result, category
    agent: paper-analyzer
    timeout_sec: 1200
    transitions:
      - to: GAP_CHECK
        when: matrix.csv exists AND notes_count >= (relevance_4plus_count * 0.8)

  GAP_CHECK:
    artifacts_in:
      - candidates.csv
      - matrix.csv
      - notes/*.md
    artifacts_out:
      - gap_report.md          # NEW: structured gap analysis (was implicit in v1)
    agent: orchestrator
    timeout_sec: 300
    transitions:
      - to: DISCOVERY           # loop back with new queries
        when: gap_report.coverage_score < threshold AND discovery_rounds < max_rounds
      - to: WRITING
        when: gap_report.coverage_score >= threshold OR discovery_rounds >= max_rounds

  WRITING:
    artifacts_in:
      - matrix.csv
      - notes/*.md
      - gap_report.md
    artifacts_out:
      - review.md
      - references.bib
    agent: orchestrator          # review-lead writes, never delegates
    timeout_sec: 1800
    transitions:
      - to: VERIFY
        when: review.md exists AND references.bib exists

  VERIFY:                        # NEW in v2
    artifacts_in:
      - review.md
      - references.bib
      - candidates.csv
      - matrix.csv
      - notes/*.md
    artifacts_out:
      - verify.json              # structured verification report
    agent: verifier              # NEW agent
    timeout_sec: 600
    transitions:
      - to: WRITING              # fix issues
        when: verify.json.pass == false AND fix_rounds < max_fix_rounds
      - to: DONE
        when: verify.json.pass == true OR fix_rounds >= max_fix_rounds

  DONE:
    artifacts_in:
      - review.md
      - references.bib
      - verify.json
    artifacts_out: []
    agent: orchestrator
    timeout_sec: 60
    transitions: []              # terminal state
```

### 1.3 State File Schema (`run_state.json`)

```jsonc
{
  "version": 2,
  "run_id": "20260401_143000",
  "project": "rl-market-making",
  "status": "running",          // running | completed | failed | paused
  "current_state": "ANALYSIS",
  "params": {
    "topic": "RL multi-agent market making",
    "min_papers": 30,
    "target_papers": 45,
    "min_rounds": 2,
    "max_rounds": 6,
    "depth": "B",               // A | B | C
    "time_budget_min": 60
  },
  "history": [
    {
      "state": "INIT",
      "entered_at": "2026-04-01T14:30:00Z",
      "exited_at": "2026-04-01T14:30:15Z",
      "agent": "orchestrator",
      "result": "ok"
    },
    {
      "state": "DISCOVERY",
      "entered_at": "2026-04-01T14:30:15Z",
      "exited_at": "2026-04-01T14:42:30Z",
      "agent": "paper-scout",
      "result": "ok",
      "metrics": { "candidates_found": 47, "sources_used": 5 }
    }
  ],
  "discovery_rounds": 1,
  "fix_rounds": 0,
  "heartbeat_at": "2026-04-01T14:45:00Z",
  "started_at": "2026-04-01T14:30:00Z",
  "platform": "openclaw"         // openclaw | cli
}
```

### 1.4 File Contracts

Every artifact has a **fixed schema**. Agents produce files; the state machine validates them.

| Artifact | Format | Validation Rule |
|----------|--------|----------------|
| `candidates.csv` | CSV with header | Must have columns: `paper_id,title,authors,year,source,relevance_score,url`. `paper_id` unique. |
| `search_log.md` | Markdown | Must contain at least one `## Source:` section |
| `notes/{id}.md` | Markdown with YAML frontmatter | Frontmatter must include `paper_id`, `title`, `relevance_score` |
| `matrix.csv` | CSV with header | Must have columns: `paper_id,method,dataset,category`. All `paper_id` must exist in candidates.csv |
| `gap_report.md` | Markdown | Must contain `coverage_score:` line (float 0-1) |
| `review.md` | Markdown | Must contain `## References` or link to references.bib |
| `references.bib` | BibTeX | Valid BibTeX syntax. Every `\cite{}` in review.md has matching entry |
| `verify.json` | JSON | Must have `pass` (bool), `issues` (array), `citation_check`, `claim_check` |

---

## 2. Platform Adapter Layer

The adapter is the **only platform-specific code**. Everything above it is portable.

### 2.1 Adapter Interface

```python
from abc import ABC, abstractmethod
from typing import Optional
from pathlib import Path

class PlatformAdapter(ABC):
    """Bridge between the state machine and a specific LLM platform."""

    @abstractmethod
    def spawn_agent(self, agent_id: str, task: str, timeout_sec: int) -> str:
        """Dispatch a sub-agent. Returns a handle/session ID."""
        ...

    @abstractmethod
    def await_agent(self, handle: str, poll_sec: int = 10) -> dict:
        """Block until agent completes. Returns {status, output}."""
        ...

    @abstractmethod
    def http_get(self, url: str, headers: Optional[dict] = None) -> dict:
        """Fetch a URL. Returns {status_code, body, headers}."""
        ...

    @abstractmethod
    def read_file(self, path: Path) -> str:
        """Read a file from the project directory."""
        ...

    @abstractmethod
    def write_file(self, path: Path, content: str) -> None:
        """Write a file to the project directory."""
        ...

    @abstractmethod
    def run_shell(self, command: str, timeout_sec: int = 30) -> dict:
        """Execute a shell command. Returns {exit_code, stdout, stderr}."""
        ...

    @abstractmethod
    def send_heartbeat(self, state: dict) -> None:
        """Update the platform-specific heartbeat/progress indicator."""
        ...

    @abstractmethod
    def browser_eval(self, js: str, url: Optional[str] = None) -> str:
        """Execute JavaScript in a browser context (for platform-hotspots)."""
        ...

    @property
    @abstractmethod
    def platform_name(self) -> str:
        """Return platform identifier: 'openclaw' | 'claude-code' | 'codex' | 'cli'"""
        ...
```

### 2.2 Adapter Implementations

#### ClaudeCodeAdapter (v2.1.0 — primary runtime)
```
spawn_agent  → write to claude_code_dispatch.jsonl; await claude_code_completions/<handle>.json
http_get     → WebFetch tool (native) or subprocess curl
run_shell    → Bash tool (native) or subprocess
browser_eval → MCP browser tools
read_file    → Read tool / Path.read_text()
write_file   → Write tool / Path.write_text()
heartbeat    → atomic write to heartbeat.json (no stdout)
```
See `docs/CLAUDE_CODE_ADAPTER.md` for the full dispatch-completion protocol.

#### OpenClaw Adapter (legacy — fully supported)
```
spawn_agent  → sessions_spawn + sessions_yield
http_get     → web_fetch
run_shell    → exec:
browser_eval → openclaw browser --browser-profile cdp eval "..."
read_file    → read
write_file   → write
heartbeat    → update run_status.json + progress.md
```

#### CLI Adapter (standalone, no LLM platform)
```
spawn_agent  → subprocess.Popen with LLM API calls
http_get     → requests.get / urllib.request
run_shell    → subprocess.run
browser_eval → playwright sync API
read_file    → Path.read_text()
write_file   → Path.write_text()
heartbeat    → print + write run_state.json
```

#### Claude Code Integration (shipped in v2.1.0)

The `ClaudeCodeAdapter` provides full source-level integration:
- **native mode**: dispatch via `claude_code_dispatch.jsonl`, completion via `claude_code_completions/<handle>.json`
- **subprocess mode**: delegates to `CLIAdapter` via `claude -p`
- **Hooks**: `SessionStart` scans pending runs; `Stop` writes terminal heartbeat; `SubagentStop` unblocks the polling loop
- **Plugin manifest**: `runtimes/claude-code/plugin.json` with 4 agents + 5 slash commands

See `docs/CLAUDE_CODE_ADAPTER.md` for the full specification.

### 2.3 Adapter Selection

```python
def get_adapter(platform: str = "auto") -> PlatformAdapter:
    if platform == "auto":
        platform = detect_platform()
    adapters = {
        "claude-code": ClaudeCodeAdapter,   # primary (v2.1.0+)
        "openclaw": OpenClawAdapter,        # legacy support
        "cli": CLIAdapter,
        "codex": CLIAdapter,
    }
    if platform not in adapters:
        raise ValueError(f"Unknown platform: {platform}. Available: {list(adapters.keys())}")
    return adapters[platform]()

def detect_platform() -> str:
    """Detect which platform we're running on."""
    if os.environ.get("OPENCLAW_SESSION_ID"):
        return "openclaw"
    return "cli"  # default: standalone mode
```

---

## 3. State Machine Engine

The engine is **pure Python, no LLM dependency**. It reads `run_state.json`, checks transition conditions, and tells the adapter what to do next.

### 3.1 Engine Core

```python
class ResearchStateMachine:
    def __init__(self, project_dir: Path, adapter: PlatformAdapter):
        self.project_dir = project_dir
        self.adapter = adapter
        self.state = self.load_state()

    def load_state(self) -> dict:
        state_file = self.project_dir / "run_state.json"
        if state_file.exists():
            return json.loads(state_file.read_text())
        return None

    def save_state(self):
        (self.project_dir / "run_state.json").write_text(
            json.dumps(self.state, indent=2, default=str)
        )

    def check_transition(self) -> Optional[str]:
        """Check if current state's exit conditions are met. Returns next state or None."""
        current = self.state["current_state"]
        validators = {
            "INIT": self._check_init_exit,
            "DISCOVERY": self._check_discovery_exit,
            "ANALYSIS": self._check_analysis_exit,
            "GAP_CHECK": self._check_gap_exit,
            "WRITING": self._check_writing_exit,
            "VERIFY": self._check_verify_exit,
        }
        return validators.get(current, lambda: None)()

    def transition(self, next_state: str):
        """Record transition and update state."""
        now = datetime.utcnow().isoformat() + "Z"
        # Close current history entry
        if self.state["history"]:
            self.state["history"][-1]["exited_at"] = now
        # Open new history entry
        self.state["history"].append({
            "state": next_state,
            "entered_at": now,
            "exited_at": None,
            "agent": STATE_AGENTS[next_state],
        })
        self.state["current_state"] = next_state
        self.state["heartbeat_at"] = now
        self.save_state()

    def execute_current(self):
        """Dispatch the current state's work to the appropriate agent via adapter."""
        current = self.state["current_state"]
        executors = {
            "INIT": self._exec_init,
            "DISCOVERY": self._exec_discovery,
            "ANALYSIS": self._exec_analysis,
            "GAP_CHECK": self._exec_gap_check,
            "WRITING": self._exec_writing,
            "VERIFY": self._exec_verify,
            "DONE": self._exec_done,
        }
        executors[current]()

    def run(self):
        """Main loop: execute current state, check transitions, advance."""
        while self.state["current_state"] != "DONE":
            self.execute_current()
            next_state = self.check_transition()
            if next_state:
                self.transition(next_state)
            else:
                self.state["status"] = "failed"
                self.save_state()
                break
```

### 3.2 Artifact Validators

```python
class ArtifactValidator:
    """Validates file contracts before allowing state transitions."""

    @staticmethod
    def validate_candidates_csv(path: Path) -> tuple[bool, str]:
        if not path.exists():
            return False, "candidates.csv not found"
        df = csv.DictReader(path.open())
        required = {"paper_id", "title", "authors", "year", "source", "relevance_score", "url"}
        headers = set(df.fieldnames or [])
        missing = required - headers
        if missing:
            return False, f"Missing columns: {missing}"
        rows = list(df)
        if len(rows) == 0:
            return False, "candidates.csv is empty"
        ids = [r["paper_id"] for r in rows]
        if len(ids) != len(set(ids)):
            return False, "Duplicate paper_ids found"
        return True, f"{len(rows)} candidates"

    @staticmethod
    def validate_verify_json(path: Path) -> tuple[bool, str]:
        if not path.exists():
            return False, "verify.json not found"
        data = json.loads(path.read_text())
        if "pass" not in data or "issues" not in data:
            return False, "verify.json missing required fields"
        return True, f"pass={data['pass']}, issues={len(data['issues'])}"

    # ... similar validators for each artifact
```

---

## 4. Verifier Agent

The verifier is the **only new agent** in v2. It runs after WRITING and before DONE.

### 4.1 What It Checks

```yaml
checks:
  citation_existence:
    description: "Every \\cite{key} in review.md has a matching @entry in references.bib"
    method: regex extraction + bib parsing
    severity: error

  citation_reality:
    description: "Every references.bib entry corresponds to a real paper"
    method: cross-check paper_id against candidates.csv; spot-check 5 random entries via Semantic Scholar API
    severity: error

  claim_support:
    description: "Factual claims in review.md trace back to notes/*.md"
    method: for each claim sentence containing a citation, check that the cited paper's notes contain supporting evidence
    severity: warning

  coverage:
    description: "All papers with relevance >= 4 in candidates.csv are mentioned in review.md"
    method: extract paper_ids from review.md citations, compare with candidates.csv filtered by relevance
    severity: warning

  taxonomy_consistency:
    description: "Categories in taxonomy table match section headers in Detailed Analysis"
    method: parse markdown headers vs table rows
    severity: error

  bib_quality:
    description: "BibTeX entries have year, author, title at minimum"
    method: parse each @entry
    severity: warning
```

### 4.2 verify.json Schema

```jsonc
{
  "pass": false,
  "run_id": "20260401_143000",
  "checked_at": "2026-04-01T15:10:00Z",
  "summary": "4 errors, 2 warnings",
  "checks": {
    "citation_existence": {
      "pass": true,
      "details": "32/32 citations found in references.bib"
    },
    "citation_reality": {
      "pass": false,
      "details": "2 entries not found in candidates.csv",
      "issues": [
        { "citekey": "smith2024foo", "reason": "not in candidates.csv" },
        { "citekey": "jones2023bar", "reason": "Semantic Scholar returned 404" }
      ]
    },
    "claim_support": {
      "pass": true,
      "details": "28/30 claims have supporting notes (2 are general statements)"
    },
    "coverage": {
      "pass": false,
      "details": "3 papers with relevance >= 4 not mentioned",
      "issues": [
        { "paper_id": "arxiv:2024.12345", "title": "..." }
      ]
    },
    "taxonomy_consistency": {
      "pass": true,
      "details": "4 categories match 4 section headers"
    },
    "bib_quality": {
      "pass": true,
      "details": "32/32 entries have required fields"
    }
  }
}
```

### 4.3 Verifier SOUL.md

```markdown
# Verifier — Agent

You verify literature review quality. You do NOT write or rewrite — you only check.

## Rules
1. Read verify checks from skills/verifier/SKILL.md
2. Never modify review.md or references.bib
3. Output ONLY verify.json
4. Be strict: flag uncertain items as warnings, not passes
5. For citation_reality spot-checks, use Semantic Scholar API (GET /paper/{paper_id})

## You Do NOT
- Rewrite the review
- Add or remove citations
- Change the taxonomy
- Make subjective quality judgments ("the writing is unclear")
```

---

## 5. Watchdog v2 — Platform-Agnostic Heartbeat Protocol

### 5.1 Protocol

Instead of OpenClaw-specific `openclaw agent --session-id` injection, v2 uses a **file-based heartbeat protocol** that any platform can implement:

```
~/research/{project}/heartbeat.json
```

```jsonc
{
  "agent": "paper-scout",
  "state": "DISCOVERY",
  "updated_at": "2026-04-01T14:35:00Z",
  "message": "Searching OpenAlex... 23 results so far"
}
```

**Contract:**
- Active agents write `heartbeat.json` every 5 minutes
- The watchdog reads `heartbeat.json` + `run_state.json` to detect stalls
- On stall detection, the watchdog writes a `resume_request.json`:

```jsonc
{
  "requested_at": "2026-04-01T14:50:00Z",
  "reason": "No heartbeat for 10 minutes in DISCOVERY state",
  "suggested_action": "resume_discovery",
  "stall_count": 1
}
```

**Platform adapters** poll for `resume_request.json` and handle it:
- **OpenClaw**: inject message via `openclaw agent --session-id`
- **Claude Code**: the state machine engine reads it and re-dispatches
- **CLI**: the main loop reads it and retries the current step

### 5.2 Watchdog Implementation

The watchdog becomes a **simple Python daemon** with no platform imports:

```python
# watchdog_v2.py — platform-agnostic
class Watchdog:
    def __init__(self, project_dir: Path, config: WatchdogConfig):
        self.project_dir = project_dir
        self.config = config

    def run(self):
        while True:
            state = self.read_state()
            if state and state["status"] in ("completed", "failed"):
                break
            heartbeat = self.read_heartbeat()
            if self.is_stalled(heartbeat, state):
                self.write_resume_request(state, heartbeat)
            time.sleep(self.config.poll_sec)

    def is_stalled(self, heartbeat, state) -> bool:
        if not heartbeat:
            return True
        age = (datetime.utcnow() - parse(heartbeat["updated_at"])).total_seconds()
        return age > self.config.idle_timeout_sec
```

---

## 6. Directory Structure (v2)

```
trendr/
├── ARCHITECTURE.md          # this file
├── CLAUDE.md                # Claude Code entry point
├── AGENTS.md                # Codex entry point
├── README.md                # user-facing docs
├── REVIEW.md                # project assessment
│
├── engine/                  # NEW: state machine engine (Python)
│   ├── __init__.py
│   ├── state_machine.py     # ResearchStateMachine
│   ├── validators.py        # ArtifactValidator
│   ├── watchdog.py          # Watchdog v2
│   └── adapters/
│       ├── __init__.py
│       ├── base.py          # PlatformAdapter ABC
│       ├── openclaw.py      # OpenClaw adapter (Phase 1)
│       └── cli.py           # Standalone CLI adapter (Phase 3)
│
├── skills/                  # UNCHANGED: knowledge artifacts
│   ├── paper-scout/SKILL.md
│   ├── paper-analyzer/SKILL.md
│   ├── review-writer/SKILL.md
│   ├── verifier/SKILL.md           # NEW
│   ├── research-vault/SKILL.md
│   ├── platform-hotspots/SKILL.md
│   ├── chrome-cdp-setup/SKILL.md
│   └── trendr-watchdog/SKILL.md    # updated for v2 protocol
│
├── agents/                  # UNCHANGED: personality definitions
│   ├── paper-scout/SOUL.md
│   ├── paper-analyzer/SOUL.md
│   ├── review-lead/SOUL.md
│   └── verifier/SOUL.md            # NEW
│
├── protocols/               # UNCHANGED
│   ├── trendr-protocol.md
│   └── research-team-protocol.md
│
├── scripts/                 # UNCHANGED: Chrome CDP
│   ├── start-chrome-cdp.sh
│   ├── stop-chrome-cdp.sh
│   └── sync-chrome-profile.sh
│
├── install.sh               # updated for v2
├── uninstall.sh
├── pyproject.toml           # NEW: Python project config
└── cli.py                   # NEW: standalone entry point
```

---

## 7. Migration Path (v1 → v2)

### Phase 1: Engine Core + OpenClaw Adapter (Codex tasks)

**Goal**: Get the state machine running on OpenClaw end-to-end, replacing ad-hoc orchestration.

| # | Task | Input | Output | Est. Lines |
|---|------|-------|--------|------------|
| 1 | Create `engine/adapters/base.py` | This spec §2.1 | Abstract base class | ~60 |
| 2 | Create `engine/validators.py` | This spec §3.2, §1.4 | All artifact validators | ~150 |
| 3 | Create `engine/state_machine.py` | This spec §3.1, §1.2 | State machine core | ~250 |
| 4 | Create `engine/watchdog.py` | This spec §5.2 | Platform-agnostic watchdog | ~100 |
| 5 | Create `engine/adapters/openclaw.py` | This spec §2.2 | OpenClaw adapter | ~120 |
| 6 | Create `skills/verifier/SKILL.md` | This spec §4.1 | Verifier skill instructions | ~80 |
| 7 | Create `agents/verifier/SOUL.md` | This spec §4.3 | Verifier agent personality | ~30 |
| 8 | Create `cli.py` | Spec §6 | Entry point (argparse + state machine init) | ~60 |
| 9 | Create `pyproject.toml` | Standard | Project config, no external deps | ~20 |
| 10 | Update `agents/review-lead/SOUL.md` | Current file + §1.2 | Use run_state.json v2 schema, heartbeat protocol | ~diff |

**Total new code**: ~870 lines Python + ~110 lines Markdown

### Phase 2: OpenClaw Integration Test + Backward Compat

| # | Task | Notes |
|---|------|-------|
| 11 | Update `install.sh` | Register engine/ files, add `trendr` CLI command |
| 12 | Update `skills/trendr-watchdog/SKILL.md` | Point to new watchdog, keep old supervisor.py as fallback |
| 13 | Integration test on OpenClaw | Run a real literature review end-to-end |
| 14 | Update protocols to reference v2 state machine | `trendr-protocol.md`, `research-team-protocol.md` |

### Phase 3: Standalone CLI Adapter

| # | Task | Notes |
|---|------|-------|
| 15 | Create `engine/adapters/cli.py` | Pure Python, uses LLM API directly (Anthropic / OpenAI) |
| 16 | Add `--platform` flag to cli.py | Auto-detect + manual override |
| 17 | End-to-end test without OpenClaw | `python cli.py --topic "..." --platform cli` |

### Phase 4: Verifier Hardening

| # | Task | Notes |
|---|------|-------|
| 18 | Implement citation_reality check | Semantic Scholar API spot-check |
| 19 | Implement claim_support check | NLI-style matching between claims and notes |
| 20 | Add fix-loop: VERIFY → WRITING → VERIFY | Auto-fix cycle with max 2 rounds |

### Future: Claude Code Source Integration (separate project)

Not an adapter — a source-level merge. Requires:
- Fork/extend Claude Code agent lifecycle for research-domain primitives
- Embed TrendR engine as a built-in research mode
- Unified memory layer (Claude Code context + TrendR file contracts)
- This is the "agent OS" milestone. Blocked on v2 engine stability.

---

## 8. Key Design Decisions

### Why state machine first (not verifier first)?

GPT recommended P0 = verification layer. I disagree:

1. **Building verifier on OpenClaw glue adds more lock-in.** If the verifier uses `sessions_spawn` to dispatch, it's another OpenClaw-only component to port later.
2. **The state machine is the foundation everything else sits on.** Verifier is just another state (VERIFY) in the machine. Build the machine, then plug in the verifier.
3. **The adapter layer enables testing.** With a CLI adapter, we can test the full pipeline locally without any LLM platform. The verifier's mechanical checks (BibTeX parsing, CSV cross-referencing) don't need an LLM at all.

### Why Python for the engine?

- Already have Python in the project (supervisor.py)
- Zero external dependencies needed for core (csv, json, pathlib, datetime are stdlib)
- Semantic Scholar API calls need only `urllib.request`
- The engine is ~870 lines — small enough to audit entirely

### Why keep SKILL.md files unchanged?

- They're the most valuable assets (REVIEW.md: "the 9-source API handbook alone is worth cloning the repo")
- Agents still read them at runtime for domain knowledge
- The engine doesn't interpret SKILL.md — agents do. Engine only validates outputs.

### Why file-based heartbeat (not API)?

- Works on every platform (even a bare terminal)
- No authentication or network dependency
- Easy to debug (`cat heartbeat.json`)
- The watchdog and the agent only share a filesystem — no coupling

---

## 9. Non-Goals for v2

- **Claude Code source-level integration** — that's the agent OS milestone, a separate project after v2 stabilizes.
- **Web UI / dashboard** — out of scope. File artifacts are the interface.
- **Multi-user / concurrent runs** — one run per project directory.
- **Model fine-tuning** — TrendR uses general-purpose models. Quality comes from playbooks.
- **Replacing SKILL.md with code** — the Markdown-as-playbook pattern is a feature, not a limitation.
- **Supporting non-English literature** — API coverage is English-dominant. Acknowledged limitation.
- **Thin tool-mapping adapters for every platform** — the point is a solid engine, not a compatibility matrix. Two adapters (OpenClaw + CLI) prove the abstraction works.

---

## 10. Success Criteria

v2 is done when:

1. `python cli.py --topic "RL multi-agent market making" --platform openclaw` drives a full pipeline through the state machine on OpenClaw
2. The same command works with `--platform cli` (standalone, no LLM platform dependency for orchestration)
3. `verify.json` catches at least: missing citations, phantom papers, uncovered high-relevance papers
4. The watchdog detects and recovers from a 10-minute agent stall via file-based heartbeat protocol
5. Zero OpenClaw-specific imports in `engine/state_machine.py` or `engine/validators.py`
6. v1 OpenClaw users can still run the old way (`/tr`) with zero breakage — backward compat is mandatory

---

## 11. Trajectory

```
v1 (now)          → workflow with harness characteristics
v2 (this spec)    → proper harness with state machine control plane
v3 (future)       → research agent OS via Claude Code source integration
```

**TrendR is a research-agent harness system, evolving toward a domain-specific agent OS.**
