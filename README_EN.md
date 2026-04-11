<p align="center">
  <h1 align="center">TrendR</h1>
  <p align="center"><strong>Trend Research — Automated Literature Review + Platform Trend Monitoring + Obsidian Knowledge Management</strong></p>
  <p align="center">4 Agents · 8 Skills · 9-Source Search · 9-Platform Trends · Basic / Full Install</p>
  <p align="center">
    <a href="#installation">Install</a> · <a href="#usage">Usage</a> · <a href="#architecture">Architecture</a>
  </p>
  <p align="center">
    <a href="./README.md">中文</a> | English
  </p>
</p>

---

Tell your Agent one sentence. TrendR handles the rest.

```
You: "Survey the latest advances in agentic RAG 2025"

TrendR:
  → 9-source parallel search, 81 candidate papers found
  → Deep-read 11 papers, structured notes + comparison matrix
  → 14KB literature review (taxonomy, gap analysis, BibTeX)
  → Auto-archived to Obsidian, paper pool persisted
  → Notifies you: Done ✅
```

Inspired by [karpathy/autoresearch](https://github.com/karpathy/autoresearch) — redesigned from "LLM training optimization" to "paper search + literature review."

> TrendR is a research-agent harness system, evolving toward a domain-specific agent OS.

---

## What Problem It Solves

| Step | Manual | TrendR |
|------|--------|--------|
| Cross-platform paper search | 3–4 hrs | 5 min (9 sources parallel) |
| Filter relevant papers | 2–3 hrs | Auto score 1–5 + dedup |
| Deep read + notes | 8–12 hrs | Structured extraction (problem / method / result / limitation) |
| Write literature review | 6–8 hrs | Auto-generated (taxonomy + gap analysis + trends) |
| BibTeX references | 1–2 hrs | Automatic |
| Archive to knowledge base | 1 hr | Auto-sync to Obsidian |
| **Total** | **~20–30 hrs** | **~30 min wait** |

---

## What's Inside

**Core (Basic + Full)**

| Type | Name | Role |
|------|------|------|
| Agent | `paper-scout` | 9-source search + score + dedup |
| Agent | `paper-analyzer` | Deep read + structured notes + comparison matrix |
| Agent | `review-lead` | Pipeline orchestration + survey writing |
| Agent | `verifier` | Citation validity / claim accuracy / taxonomy consistency |
| Skill | `paper-scout` | 9 academic API playbooks (10KB) |
| Skill | `paper-analyzer` | Structured extraction templates |
| Skill | `review-writer` | Survey template + quality checklist |
| Skill | `verifier` | VERIFY rules + verify.json output protocol |
| Skill | `research-vault` | Obsidian persistence + paper pool index |
| Skill | `trendr-watchdog` | Runtime supervision + timeout auto-resume + checkpoint recovery |
| Skill | `platform-hotspots` | 9-platform trend scraping (Zhihu / XHS / X / Reddit / YouTube / GitHub / HN / PH) |
| Skill | `chrome-cdp-setup` | Chrome 146+ CDP dual-instance + cookie sync + troubleshooting |
| Runtime | `engine/` | v2 engine: state machine + validators + watchdog + adapters |
| Runtime | `cli.py` | Standalone CLI: `run / resume / status` |

**Full Mode Extras**

| Component | Function | Without it |
|-----------|----------|-----------|
| Scrapling | Deep-crawl JS-rendered pages | Static APIs only, slightly lower coverage |
| Zotero | Library sync, auto-import DOI | BibTeX still generated locally |
| Obsidian + obsidian-cli | Paper cards + review archive + daily logs | Results saved to `~/research/` only |
| Nano-pdf | Full-text PDF reading | Abstract/metadata only |
| Context7 | Precise library docs for codex-coder | Falls back to web search |

**Fallback Layer (not enabled by default)**

| Component | Trigger |
|-----------|---------|
| Playwright | JS rendering gaps, login-gated pages, or explicit user request only |

---

## Compatible Runtimes

TrendR Skills are pure Markdown files; core API calls are standard HTTP REST — works across multiple agent platforms:

| Platform | Support | Notes |
|----------|---------|-------|
| **OpenClaw** | Full | Native multi-agent orchestration + browser automation |
| **Standalone CLI** | v2 engine | `python cli.py run --topic "..." --platform cli` via `engine/adapters/cli.py` + OpenAI/Anthropic auto-provider |
| **Claude Code** | Skills + CLI | `python cli.py run --topic "..." --platform claude-code`, or use CLAUDE.md tool mapping |
| **Codex** | Skills + CLI | `python cli.py run --topic "..." --platform codex`, or use AGENTS.md tool mapping |
| **Other agents** | Skills readable | `SKILL.md` is standard Markdown; API URLs are directly copyable |

> Native multi-agent orchestration and browser automation are best supported on OpenClaw. Codex / Claude Code / CLI default to stability-first sequential execution, with limited parallelism only for DISCOVERY and ANALYSIS.

Unified runtime contract:
- canonical runtime: `openclaw`, `codex`, `claude-code`, `cli`
- alias: `claudecode -> claude-code`
- detection priority: CLI `--platform` > `TRENDR_PLATFORM` > `OPENCLAW_SESSION_ID` > `CODEX_*` > `CLAUDE_CODE_*` > `cli`
- each skill executes only the matching runtime block; non-target blocks are marked `dormant` and skipped

---

## Prerequisites

**Basic mode (minimum)**
- macOS or Linux
- Node.js 18+
- [OpenClaw](https://openclaw.ai) installed with `openclaw onboard` (or use Claude Code / Codex to read Skills directly)
- Any LLM supported by OpenClaw (MiniMax M2.5 / Claude / GPT / etc.)

**CLI mode (standalone)**
- Python 3
- Runtime-native credentials (either path):
  - `--platform codex`: Codex App session or `codex` CLI login
  - `--platform claude-code`: Claude Code session or `claude` CLI login
- Or API-key fallback: `OPENAI_API_KEY` (preferred) or `ANTHROPIC_API_KEY`
- Optional: `TRENDR_PROVIDER=auto|openai|anthropic` (default `auto`)
- Optional: `TRENDR_MODEL` to override default model (OpenAI default `gpt-5.4-mini`, Anthropic default `claude-sonnet-4-20250514`)
- Optional: `TRENDR_PLATFORM` to explicitly set runtime (overrides auto-detection)

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

Cross-runtime skill distribution (Codex / Claude Code):

```bash
bash scripts/install-universal-skills.sh --runtime all --copy
# or: --runtime codex / --runtime claude-code
# optional: --force to replace existing installs, --link for symlink mode
```

The installer shows a full component manifest and Basic/Full comparison table before asking you to choose. Nothing installs until you confirm.

**Choose Basic:** Core pipeline ready immediately, no extra tool dependencies.
**Choose Full:** Automatically installs Scrapling, Obsidian CLI, Nano-pdf, Context7, and guides Zotero setup.

Custom Obsidian vault path (Full mode):

```bash
OBSIDIAN_VAULT="/your/vault/path" ./install.sh
```

### Enable Obsidian CLI

1. Open Obsidian → Settings → General → Command Line Interface → Enable
2. In Terminal:
```bash
obsidian-cli set-default --vault OpenClaw-Vault
obsidian-cli print-default
# Should show: OpenClaw-Vault at /Users/mac/Documents/OpenClaw-Vault

obsidian-cli create "test-note" --vault OpenClaw-Vault --content "# Hello from CLI"
```

### Post-Install: Verify openclaw.json

The installer auto-registers agents and skills. Confirm `~/.openclaw/openclaw.json` contains:

**agents.list** — four subagents:

```json
{ "id": "paper-scout",    "name": "Paper Scout",    "workspace": "~/.openclaw/workspace" },
{ "id": "paper-analyzer", "name": "Paper Analyzer", "workspace": "~/.openclaw/workspace" },
{ "id": "review-lead",    "name": "Review Lead",    "workspace": "~/.openclaw/workspace" },
{ "id": "verifier",       "name": "Verifier",       "workspace": "~/.openclaw/workspace" }
```

**maxTokens** >= 32768 (otherwise analyzer output gets truncated)

Then:

```bash
openclaw gateway restart
```

---

## Usage

```bash
# Standalone CLI (v2 engine)
python cli.py run --topic "agentic RAG 2025" --depth B
python cli.py run --topic "agentic RAG 2025" --platform codex
python cli.py run --topic "agentic RAG 2025" --platform claude-code
python cli.py status ~/research/agentic-rag-2025
python cli.py resume ~/research/agentic-rag-2025

# New literature review
"Survey the latest advances in [TOPIC]"

# Search papers
"Search papers on autonomous AI agents, focus 2024-2025, prefer those with code"

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

### CLI Runtime & Provider Troubleshooting

- Runtime-native credentials are preferred: `--platform codex` first tries native Codex session (including Codex App), and `--platform claude-code` first tries native Claude session
- Errors containing `401 Unauthorized` or `Missing bearer`: log in the corresponding CLI (`codex login` or `claude auth login`), or configure API-key fallback
- `No model API key found`: native session is unavailable and fallback keys are not configured; set `OPENAI_API_KEY` (preferred) or `ANTHROPIC_API_KEY`
- Force provider: `export TRENDR_PROVIDER=openai` or `export TRENDR_PROVIDER=anthropic`
- Force runtime: `export TRENDR_PLATFORM=codex` (or `claude-code` / `openclaw` / `cli`)
- Alias support: `--platform claudecode` is normalized to `claude-code`

### Platform Trend Monitoring

Beyond academic papers, TrendR monitors 9 platforms in real time via Chrome CDP:

```
You: "What's trending in AI today?"

TrendR:
  → Chrome CDP automation (dedicated instance with login state)
  → Zhihu · Zhihu Tech · XHS Tech · X/Twitter
  → Reddit · YouTube · GitHub Trending · Hacker News · Product Hunt
  → Cross-platform tech trend summary
```

Start Chrome CDP instance first:
```bash
bash ~/.openclaw/workspace/scripts/start-chrome-cdp.sh
```

Log in to Zhihu, X, etc. on first use. Cookies persist in `cdp-automation` profile. See `chrome-cdp-setup` skill for details.

### Interactive Entry (`/tr`)

Type `/tr`, `/tr Topic: ...`, `/trendr`, or `trendr research ...` to enter parameterized quick mode. For precise mode, input `/b`.

**Parameterized quick mode:**
- Research topic: one-sentence problem statement (required)
- Iteration rounds: `A=1–3` / `B=3–6` / `C=6–10`
- Research depth: `A=API standard` / `B=API + Scrapling` / `C=API + Scrapling + Tavily`
- Time budget (minutes)
- Example: `Topic: RL multi-agent market making; B / B / 60`

TrendR returns a feasibility-adjusted plan with estimated completion time, then asks: `Confirm execution? (y / n)` — will not dispatch `review-lead` before explicit confirmation.

### Runtime Progress & Logs

Each run writes and refreshes:

- `run_status.json` — machine-readable status (phase, percent, started_at, eta)
- `progress.md` — human-readable progress bar (Phase 1–5)
- `logs/<RUN_ID>.log` — full run log for debugging
- `logs/latest.log` — latest run snapshot
- `logs/supervisor_<RUN_ID>.json` — overnight state (injection count, latest reason, stop reason)
- `logs/overnight_report_<RUN_ID>.md` — overnight guardian report
- `logs/overnight_report.md` — latest overnight report mirror
- `logs/watchdog.out` — watchdog background output

Default heartbeat: update at least every 5–10 minutes.
Auto-resume threshold: 10 min no activity, or 3 min phase/file mismatch.
Early-complete: when `review.md + references.bib` stable for 30 min, supervisor exits automatically.

---

## Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         User                                     │
│                Telegram / Feishu / Web / CLI                     │
└──────────────────────────┬──────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│              OpenClaw Gateway (runs locally)                      │
│                                                                  │
│  ┌─ main agent ──────────────────────────────────────────────┐   │
│  │      Receive → Decompose → Dispatch → Synthesize           │   │
│  └──────┬──────────────┬──────────────┬──────────────────────┘   │
│         ▼              ▼              ▼              ▼           │
│  ┌────────────┐ ┌────────────┐ ┌──────────────┐ ┌──────────┐   │
│  │paper-scout │ │paper-      │ │review-lead   │ │verifier  │   │
│  │search·score│ │analyzer    │ │orchestrate   │ │citation  │   │
│  │dedup       │ │read·extract│ │write·archive │ │taxonomy  │   │
│  └────────────┘ └────────────┘ └──────────────┘ └──────────┘   │
│                                                                  │
│  ┌── Skills (executable Markdown knowledge files) ─────────┐    │
│  │  paper-scout · paper-analyzer · review-writer · verifier │    │
│  │  research-vault · trendr-watchdog                        │    │
│  │  platform-hotspots · chrome-cdp-setup                   │    │
│  └──────────────────────────┬───────────────────────────────┘   │
│                             ▼                                    │
│  ┌── v2 engine (state machine / validators / watchdog) ────┐    │
│  │  INIT→DISCOVERY→ANALYSIS→GAP_CHECK→WRITING→VERIFY→DONE  │    │
│  ├─────────────────────────────────────────────────────────┤    │
│  │  Basic:   9×Academic APIs (free, no extra deps)          │    │
│  │  Full:    +Scrapling +Nano-pdf +Context7 +Zotero         │    │
│  │  Fallback: Playwright (JS gaps / login only)             │    │
│  └─────────────────────────────────────────────────────────┘   │
└────────────┬───────────────────────────┬────────────────────────┘
             ▼                           ▼
  ┌─────────────────────┐   ┌───────────────────────────┐
  │  9 Academic APIs    │   │  Obsidian Vault            │
  │  arXiv·S2·OA·PubMed │   │  pool / cards / reviews   │
  │  CrossRef·DBLP···   │   │  daily logs               │
  └─────────────────────┘   └───────────────────────────┘
```

### v2 State Machine

```
INIT → DISCOVERY → ANALYSIS → GAP_CHECK → WRITING → VERIFY → DONE
                          ↑                          ↓
                          └────── coverage gaps ─────┘

VERIFY fail:
WRITING ← verify.json.pass=false (max 2 repair rounds)
```

### Pipeline

```
User prompt
    │
    ▼
Phase 1 · Search ────── paper-scout: 3–5 APIs parallel
    │                   → candidates.csv (40–100, scored 1–5)
    │                   → search_log.md
    ▼
Phase 2 · Deep Read ─── paper-analyzer: reads score ≥ 4
    │                   → notes/*.md (problem/method/result/limitation)
    │                   → matrix.csv (multi-dimensional comparison)
    ▼
Phase 3 · Gap Check ─── enough coverage? → Ph.4 : loop back to Ph.1
    ▼
Phase 4 · Write ──────── review-lead: full literature review
    │                   → review.md (15–25KB: taxonomy/gaps/trends)
    │                   → references.bib
    ▼
Phase 5 · Verify ──────── verifier: citation/claim/coverage/taxonomy
    │                   fail → Ph.4 (max 2 rounds) | pass → Ph.6
    ▼
Phase 6 · Persist ────── Basic: ~/research/<project>/
    │                   Full:  Obsidian paper-pool.csv (cumulative)
    │                          Obsidian papers/*.md (cards + wiki-links)
    │                          Obsidian reviews/project/ (archived)
    │                          Zotero library auto-sync
    ▼
Notify user (Telegram / Feishu)
```

### 9 Search Sources

All APIs are public and free — called via `web_fetch`, no extra MCP needed:

| # | Source | Coverage | Key Required |
|---|--------|----------|-------------|
| 1 | arXiv | CS / Math / Physics preprints | No |
| 2 | Semantic Scholar | 200M+ papers, citation graph | Recommended (free) |
| 3 | OpenAlex | 250M+ works, fully open | No |
| 4 | PubMed | 36M+ biomedical | No |
| 5 | CrossRef | 140M+ DOI-registered | No |
| 6 | DBLP | Computer science bibliography | No |
| 7 | Europe PMC | 40M+ life sciences | No |
| 8 | bioRxiv | Biology preprints | No |
| 9 | Papers with Code | ML papers + code repos | No |

Agent auto-selects 3–5 most relevant sources per topic.

### Obsidian Knowledge Base

```
[Vault]/Research/
├── _index/
│   └── paper-pool.csv          ← paper pool (cumulative across projects)
├── papers/
│   └── 2301.12345.md           ← paper cards (YAML frontmatter + wiki-links)
├── reviews/
│   └── project-name/
│       ├── review.md
│       ├── references.bib
│       └── matrix.csv
├── daily/
│   └── 2026-03-10.md           ← daily research log
└── templates/
```

Paper pool CSV tracks status: `candidate` → `analyzed` → `cited_in_review`

### Anti-Forgetting Mechanism

When using non-frontier models (e.g. MiniMax M2.5), agents may skip reading Skill files. TrendR uses 3-layer defense:

| Layer | Mechanism |
|-------|-----------|
| `AGENTS.md` | Hard rule: task description MUST include "read skills/xxx/SKILL.md first" |
| `SOUL.md` | Top warning: "⚠️ Step 1: read skills/xxx/SKILL.md" |
| `SKILL.md` | Complete copy-paste commands, not abstract instructions |

---

## Customization

All core logic lives in Skill files (Markdown) — edit directly, no code changes needed.

- **Add search sources** — edit `skills/paper-scout/SKILL.md`, add `web_fetch` block
- **Modify review structure** — edit `skills/review-writer/SKILL.md`, adjust templates/checklists
- **Modify note fields** — edit `skills/paper-analyzer/SKILL.md`, add/remove extraction dimensions
- **Switch models** — configure in `openclaw.json`:

```json
{ "model": "minimax-m2.5" }    // Low cost (~$0–1/run)
{ "model": "claude-opus-4-6" }  // High quality
{ "model": "gpt-4o" }           // Alternative
```

---

## Known Limitations

- **Not real-time**: academic APIs have rate limits (arXiv: 3s/request); full search takes minutes
- **Network policy variance**: some DNS/proxy routes domains to `198.18.x.x` (fake-ip); TrendR has fallback search but coverage may drop
- **Non-frontier model forgetting**: MiniMax M2.5 may occasionally skip Skill files despite 3-layer defense
- **Full-text reading (Basic)**: abstract only; Full mode with Nano-pdf enables PDF deep reading
- **No dual-AI review**: extensible (see paper-distill-mcp dual-review mode)
- **Stability-first scheduling**: Codex/Claude defaults to sequential execution (not full pipeline parallelism)
- **Very large end-to-end scientific orchestration**: consider [K-Dense Web](https://www.k-dense.ai)

---

## Uninstall

```bash
chmod +x uninstall.sh
./uninstall.sh
```

Your Obsidian research data and `~/research/` are preserved.

---

## Credits

- [karpathy/autoresearch](https://github.com/karpathy/autoresearch) — autonomous research loop inspiration
- [paper-distill-mcp](https://github.com/Eclipse-Cj/paper-distill-mcp) — multi-source search architecture reference
- [OpenClaw](https://openclaw.ai) — agent runtime infrastructure

## License

MIT
