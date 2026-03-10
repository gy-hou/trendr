<p align="center">
  <h1 align="center">TrendR</h1>
  <p align="center"><strong>Trend Research — Automated Literature Review + Obsidian Knowledge Management</strong></p>
  <p align="center">3 Agents · 4 Skills · 9-Source Search · Zero Extra MCP Dependencies</p>
  <p align="center">
    <a href="#installation">Install</a> · <a href="#usage">Usage</a> · <a href="#architecture">Architecture</a> · <a href="#comparison">Comparison</a>
  </p>
</p>

---

Tell your Agent one sentence. It does the rest.

```
You: "Survey the latest advances in multi-agent systems for finance"

TrendR:
  → 9-source parallel search, 47 candidate papers found
  → Deep-read 12 papers, structured notes + comparison matrix
  → 21KB literature review (taxonomy, gap analysis, BibTeX)
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

| Type | Name | Role |
|------|------|------|
| Agent | `paper-scout` | 9-source search + scoring + dedup |
| Agent | `paper-analyzer` | Deep-read + structured notes + comparison matrix |
| Agent | `review-lead` | Orchestrate pipeline + write review + Obsidian persistence |
| Skill | `paper-scout` | 9 academic API call handbook (10KB) |
| Skill | `paper-analyzer` | Structured extraction templates |
| Skill | `review-writer` | Review writing template + quality checklist |
| Skill | `research-vault` | Obsidian persistence + paper pool index |

---

## Prerequisites

- macOS or Linux
- Node.js 18+
- [OpenClaw](https://openclaw.ai) installed with `openclaw onboard` completed
- [Obsidian](https://obsidian.md) installed
- Any LLM supported by OpenClaw (MiniMax M2.5 / Claude / GPT / etc.)

---

## Installation

```bash
git clone https://github.com/yourname/trendr.git
cd trendr
chmod +x install.sh
./install.sh
```

Custom Obsidian vault path:

```bash
OBSIDIAN_VAULT="/your/vault/path" ./install.sh
```

### What the Installer Does (8 Steps)

| Step | Action |
|------|--------|
| 0 | Detect environment: Node.js, npx, OpenClaw, workspace, Obsidian vault |
| 1 | Install 7 dependency skills via ClawHub (arxiv-watcher, tavily-search, summarize, deep-research, playwright-mcp, agent-browser, obsidian) |
| 2 | Install Playwright browser (chromium) |
| 3 | Copy 3 Agents → `workspace/agents/` |
| 4 | Copy 4 Skills → `workspace/skills/` |
| 5 | Detect Obsidian vault path, inject into skill configs |
| 6 | Initialize Obsidian `Research/` directory + paper pool + templates, sync existing data |
| 7 | Append TrendR workflow to AGENTS.md (with mandatory Obsidian auto-save) |
| 8 | Prompt user to verify `openclaw.json` config |

### Post-Install: Verify openclaw.json

Ensure `~/.openclaw/openclaw.json` contains:

**1. agents.list** — register the three subagents:

```json
{
  "agents": {
    "list": [
      {
        "id": "main",
        "default": true,
        "subagents": {
          "allowAgents": ["paper-scout", "paper-analyzer", "review-lead"]
        }
      },
      { "id": "paper-scout",    "name": "Paper Scout",    "workspace": "~/.openclaw/workspace" },
      { "id": "paper-analyzer", "name": "Paper Analyzer", "workspace": "~/.openclaw/workspace" },
      { "id": "review-lead",    "name": "Review Lead",    "workspace": "~/.openclaw/workspace" }
    ]
  }
}
```

**2. skills.entries** — enable all relevant skills:

```json
"paper-scout": { "enabled": true },
"paper-analyzer": { "enabled": true },
"review-writer": { "enabled": true },
"research-vault": { "enabled": true }
```

**3. maxTokens** >= 32768 for your model (otherwise analyzer output gets truncated)

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

---

## Architecture

### System Overview

```
┌──────────────────────────────────────────────────────────┐
│                         User                              │
│                Telegram / Feishu / Web                     │
└─────────────────────┬────────────────────────────────────┘
                      ▼
┌──────────────────────────────────────────────────────────┐
│           OpenClaw Gateway (runs locally)                  │
│                                                          │
│  ┌─ main agent ───────────────────────────────────────┐  │
│  │  Receive → Decompose → Dispatch → Synthesize       │  │
│  └──────┬──────────────┬──────────────┬───────────────┘  │
│         ▼              ▼              ▼                   │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐           │
│  │  paper-   │  │  paper-   │  │  review-  │           │
│  │  scout    │  │  analyzer │  │  lead     │           │
│  │  Search   │  │  Read     │  │  Write    │           │
│  │  Score    │  │  Extract  │  │  Archive  │           │
│  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘           │
│        │              │              │                   │
│  ┌─────▼──────────────▼──────────────▼───────────────┐  │
│  │  Skills (Markdown instructions for tools)          │  │
│  ├────────────────────────────────────────────────────┤  │
│  │  Tools (exec / web_fetch / read / write / browser) │  │
│  └────────────────────────────────────────────────────┘  │
└─────────┬───────────────────────────────┬────────────────┘
          ▼                               ▼
 ┌─────────────────┐          ┌──────────────────────┐
 │  9 Academic APIs │          │  Obsidian Vault       │
 │  (all free)      │          │  Pool + Cards + Reviews│
 └─────────────────┘          └──────────────────────┘
```

### Pipeline

```
Phase 1: Search ──→ candidates.csv (40-100 papers)
                     search_log.md
         │
Phase 2: Analyze ─→ notes/*.md (10-30 structured notes)
                     matrix.csv (comparison matrix)
         │
Phase 3: Gap Check → insufficient? → back to Phase 1
                     sufficient?  → Phase 4
         │
Phase 4: Write ───→ review.md (15-25KB literature review)
                     references.bib
         │
Phase 5: Persist ─→ Obsidian paper-pool.csv (cumulative, deduped)
                     Obsidian papers/*.md (cards with wiki-links)
                     Obsidian reviews/project/ (archived)
                     Obsidian daily/date.md (research log)
         │
Phase 6: Report ──→ Notify user via Telegram/Feishu
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

---

## Comparison

### TrendR vs autoresearch vs paper-distill-mcp

```
              Discovery      Deep-Read      Review       Knowledge Mgmt
             ──────────     ──────────    ──────────    ──────────
autoresearch      ·              ·             ·              ·

distill-mcp   ████████          █             ·           ████

TrendR        ████████       ████████      ████████      ████████
              9-source       structured    full review   Obsidian + pool
```

### Feature Matrix

| Dimension | autoresearch | paper-distill-mcp | TrendR |
|-----------|-------------|-------------------|--------|
| **Purpose** | LLM training optimization | Paper discovery + push | **Full literature review pipeline** |
| **Core loop** | Edit code → train 5min → eval | Search 9 sources → score → push | **Search → read → write review → archive** |
| **Hardware** | NVIDIA H100 | Any (API calls) | **Mac / Linux (API calls)** |
| **Cost per run** | GPU electricity | ~$3-8 (Claude/GPT) | **~$0-1 (MiniMax)** |
| **Search sources** | N/A | 9 | **9** |
| **Scoring** | val_bpb (hard metric) | 4-dim weighted (code) | 1-5 score (agent) |
| **Paper pool** | N/A | ✅ Persistent | **✅ Obsidian CSV** |
| **Deep reading** | N/A | ❌ One-line summary | **✅ Structured notes** |
| **Comparison matrix** | N/A | ❌ | **✅ matrix.csv** |
| **Literature review** | N/A | ❌ | **✅ Full review** |
| **Obsidian** | N/A | ✅ Note cards | **✅ Cards + reviews + logs + pool** |
| **Zotero** | N/A | ✅ | ❌ (extensible) |
| **Dual AI review** | ❌ | ✅ | ❌ (extensible) |
| **Agent architecture** | Single agent | No agent (pure tools) | **Multi-agent (3 subagents)** |
| **Extra dependencies** | PyTorch + GPU | Python package | **None (web_fetch only)** |
| **License** | MIT | AGPL-3.0 | **MIT** |

### Design Philosophy

**autoresearch** — *"Hand the experiment loop to AI"*. Human writes `program.md` (strategy), AI writes `train.py` (code). Elegant constraint design: single file, fixed 5-min budget, single metric. But GPU-only.

**paper-distill-mcp** — *"Hand the screening grunt-work to code"*. Search/score/dedup are deterministic ops — Python code does them 100x cheaper than LLMs. 19 tool functions, 4-dim scoring, paper pool state machine. Solid engineering. But stops at "push 6 papers with one-line summaries".

**TrendR** — *"Hand the entire literature review to multi-agent collaboration"*. Paper search is cheap (free APIs). **Deep reading and review writing are the real value**. 3 specialized subagents, Skill files as executable knowledge, Obsidian for persistent knowledge. Zero extra dependencies — agents call public APIs directly.

### Complementary Use

The three projects are not mutually exclusive. Strongest combo:

```
paper-distill-mcp (replace paper-scout for search frontend)
  → 4-dim weighted scoring + code-level dedup + dual AI review

TrendR analyzer + writer + vault (keep as backend)
  → Structured notes + review writing + Obsidian persistence
```

TrendR is already compatible — Phase 1 can be replaced by anything that produces `candidates.csv`.

---

## Cost Analysis

Using MiniMax M2.5 ($0.30/1M input, $1.20/1M output):

| Phase | Tokens | Cost |
|-------|--------|------|
| Phase 1: Search | ~100K | ~$0.15 |
| Phase 2: Deep-read 20 papers | ~400K | ~$0.60 |
| Phase 3: Gap check | ~50K | ~$0.08 |
| Phase 4: Write review | ~200K | ~$0.30 |
| Phase 5: Persist | ~30K | ~$0.05 |
| **Total** | **~780K** | **~$1.18** |

With MiniMax Portal (free OAuth tier): **$0**.

| Approach | Per Run | Monthly (4x) |
|----------|---------|-------------|
| TrendR + MiniMax free | $0 | $0 |
| TrendR + MiniMax API | ~$1.2 | ~$5 |
| paper-distill + Claude | ~$3-5 | ~$15-20 |
| Manual (@ $30/hr) | ~$240 | ~$960 |

---

## Customization

**Add search sources**: Edit `skills/paper-scout/SKILL.md`, add new `web_fetch` calls following existing format.

**Modify review template**: Edit `skills/review-writer/SKILL.md`.

**Modify note fields**: Edit `skills/paper-analyzer/SKILL.md`.

**Switch models**: TrendR is model-agnostic. Configure in `openclaw.json` — MiniMax, Claude, GPT, DeepSeek, anything.

**Daily paper tracking**: Tell your agent: "Set up daily arXiv cs.AI check at 9am".

---

## Known Limitations

- **Not real-time**: Academic APIs have rate limits (arXiv: 3s/request); full search takes minutes
- **Non-frontier models may forget**: MiniMax M2.5 sometimes skips Skill files despite 3-layer defense
- **Limited full-text reading**: Most papers analyzed via abstract pages; full PDF parsing depends on download + parse capability
- **No Zotero integration**: Extensible (reference paper-distill-mcp's implementation)
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
