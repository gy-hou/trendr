---
name: platform-hotspots
description: Collect and summarize Zhihu, Xiaohongshu, X, Reddit, YouTube, GitHub Trending, Hacker News, and Product Hunt hotspots with strict Chrome CDP routing and reproducible extraction commands.
read_when:
  - User asks for Zhihu hot list summaries
  - User asks for Zhihu tech hotspot summaries
  - User asks for Xiaohongshu tech hotspot summaries
  - User asks for X/Twitter hotspot summaries
  - User asks for Reddit hotspot summaries
  - User asks for YouTube hotspot summaries
  - User asks for GitHub trending summaries
  - User asks for Hacker News summaries
  - User asks for Product Hunt summaries
  - User asks for cross-platform hotspot briefs
metadata: {"openclaw": {}}
---

# Platform Hotspots Skill

## Multi-Platform Compatibility

This skill uses `openclaw browser --browser-profile cdp` syntax (OpenClaw native). On other platforms:
- **Claude Code**: Use MCP browser tools (`mcp__Claude_Preview__*`, `mcp__Control_Chrome__*`) or Playwright MCP. The `evaluate --fn '...'` commands are standard JS — run them via your browser tool's evaluate/javascript function.
- **Codex**: Use Playwright, Puppeteer, or any CDP-compatible browser automation.
- **No browser available?** For sites that work without JS (GitHub Trending, Hacker News), use `WebFetch`/`curl` and parse HTML. For JS-heavy sites (Zhihu, X, Reddit), mark as `skipped_no_browser`.

Use this skill to produce structured hotspot summaries from:
- Zhihu current hot list
- Zhihu tech-related hotspot list
- Xiaohongshu tech-related hotspot list
- X (x.com) hotspot list
- Reddit hotspot list
- YouTube tech/AI hotspot list
- GitHub Trending repositories
- Hacker News top stories
- Product Hunt daily products

## Channel Policy (Mandatory)

Always use human Chrome CDP profile:

```bash
openclaw browser --browser-profile cdp ...
```

Do not switch to `openclaw` profile for this skill.

Run one platform step at a time. Do not open many tabs in batch.

For platform sites that may require login/challenge (especially X), always stay on `cdp`.

Tab hygiene is mandatory: every `open` must capture the returned tab id, and close that tab after extraction.

Pattern:

```bash
OPEN_OUT=$(openclaw browser --browser-profile cdp open "<url>")
TAB_ID=$(printf '%s\n' "$OPEN_OUT" | awk '/^id:/{print $2}' | tail -n1)
# ... run snapshot/evaluate extraction ...
openclaw browser --browser-profile cdp close "$TAB_ID"
```

## Preflight

Chrome 146 requires a non-default user-data-dir for `--remote-debugging-port`.
We use `~/.openclaw/browser/cdp-automation` with cookies synced from a real Chrome profile. See `chrome-cdp-setup` skill for full architecture details.

1. Launch the automation Chrome (syncs cookies automatically, skips if already running):

```bash
bash ~/.openclaw/workspace/scripts/start-chrome-cdp.sh
```

If already running, the script exits with `already_listening`.

2. Attach to `cdp`:

```bash
openclaw browser --browser-profile cdp start
```

3. Verify tabs:

```bash
openclaw browser --browser-profile cdp tabs
```

4. If attach fails with `selected page has been closed`:
- Confirm Chrome is running on port 19222: `curl -s http://127.0.0.1:19222/json/version`
- If not, stop and restart: `bash stop-chrome-cdp.sh && bash start-chrome-cdp.sh`
- Retry `start`.

5. If cookies are stale (sites show logged out), re-sync manually:

```bash
bash ~/.openclaw/workspace/scripts/sync-chrome-profile.sh
```

Then restart automation Chrome.

## Step A: Zhihu Current Hot Top 10

Open hot page:

```bash
openclaw browser --browser-profile cdp open https://www.zhihu.com/hot
```

Extract top items:

```bash
openclaw browser --browser-profile cdp evaluate --fn '() => {
  const items = Array.from(document.querySelectorAll(".HotItem")).slice(0, 10);
  return items.map((item, idx) => {
    const title = item.querySelector("h2")?.innerText?.trim()
      || item.querySelector("a")?.innerText?.trim()
      || "";
    const heat = item.querySelector(".HotItem-metrics")?.innerText
      ?.match(/[0-9]+(?:\.[0-9]+)?\s*[万亿]?热度/)?.[0] || null;
    return { rank: idx + 1, title, heat };
  });
}'
```

## Step B: Zhihu Tech Hotspots Top 10

Use search-based tech stream (stable fallback when no dedicated tech-hotboard URL):

```bash
openclaw browser --browser-profile cdp open "https://www.zhihu.com/search?type=content&q=%E7%A7%91%E6%8A%80"
```

Extract top tech discussion items:

```bash
openclaw browser --browser-profile cdp evaluate --fn '() => {
  const out = [];
  const seen = new Set();
  const links = Array.from(document.querySelectorAll("a[href*=\"/question/\"]"));
  for (const a of links) {
    const title = (a.innerText || a.textContent || "").replace(/\s+/g, " ").trim();
    if (!title || title.length < 8) continue;
    if (!/[？?]/.test(title)) continue;
    if (seen.has(title)) continue;
    const card = a.closest(".List-item,.Card.SearchResult-Card") || a.parentElement;
    const txt = (card?.innerText || "").replace(/\s+/g, " ");
    const metric = txt.match(/\d+\s*回答\s*·\s*\d+\s*浏览/)?.[0]
      || txt.match(/赞同\s*[0-9.]+\s*[万千]?/)?.[0]
      || null;
    const comments = txt.match(/\d+\s*条评论/)?.[0] || null;
    const time = txt.match(/(\d{2}-\d{2}|\d{4}-\d{2}-\d{2}|\d+\s*小时前)/)?.[0] || null;
    out.push({ title, metric, comments, time, href: a.href });
    seen.add(title);
    if (out.length >= 10) break;
  }
  return out;
}'
```

## Step C: Xiaohongshu Tech Hotspots Top 10

Try search result first:

```bash
openclaw browser --browser-profile cdp open "https://www.xiaohongshu.com/search_result?keyword=%E7%A7%91%E6%8A%80&source=web_explore_feed"
```

If the page is a skeleton/empty content shell, fallback to `explore` feed:

```bash
openclaw browser --browser-profile cdp open https://www.xiaohongshu.com/explore
```

Extract feed cards:

```bash
openclaw browser --browser-profile cdp evaluate --fn '() => {
  const items = Array.from(document.querySelectorAll(".note-item")).slice(0, 160);
  return items.map((item, idx) => {
    const lines = (item.innerText || "").split("\n").map(s => s.trim()).filter(Boolean);
    const title = lines[0] || "";
    const author = lines[1] || "";
    const heat = lines[2] || "";
    const href = item.querySelector("a[href*=\"/explore/\"]")?.href || null;
    return { idx: idx + 1, title, author, heat, href };
  });
}'
```

Filter to tech-related items by title keywords:

```text
科技, AI, 人工智能, 大模型, Claude, OpenAI, ChatGPT, Gemini,
论文, AIGC, 代码, 编程, 芯片, 算力, 机器人, 量子, 宇树
```

Keep first 10 valid tech items after filtering and de-duplication.

## Step D: X (x.com) Tech/AI Hotspots Top 10

Open one query at a time (no batch opening):

```bash
openclaw browser --browser-profile cdp open "https://x.com/search?q=(AI%20OR%20agent%20OR%20LLM%20OR%20OpenAI%20OR%20Anthropic%20OR%20Gemini)%20(lang%3Aen%20OR%20lang%3Azh)&f=live"
```

Optional query buckets (run only if needed):

```text
A) Labs/accounts:
https://x.com/search?q=(from%3AOpenAI%20OR%20from%3AAnthropicAI%20OR%20from%3AGoogleDeepMind%20OR%20from%3Anvidia)%20(launch%20OR%20release%20OR%20model)&f=live

B) Agent ecosystem:
https://x.com/search?q=(%22AI%20agent%22%20OR%20%22coding%20agent%22%20OR%20LLM)%20(launch%20OR%20benchmark%20OR%20open-source)&f=live
```

Extract visible posts:

```bash
openclaw browser --browser-profile cdp evaluate --fn '() => {
  const out = [];
  const seen = new Set();
  const nodes = Array.from(document.querySelectorAll("article"));
  for (const n of nodes) {
    const txt = (n.innerText || "").replace(/\s+/g, " ").trim();
    if (!txt) continue;
    const lines = txt.split(" ").slice(0, 36).join(" ");
    if (seen.has(lines)) continue;
    const href = n.querySelector("a[href*=\"/status/\"]")?.href || null;
    const metric = txt.match(/\d+(\.\d+)?[KMB]?\s*(views|likes|reposts|replies)/i)?.[0] || null;
    out.push({ snippet: lines, metric, href });
    seen.add(lines);
    if (out.length >= 20) break;
  }
  return out;
}'
```

Keep top 10 tech-relevant items after keyword filtering and de-duplication.

If challenge/login/rate limit appears, do not force retry loops. Mark X as `skipped_with_reason`.

## Step E: Reddit Tech/AI Hotspots Top 10

Open search page:

```bash
openclaw browser --browser-profile cdp open "https://www.reddit.com/search/?q=(AI%20OR%20agent%20OR%20LLM%20OR%20OpenAI%20OR%20Anthropic%20OR%20Gemini)&sort=hot&t=day"
```

Alternative subreddits if needed:

```text
https://www.reddit.com/r/artificial/hot/
https://www.reddit.com/r/MachineLearning/hot/
https://www.reddit.com/r/technology/hot/
```

Extract visible cards (Reddit 2025+ DOM uses `shreddit-search-result` and `faceplate-partial`):

```bash
openclaw browser --browser-profile cdp evaluate --fn '() => {
  const out = [];
  const seen = new Set();

  // Strategy 1: find all comment links and walk up to the nearest result card
  const commentLinks = Array.from(document.querySelectorAll("a[href*=\"/comments/\"]"));
  for (const a of commentLinks) {
    const card = a.closest("shreddit-search-result, faceplate-partial, shreddit-post, article, div[data-testid=\"post-container\"]")
      || a.parentElement?.parentElement?.parentElement;
    if (!card) continue;
    const txt = (card.innerText || "").replace(/\s+/g, " ").trim();
    if (!txt) continue;
    const title = txt.split(" · ")[0]?.slice(0, 220) || txt.slice(0, 220);
    if (!title || title.length < 6 || seen.has(title)) continue;
    const href = a.href || null;
    const score = txt.match(/\b\d+(\.\d+)?[kK]?\s*(upvotes?|points?|votes?)\b/i)?.[0] || null;
    out.push({ title, score, href });
    seen.add(title);
    if (out.length >= 20) break;
  }

  // Strategy 2 fallback: if no results from comment links, try result cards directly
  if (out.length === 0) {
    const cards = Array.from(document.querySelectorAll("shreddit-search-result, faceplate-partial"));
    for (const card of cards) {
      const txt = (card.innerText || "").replace(/\s+/g, " ").trim();
      if (!txt) continue;
      const title = txt.split(" · ")[0]?.slice(0, 220) || txt.slice(0, 220);
      if (!title || title.length < 6 || seen.has(title)) continue;
      const href = card.querySelector("a[href*=\"/r/\"]")?.href
        || card.querySelector("a[href*=\"/comments/\"]")?.href || null;
      const score = txt.match(/\b\d+(\.\d+)?[kK]?\s*(upvotes?|points?|votes?)\b/i)?.[0] || null;
      out.push({ title, score, href });
      seen.add(title);
      if (out.length >= 20) break;
    }
  }

  return out;
}'
```

Keep top 10 tech-relevant items after keyword filtering and de-duplication.

## Step F: YouTube Tech/AI Hotspots Top 10

Open trending entry first:

```bash
openclaw browser --browser-profile cdp open https://www.youtube.com/feed/trending
```

If YouTube redirects to home, switch to AI-focused feed:

1. Capture snapshot and find `AI` tab ref.
2. Click that ref.

```bash
openclaw browser --browser-profile cdp snapshot --compact --limit 220
openclaw browser --browser-profile cdp click <ai_tab_ref>
```

If no `AI` tab exists, fallback to search:

```bash
openclaw browser --browser-profile cdp open "https://www.youtube.com/results?search_query=AI%20agent%20LLM%20news"
```

Extract visible cards:

```bash
openclaw browser --browser-profile cdp evaluate --fn '() => {
  const out = [];
  const seen = new Set();
  const cards = Array.from(document.querySelectorAll("ytd-rich-item-renderer, ytd-video-renderer")).slice(0, 80);
  for (const c of cards) {
    const lines = (c.innerText || "").split("\n").map(s => s.trim()).filter(Boolean);
    if (!lines.length) continue;
    const flat = lines.join(" ");
    if (/Sponsored|Playables|My Ad Center/i.test(flat)) continue;
    const title = lines[1] || lines[0] || "";
    if (!title || title.length < 4 || seen.has(title)) continue;
    const channel = lines[2] || null;
    const heat = lines[3] || null;
    const time = lines[4] || null;
    const link = c.querySelector("a[href*=\"/watch\"], a[href*=\"/shorts\"]")?.href || null;
    out.push({ title, channel, heat, time, link });
    seen.add(title);
    if (out.length >= 20) break;
  }
  return out;
}'
```

Keep top 10 tech-relevant items after filtering and de-duplication.

## Step G: GitHub Trending Top 10

Open trending repositories:

```bash
openclaw browser --browser-profile cdp open https://github.com/trending
```

Extract top repositories:

```bash
openclaw browser --browser-profile cdp evaluate --fn '() => {
  const rows = Array.from(document.querySelectorAll("article.Box-row")).slice(0, 10);
  return rows.map((row, idx) => {
    const repo = (row.querySelector("h2 a")?.textContent || "")
      .replace(/\s+/g, " ")
      .replace(/\//g, " / ")
      .trim();
    const href = row.querySelector("h2 a")?.href || null;
    const desc = (row.querySelector("p")?.textContent || "").replace(/\s+/g, " ").trim() || null;
    const lang = (row.querySelector("[itemprop=\"programmingLanguage\"]")?.textContent || "")
      .replace(/\s+/g, " ")
      .trim() || null;
    const stars = (row.querySelector("a[href$=\"/stargazers\"]")?.textContent || "")
      .replace(/\s+/g, " ")
      .trim() || null;
    const forks = (row.querySelector("a[href$=\"/forks\"]")?.textContent || "")
      .replace(/\s+/g, " ")
      .trim() || null;
    const starsToday = (row.textContent || "").match(/\d[\d,]*\s+stars\s+today/i)?.[0] || null;
    return { rank: idx + 1, repo, desc, lang, stars, forks, stars_today: starsToday, link: href };
  });
}'
```

## Step H: Hacker News Top 10

Open HN front page:

```bash
openclaw browser --browser-profile cdp open https://news.ycombinator.com/
```

Extract top items:

```bash
openclaw browser --browser-profile cdp evaluate --fn '() => {
  const rows = Array.from(document.querySelectorAll("tr.athing")).slice(0, 10);
  return rows.map((row, idx) => {
    const titleLink = row.querySelector(".titleline a");
    const sub = row.nextElementSibling;
    const metaText = (sub?.innerText || "").replace(/\s+/g, " ").trim();
    const points = metaText.match(/\d+\s+points?/)?.[0] || null;
    const comments = metaText.match(/\d+\s+comments?/)?.[0] || (metaText.includes("discuss") ? "0 comments" : null);
    return {
      rank: idx + 1,
      title: (titleLink?.textContent || "").trim(),
      points,
      comments,
      link: titleLink?.href || null
    };
  });
}'
```

## Step I: Product Hunt Top 10

Open Product Hunt home first:

```bash
openclaw browser --browser-profile cdp open https://www.producthunt.com/
```

If home feed is not parseable, fallback to AI topic:

```bash
openclaw browser --browser-profile cdp open https://www.producthunt.com/topics/artificial-intelligence
```

Extract visible products:

```bash
openclaw browser --browser-profile cdp evaluate --fn '() => {
  const out = [];
  const seen = new Set();
  const clean = (s) => (s || "")
    .replace(/([a-z\.])([A-Z])/g, "$1 $2")
    .replace(/\s+/g, " ")
    .trim();

  for (const a of document.querySelectorAll("main a[href]")) {
    const href = a.getAttribute("href") || "";
    const m = href.match(/\/products\/([^/?#]+)/);
    if (!m) continue;
    const slug = m[1];
    if (href.includes("/reviews") || seen.has(slug)) continue;

    const card = a.closest("article, li, section, div");
    if (!card) continue;
    const reviewLink = card.querySelector(`a[href*="/products/${slug}/reviews"]`);
    if (!reviewLink) continue;

    let title = (a.textContent || "").replace(/\s+/g, " ").trim();
    if (!title) continue;
    title = title
      .replace(/Launched this month/gi, " ")
      .replace(/APIs and tools for building AI products/gi, " ")
      .replace(/A family of foundational AI models/gi, " ")
      .replace(/Get answers\. Find inspiration\. Be more productive\./gi, " ")
      .replace(/How people build software/gi, " ")
      .replace(/The all-in-one workspace/gi, " ")
      .replace(/The collaborative interface design tool/gi, " ")
      .replace(/The frontend cloud\. Creators of Next\.js\./gi, " ");
    title = clean(title) || slug;

    const txt = (card.innerText || "").replace(/\s+/g, " ").trim();
    const rating = txt.match(/\b\d\.\d\b/)?.[0] || null;
    const reviews = (reviewLink.textContent || "").replace(/\s+/g, " ").trim() || null;

    out.push({
      rank: out.length + 1,
      title,
      rating,
      reviews,
      link: new URL(`/products/${slug}`, location.origin).href
    });
    seen.add(slug);
    if (out.length >= 10) break;
  }
  return out;
}'
```

## Output Format

Output should include:

1. `Zhihu Current Hot Top 10`:
- `rank`
- `title`
- `heat`

2. `Zhihu Tech Hotspots Top 10`:
- `rank`
- `title`
- `metric` (answers/views or upvotes)
- `time`

3. `Xiaohongshu Tech Hotspots Top 10`:
- `rank`
- `title`
- `author`
- `heat`

4. `X Hotspots Top 10`:
- `rank`
- `snippet/title`
- `metric` (if visible)
- `link`

5. `Reddit Hotspots Top 10`:
- `rank`
- `title`
- `score` (if visible)
- `link`

6. `YouTube Hotspots Top 10`:
- `rank`
- `title`
- `channel`
- `heat` (views/play count if visible)
- `time`
- `link`

7. `GitHub Trending Top 10`:
- `rank`
- `repo`
- `lang`
- `stars_today`
- `stars`
- `link`

8. `Hacker News Top 10`:
- `rank`
- `title`
- `points`
- `comments`
- `link`

9. `Product Hunt Top 10`:
- `rank`
- `title`
- `rating` (if visible)
- `reviews` (if visible)
- `link`

10. `Cross-platform Tech Takeaways`:
- 3 concise bullets.

## Reliability Rules

- Never fabricate missing items.
- If fewer than 10 valid records are available, return actual count and mark `insufficient_items`.
- If one platform fails, continue the other platforms and report the failure reason.
- For X challenge/rate-limit/login walls, return `skipped_with_reason` and continue remaining platforms.
- For YouTube redirect/region limits, use AI-tab or search fallback and continue. If still unavailable, return `skipped_with_reason`.
- For GitHub/Product Hunt/HN regional or anti-bot interstitials, return `skipped_with_reason` and continue.
