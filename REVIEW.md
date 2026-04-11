# TrendR — Project Review & Brief for External Evaluation

> Written by Claude Opus 4.6 after full codebase audit. Intended audience: GPT, Gemini, or any AI evaluating this project.

---

## One-Sentence Summary

TrendR is a **multi-agent literature review automation system** that turns a one-sentence research topic into a structured survey paper (~15KB review + BibTeX) by orchestrating 3 LLM agents across 9 free academic APIs, with an optional real-time web platform hotspot monitoring module using Chrome CDP.

---

## What It Actually Is

TrendR is **not a traditional software project**. It contains zero application code in the conventional sense — no `main.py`, no `index.js`, no compiled binary. Instead, it is:

1. **A set of Markdown skill files** (~2,000 lines total) that serve as executable knowledge for LLM agents — containing API URL templates, CSS selectors, output schemas, and step-by-step procedures
2. **A set of SOUL.md agent personality files** (~300 lines total) defining behavioral constraints for 3 specialized agents
3. **A Python watchdog daemon** (~550 lines) that monitors file timestamps and auto-resumes stuck agent runs
4. **A bash installer** (~700 lines) that registers everything into the host platform (OpenClaw)
5. **Chrome CDP automation scripts** (~150 lines) for browser-based web scraping

The core insight: **LLM agents don't need libraries — they need playbooks.** TrendR treats SKILL.md files as the "source code" that agents execute at runtime by reading and following the instructions.

---

## Architecture Assessment

### What Works Well

**1. The 9-source academic API handbook is genuinely useful.**
`skills/paper-scout/SKILL.md` is a 430-line reference containing tested URL templates, parameter formats, response parsing rules, rate limit info, and fallback strategies for arXiv, Semantic Scholar, OpenAlex, PubMed, CrossRef, DBLP, Europe PMC, bioRxiv, and Papers with Code. All free, no keys required. This is the most valuable asset in the project — it's a real knowledge artifact that any agent on any platform can use.

**2. The multi-agent separation of concerns is clean.**
- `paper-scout`: search only, outputs CSV
- `paper-analyzer`: read only, outputs structured notes
- `review-lead`: orchestrates and writes
Each agent has a clear contract (input files → output files), and the SOUL.md files enforce boundaries ("你不做的事" sections). This makes the pipeline debuggable — you can inspect artifacts between phases.

**3. The supervisor/watchdog solves a real problem.**
LLM agents stall. They forget what they were doing. The `supervisor.py` daemon monitors file timestamps, detects phase mismatches, and auto-injects resume messages via the OpenClaw session API. It has checkpoint detection (looks for `candidates.csv`, `matrix.csv`, `review.md`), cooldown logic, and a max-resume cap. This is production-grade operational tooling for a real failure mode.

**4. The three-layer anti-forgetting mechanism is pragmatically clever.**
Weaker models (MiniMax M2.5) forget to read skill files. TrendR puts "read SKILL.md first" in three places: AGENTS.md, SOUL.md, and the task dispatch message. Redundant by design. This is the kind of defensive engineering you only learn by running agents in production.

**5. The Chrome CDP dual-instance architecture is a genuine discovery.**
Chrome 146 rejects `--remote-debugging-port` on the default user-data-dir. TrendR documents the workaround (separate data dir + cookie sync via macOS Keychain), including the non-obvious insight that Chrome's cookie encryption key is per-application, not per-directory. This is undocumented knowledge.

### What Could Be Better

**1. Tight coupling to OpenClaw.**
Despite the CLAUDE.md/AGENTS.md compatibility layer, the core skills use `web_fetch:`, `exec:`, `sessions_spawn` syntax that is OpenClaw-specific. The API URLs are portable, but the surrounding orchestration glue is not. A truly portable version would express the workflow as a DAG of pure HTTP calls + file I/O, with platform-specific adapters.

**2. The review quality ceiling is LLM-dependent, not system-dependent.**
TrendR automates the *logistics* of literature review (search, dedup, organize, format) but the *intellectual quality* of the final review — taxonomy design, gap identification, critical analysis — is entirely dependent on the underlying model. The system cannot improve a weak model's analytical ability. The review-writer SKILL.md provides a good template, but templates don't create insight.

**3. No validation of review accuracy.**
The quality checklist in `review-writer/SKILL.md` is self-assessed by the same agent that wrote the review. There's no independent verification that citations are real, that claims match paper content, or that the taxonomy is reasonable. A "review-reviewer" agent or cross-validation step would add reliability.

**4. Platform hotspots skill is brittle by nature.**
CSS selectors for Zhihu, Reddit, Xiaohongshu, etc. break whenever these sites update their DOM. The Reddit selectors already needed fixing once (from `shreddit-post` to `shreddit-search-result`). This is inherent to web scraping but means ongoing maintenance.

**5. The watchdog only works with OpenClaw.**
`supervisor.py` sends resume messages via `openclaw agent --session-id`. On Claude Code or Codex, the watchdog is non-functional. This is the hardest piece to port because it requires platform-specific session management APIs.

---

## Novelty & Contributions

| Aspect | Novel? | Comment |
|--------|--------|---------|
| Using LLMs for literature review | No | Many exist (Elicit, Consensus, etc.) |
| Multi-agent pipeline with file-based contracts | Somewhat | Clean implementation of a known pattern |
| 9-source free API handbook | Yes | Most tools use 1-2 sources; this is comprehensive |
| Watchdog auto-resume for stalled agents | Yes | Solves a real operational problem others ignore |
| Anti-forgetting triple-redundancy | Yes | Practical defense for weak models, rarely documented |
| Chrome 146 CDP dual-instance workaround | Yes | Undocumented Chrome security behavior |
| Skills-as-Markdown paradigm | Emerging | Part of a broader trend, TrendR is an early example |

---

## Who Should Use This

- **Researchers** who do frequent literature surveys and want to automate the mechanical parts (search, dedup, formatting)
- **OpenClaw users** who want a turnkey multi-agent research workflow
- **Agent developers** who want to study a real multi-agent system with production failure handling (watchdog, fallbacks, anti-forgetting)
- **Anyone** who wants the 9-source academic API reference — this alone is worth cloning the repo

## Who Should Not Use This

- Anyone expecting peer-review-quality output without human editing
- Anyone without an OpenClaw setup (Claude Code / Codex support is partial)
- Anyone researching topics where API-accessible papers are insufficient (e.g., proprietary industry reports, non-English literature)

---

## Technical Stats

| Metric | Value |
|--------|-------|
| Total Markdown (skills + agents + protocols) | ~3,500 lines |
| Python code (supervisor only) | ~550 lines |
| Bash code (installer + scripts) | ~850 lines |
| Application code (JS/TS/Rust) | 0 lines |
| External dependencies | 0 required (Scrapling, Zotero, Obsidian optional) |
| API keys required | 0 (Semantic Scholar recommended) |
| Agents | 3 (paper-scout, paper-analyzer, review-lead) |
| Skills | 7 (paper-scout, paper-analyzer, review-writer, research-vault, trendr-watchdog, platform-hotspots, chrome-cdp-setup) |
| Academic API sources | 9 |
| Platform hotspot sources | 9 |

---

## Verdict

TrendR is a **serious, production-tested agent system** disguised as a simple research tool. Its real value is not in the output it produces (literature reviews of variable quality) but in the **operational patterns it demonstrates**: file-based agent contracts, anti-stall supervision, defensive anti-forgetting, multi-source fallback chains, and the insight that LLM agents need playbooks more than they need code. The 9-source API handbook and Chrome CDP documentation are independently valuable knowledge artifacts.

The main limitation is platform lock-in to OpenClaw. The compatibility layer helps, but full portability would require rethinking the orchestration layer.

**Rating: 7.5/10** — Strong engineering for its paradigm, genuinely useful API handbook, limited by LLM-dependent output quality and platform coupling.



                                                                                                                                                                                                
⏺ 看完了你的 TrendR 全貌。技术上没问题，甚至很硬核。问题不在项目本身，在包装和传播。                                                                                                            
                                                                                                                                                                                                
  技术 vs lm-wiki 对比                                                                                                                                                                          
                                                                                                                                                                                                
  ┌──────────┬───────────────────────────────────┬──────────────────────────────────────────────┐                                                                                               
  │          │          lm-wiki (44星)           │                 TrendR (9星)                 │                                                                                               
  ├──────────┼───────────────────────────────────┼──────────────────────────────────────────────┤                                                                                               
  │ 技术含量 │ 目录模板 + prompt                 │ 状态机 + 4 agent + 9 API + watchdog + 验证器 │                                                                                               
  ├──────────┼───────────────────────────────────┼──────────────────────────────────────────────┤                                                                                               
  │ 代码量   │ 几乎没有                          │ 2211 行引擎 + 2081 行 skill                  │                                                                                               
  ├──────────┼───────────────────────────────────┼──────────────────────────────────────────────┤                                                                                               
  │ 受众     │ "我也想建知识库" → 人人都觉得需要 │ "我要自动写综述" → 只有科研人懂              │                                                                                               
  ├──────────┼───────────────────────────────────┼──────────────────────────────────────────────┤                                                                                               
  │ 上手门槛 │ clone 就完事                      │ 要理解 A/B/C 深度、9个 API、状态机流程       │                                                                                               
  ├──────────┼───────────────────────────────────┼──────────────────────────────────────────────┤                                                                                               
  │ 一眼看懂 │ ✅ 建文件夹，整理笔记             │ ❌ 需要看完 README 才知道在干嘛              │                                                                                               
  └──────────┴───────────────────────────────────┴──────────────────────────────────────────────┘                                                                                               
                                                                                                                                                                                                
  具体差在哪                                                                                                                                                                                    
                                                                                                                                                                                                
  1. README 前 10 行没有钩子                                                                                                                                                                    
  你的 README 开头是功能介绍。lm-wiki 开头是"把碎片信息变成知识库"——一句话就让人觉得需要。TrendR 应该开头就写：                                                                                 
                                                                                                                                                                                                
  ▎ 一句话输入研究方向，30 分钟后拿到一篇带 BibTeX 的综述。                                                                                                                                     
                                                                                                                                                                                                
  2. 没有 demo gif / 截图                                                                                                                                                                       
  这是最致命的。你有 30 分钟出综述的能力，但没人看到效果。一个 gif 展示「输入关键词 → 跑起来 → 出 review.md」比 19KB 的 README 管用十倍。                                                       
                                                                                                                                                                                                
  3. ARCHITECTURE.md 30KB 吓跑普通用户                                                                                                                                                          
  这是写给开发者看的，但 GitHub 首页和小红书受众大部分是"我想用"而不是"我想懂"。技术文档应该藏在 /docs 里，不是根目录一堆 md。                                                                  
                                                                                                                                                                                                
  4. 受众太窄但没有精准投放                                                                                                                                                                     
  小红书上发 TrendR → 大部分人不做科研，看不懂。应该去：                                                                                                                                        
  - 知乎「研究生」「文献综述」话题                                                                                                                                                              
  - Reddit r/MachineLearning、r/AcademicPhilosophy                                                                                                                                              
  - Twitter/X 英文科研圈（你有 README_EN.md，用起来）                                                                                                                                           
                                                                                                                                                                                                
  5. 入口太多反而迷茫                                                                                                                                                                           
  cli.py / OpenClaw /tr / 平台热点扫描 —— 三个入口。新用户不知道该从哪开始。lm-wiki 就一个入口：bash install.sh，完了。                                                                         
                                                                                                                                                                                                
  建议优先做的 3 件事                                                                                                                                                                           
                                                                                                                                                                                                
  1. 录一个 30 秒 gif：输入 topic → 看到状态流转 → 最终 review.md 打开。放 README 最顶部。                                                                                                      
  2. README 重写前 5 行：一句话说清楚价值，不要上来就列功能。                                                                                                                                   
  3. 去对的地方发：知乎写一篇"我用 AI 30 分钟写完文献综述"，比小红书精准一百倍。                                                                                                                
                                                                                                                                                                                                
  你的项目是真的好东西，就是卖亏了。
