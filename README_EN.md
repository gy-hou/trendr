<p align="center">
  <h1 align="center">TrendR</h1>
  <p align="center"><strong>Trend Research — Automated Literature Review + Obsidian Knowledge Management</strong></p>
  <p align="center">3 Agents · 5 Skills · 9-Source Search · Basic / Full Install Modes</p>
  <p align="center">
    <a href="#installation">Install</a> · <a href="#usage">Usage</a> · <a href="#architecture">Architecture</a>
  </p>
</p>

---

Tell your Agent one sentence. It does the rest.

```
You: "Survey the latest advances in agentic RAG 2025"

TrendR:
  → 9-source parallel search, 81 candidate papers found
  → Deep-read 11 papers, structured notes + comparison matrix
  → 14KB literature review (taxonomy, gap analysis, BibTeX)
  → Auto-archived to Obsidian, paper pool persisted
  → Notifies you: done ✅
```

Inspired by [karpathy/autoresearch](https://github.com/karpathy/autoresearch)'s autonomous research loop, redesigned from "LLM training optimization" to "paper search + literature review", from NVIDIA H100 to Mac Apple Silicon, from GPU bills to ~$1/run.

---

## What It Solves

| Step | Manual | TrendR |
|------|--------|--------|
| Cross-platform paper search | 3-4 hours | 5 min (9 sources parallel) |
| Screen relevant papers | 2-3 hours | Auto-scored 1-5 + dedup |
| Deep-read + take notes | 8-12 hours | Structured extraction (problem/method/results/limitations) |
| Write review report | 6-8 hours | Auto-generated (taxonomy + analysis + research gaps) |
| Compile references | 1-2 hours | Auto BibTeX |
| Archive to knowledge base | 1 hour | Auto-sync to Obsidian |
| **Total** | **~20-30 hours** | **~30 min wait** |

---

## What's Inside

**Core (both Basic and Full)**

| Type | Name | Role |
|------|------|------|
| Agent | `paper-scout` | 9-source search + scoring + dedup |
| Agent | `paper-analyzer` | Deep-read + structured notes + comparison matrix |
| Agent | `review-lead` | Orchestrate pipeline + write review |
| Skill | `paper-scout` | 9 academic API call handbook (10KB) |
| Skill | `paper-analyzer` | Structured extraction templates |
| Skill | `review-writer` | Review writing template + quality checklist |
| Skill | `research-vault` | Obsidian persistence + paper pool index |
| Skill | `trendr-watchdog` | Runtime watchdog + timeout auto-resume + checkpoint recovery |

**Enhancement Layer (Full mode only)**

| Component | Function | Without it |
|-----------|----------|-----------|
| Scrapling | Deep-crawl: extract JS-rendered page content | Static APIs only, slightly lower coverage |
| Zotero | Library sync, auto-import DOI | BibTeX still generated locally |
| Obsidian + obsidian-cli | Paper cards + review archive + daily log | Results saved to `~/research/` only |
| Nano-pdf | Full-text PDF reading | Abstract/metadata only |
| Context7 | Precise library docs for codex-coder | Falls back to web search |

**Fallback Layer (not enabled by default in either mode)**

| Component | Trigger condition |
|-----------|-----------------|
| Playwright | Only when JS-rendered content missing / login state required / user explicitly requests live page interaction — not in default retrieval chain |

---

## Prerequisites

**Basic mode (minimum)**
- macOS or Linux
- Node.js 18+
- [OpenClaw](https://openclaw.ai) installed with `openclaw onboard` completed
- Any LLM supported by OpenClaw (MiniMax M2.5 / Claude / GPT / etc.)

**Full mode (additional)**
- [Obsidian](https://obsidian.md) App + obsidian-cli (`brew install obsidian-cli`)
- Python 3 + `pip install scrapling`
- Zotero App + [API Key](https://www.zotero.org/settings/keys)
- (Optional) Playwright: `npm install -g @playwright/mcp`

---

## Installation

```bash
git clone https://github.com/gy-hou/trendr.git
cd trendr
chmod +x install.sh
./install.sh
```

The installer shows a full component manifest and Basic/Full comparison table before asking you to choose. Nothing is installed until you confirm.

**Choose Basic:** Core pipeline ready immediately, no extra tool dependencies.
**Choose Full:** Automatically installs Scrapling, Obsidian CLI, Nano-pdf, Context7, and guides Zotero setup.

Custom Obsidian vault path (Full mode):

```bash
OBSIDIAN_VAULT="/your/vault/path" ./install.sh
```

### Post-Install: Verify openclaw.json

The installer auto-registers agents and skills. Double-check that `~/.openclaw/openclaw.json` includes:

**agents.list** — three subagents:

```json
{ "id": "paper-scout",    "name": "Paper Scout",    "workspace": "~/.openclaw/workspace" },
{ "id": "paper-analyzer", "name": "Paper Analyzer", "workspace": "~/.openclaw/workspace" },
{ "id": "review-lead",    "name": "Review Lead",    "workspace": "~/.openclaw/workspace" }
```

**maxTokens** >= 32768 for your model (otherwise analyzer output gets truncated)

Then:

```bash
openclaw gateway restart
```

---

## Usage

```bash
# New literature review
"Survey the latest advances in [TOPIC]"

# Search papers
"Search papers on autonomous AI agents, focus on 2024-2025, prefer those with code"

# Query paper pool
"Find papers about transformer in my paper pool"
"Paper pool stats by project"

# Continue a project
"Continue rl-multi-agent-finance, add market making direction"

# Sync to Obsidian
"Sync research results to Obsidian"

# Daily tracking
"Set up daily arXiv cs.AI check at 9am"
```

### Interactive Entry (`/trendr`)

When users type `/trendr`, `/trendr Topic: ...`, or `trendr research ...`, it enters quick confirmation mode (`y/n/r`) by default. To switch to precise mode, input `/b`.

Default quick confirmation mode:
- `y`: accept defaults (3 rounds + standard 10 candidates/round + 3 citations)
- `n`: enter custom parameters
- `r`: force re-run Scout

Precise mode (`/b`):
- Research topic: one-sentence problem statement (required)
- Iteration rounds: `A=1-3` / `B=3-6` / `C=6-10`
- Research level: `A=API standard` / `B=API + Scrapling` / `C=API + Scrapling + Tavily`
- Time budget (minutes)
- Users can reply with option letters only (A/B/C)
- Example: `Topic: RL multi-agent market making; B / B / 60`
- Topic-only input is still incomplete (e.g. `/trendr Topic: Agent Decision Systems`) and must continue parameter collection before execution.

TrendR then returns a feasibility-adjusted plan:

- If budget is too low (< 70% of estimated runtime), reduce rounds first, then source target
- Show estimated completion time in local timezone
- Ask for explicit confirmation: `Confirm execution? (y / n)`
- Before explicit confirmation (`y/yes/confirm/start/continue`), TrendR will not dispatch `review-lead` and will not emit "started/dispatched/pipeline running" status.

### Runtime Progress + Logs

Each run now writes and refreshes:

- `run_status.json`: machine-readable status (phase, percent, started_at, eta)
- `progress.md`: human-readable progress bar (Phase 1-5)
- `logs/<RUN_ID>.log`: full per-run log for debugging/correction
- `logs/latest.log`: snapshot of the latest run
- `logs/watchdog_<RUN_ID>.json`: auto-resume state (injection count + latest reason)
- `logs/watchdog.out`: watchdog background stdout/stderr

Default heartbeat: update status/log at least every 5-10 minutes.  
Auto-resume threshold: 10 minutes without activity, or 3 minutes of phase/file mismatch.

---

## Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                            User                                   │
│                   Telegram / Feishu / Web / CLI                   │
└──────────────────────────┬──────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                 OpenClaw Gateway (runs locally)                    │
│                                                                 │
│  ┌─ main agent ──────────────────────────────────────────────┐  │
│  │       Receive → Decompose → Dispatch → Synthesize          │  │
│  └──────┬───────────────┬────────────────┬────────────────────┘  │
│         ▼               ▼                ▼                       │
│  ┌────────────┐  ┌────────────┐  ┌─────────────┐               │
│  │paper-scout │  │paper-      │  │review-lead  │               │
│  │Search Score│  │analyzer    │  │Orchestrate  │               │
│  │Dedup       │  │Read Extract│  │Write Archive│               │
│  └─────┬──────┘  └─────┬──────┘  └──────┬──────┘               │
│        │               │                │                       │
│  ┌─────▼───────────────▼────────────────▼──────────────────┐   │
│  │            Skills (executable Markdown knowledge files)   │   │
│  │  paper-scout · paper-analyzer · review-writer · vault    │   │
│  │  + trendr-watchdog (runtime auto-resume watchdog)        │   │
│  └──────────────────────────┬──────────────────────────────┘   │
│                             ▼                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Tool Layer (exec / web_fetch / read / write / browser)   │   │
│  ├──────────────────────────────────────────────────────────┤   │
│  │  Basic:  9×Academic APIs (free, no extra deps)            │   │
│  │  Full:   + Scrapling (JS rendering) + Nano-pdf (full PDF) │   │
│  │          + Context7 (library docs) + Zotero (library)     │   │
│  │  Fallback: Playwright (only when JS missing / login req'd) │   │
│  └──────────────────────────────────────────────────────────┘   │
└────────────┬────────────────────────────┬───────────────────────┘
             ▼                            ▼
  ┌─────────────────────┐     ┌────────────────────────────┐
  │  9 Academic APIs     │     │  Obsidian Vault             │
  │  arXiv · S2 · OA    │     │  Pool / Cards / Reviews / Log│
  │  PubMed · DBLP ···  │     └────────────────────────────┘
  └─────────────────────┘
```

### Pipeline

```
  One sentence from you
        │
        ▼
┌─ Phase 1: Search ───────────────────────────────────────┐
│  paper-scout calls 3-5 most relevant APIs in parallel    │
│  → candidates.csv (40-100 papers, relevance score 1-5)   │
│  → search_log.md                                        │
└──────────────────────────────┬──────────────────────────┘
                               ▼
┌─ Phase 2: Deep Read ────────────────────────────────────┐
│  paper-analyzer reads all papers with score ≥ 4          │
│  → notes/*.md (structured: problem/method/results/limits)│
│  → matrix.csv (multi-dimensional comparison)             │
└──────────────────────────────┬──────────────────────────┘
                               ▼
┌─ Phase 3: Gap Check ────────────────────────────────────┐
│  Coverage insufficient? ──→ back to Phase 1              │
│  Coverage sufficient?   ──→ Phase 4                      │
└──────────────────────────────┬──────────────────────────┘
                               ▼
┌─ Phase 4: Write Review ─────────────────────────────────┐
│  review-lead generates full literature review            │
│  → review.md (15-25KB: taxonomy / gap analysis / trends) │
│  → references.bib                                       │
└──────────────────────────────┬──────────────────────────┘
                               ▼
┌─ Phase 5: Persist ──────────────────────────────────────┐
│  Basic:  ~/research/<project>/  local storage            │
│  Full:   Obsidian paper-pool.csv (cumulative, deduped)   │
│          Obsidian papers/*.md (cards with wiki-links)     │
│          Obsidian reviews/project/ (archived)             │
│          Obsidian daily/date.md (research log)            │
│          Zotero library auto-sync                         │
└──────────────────────────────┬──────────────────────────┘
                               ▼
                   Notify user (Telegram / Feishu)
```

### 9-Source Search Coverage

All APIs are public and free. Called directly via `web_fetch` — no MCP server needed:

| # | Source | Coverage | Key Required |
|---|--------|----------|-------------|
| 1 | arXiv | CS/Math/Physics preprints | No |
| 2 | Semantic Scholar | 200M+ papers, citation graph | Recommended (free) |
| 3 | OpenAlex | 250M+ works, fully open | No |
| 4 | PubMed | 36M+ biomedical | No |
| 5 | CrossRef | 140M+ DOI-registered | No |
| 6 | DBLP | Computer science literature | No |
| 7 | Europe PMC | 40M+ life sciences | No |
| 8 | bioRxiv | Biology preprints | No |
| 9 | Papers with Code | ML papers with code repos | No |

The agent auto-selects 3-5 most relevant sources based on research domain.

### Obsidian Knowledge Base

```
[Vault]/Research/
├── _index/
│   └── paper-pool.csv          ← Paper pool (cumulative across projects)
├── papers/
│   └── 2301.12345.md           ← Paper cards (YAML frontmatter + wiki-links)
├── reviews/
│   └── project-name/
│       ├── review.md
│       ├── references.bib
│       └── matrix.csv
├── daily/
│   └── 2026-03-10.md           ← Daily research log
└── templates/
```

Paper pool CSV tracks status progression: `candidate` → `analyzed` → `cited_in_review`

### Anti-Forgetting Mechanism

When using non-frontier models (e.g., MiniMax M2.5), agents may forget to read Skill files. TrendR uses three defensive layers:

| Layer | Mechanism |
|-------|-----------|
| AGENTS.md | Hard-coded rule: "task description MUST include 'read skills/xxx/SKILL.md first'" |
| SOUL.md | Warning at top: "⚠️ First step: read skills/xxx/SKILL.md" |
| SKILL.md | Complete copy-paste commands instead of abstract instructions |

## Customization

All core logic lives in Skill files (Markdown) — edit directly, no code changes needed.

**Add search sources**

Edit `skills/paper-scout/SKILL.md`, add a new `web_fetch` block following the existing format. Each block contains: URL template, parameter descriptions, response field parsing.

**Modify review structure**

Edit `skills/review-writer/SKILL.md` to adjust section templates, quality checklists, and BibTeX formatting rules.

**Modify note fields**

Edit `skills/paper-analyzer/SKILL.md` to add or remove extraction dimensions (e.g. add a "Dataset" field or "Reproducibility" score).

**Switch models**

TrendR is model-agnostic. Configure in `openclaw.json`:
```json
{ "model": "minimax-m2.5" }    // Low cost (~$0-1/run)
{ "model": "claude-opus-4-6" }  // Higher quality
{ "model": "gpt-4o" }           // Alternative
```

**Extend the Full mode toolchain**

Add your tool's install and registration logic in the Full mode section of `install.sh`, following the `_ensure_skill()` function pattern.

**Daily paper tracking**

Tell your agent: "Set up daily arXiv cs.AI check at 9am" — the agent will configure the scheduled task automatically.

---

## Known Limitations

- **Not real-time**: Academic APIs have rate limits (arXiv: 3s/request); full search takes minutes
- **Network policy can change runtime quality**: some proxy/DNS setups resolve academic domains to `198.18.x.x` (fake-ip), which may trigger `web_fetch` SSRF blocking; TrendR now auto-falls back to alternate search paths, but coverage can still drop
- **Non-frontier models may forget**: MiniMax M2.5 sometimes skips Skill files despite 3-layer defense
- **Full-text reading (Basic mode)**: Abstract pages only; Full mode enables Nano-pdf for full PDF reading
- **Zotero / Obsidian (Basic mode)**: Not included; Full mode auto-configures both
- **No dual AI review**: Extensible (reference paper-distill-mcp's dual review mode)

---

## Uninstall

```bash
chmod +x uninstall.sh
./uninstall.sh
```

Your Obsidian research data and `~/research/` are preserved.

---

## Credits

- [karpathy/autoresearch](https://github.com/karpathy/autoresearch) — Autonomous research loop inspiration
- [paper-distill-mcp](https://github.com/Eclipse-Cj/paper-distill-mcp) — Multi-source search architecture reference
- [OpenClaw](https://openclaw.ai) — Agent runtime infrastructure

## License

MIT
