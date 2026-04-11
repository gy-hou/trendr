"""Independent hotspot collection flow for TrendR Lite profile.

The Lite flow supports a two-layer configuration model:
1) public template (shareable)
2) private user config (not intended for upload)

Private keywords are used for ranking/filtering but are not persisted verbatim
to run artifacts.
"""

from __future__ import annotations

import json
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_CONFIG_ROOT = Path.home() / ".trendr" / "hotspots"
DEFAULT_TEMPLATE_PATH = DEFAULT_CONFIG_ROOT / "template.json"
DEFAULT_PRIVATE_PATH = DEFAULT_CONFIG_ROOT / "private.json"
DEFAULT_SESSION_PATH = DEFAULT_CONFIG_ROOT / "session.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _resolve_path(path: Path | str) -> Path:
    return Path(path).expanduser().resolve()


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _merge_dict(base: dict, override: dict) -> dict:
    result = dict(base)
    for key, value in override.items():
        if isinstance(result.get(key), dict) and isinstance(value, dict):
            result[key] = _merge_dict(result[key], value)
        else:
            result[key] = value
    return result


def _normalize_keywords(value) -> list[str]:
    if not isinstance(value, list):
        return []
    out: list[str] = []
    seen: set[str] = set()
    for raw in value:
        token = str(raw or "").strip()
        key = token.lower()
        if not token or key in seen:
            continue
        seen.add(key)
        out.append(token)
    return out


def default_hotspots_template() -> dict:
    """Return a shareable default hotspots template."""
    return {
        "version": 1,
        "profile": "lite",
        "topic": "AI agents and LLM ecosystem",
        "description": "Public template for TrendR Lite hotspots. Keep personal preferences in private.json.",
        "keywords": ["AI", "agent", "LLM", "OpenAI", "Anthropic", "Gemini"],
        "platforms": [
            {"id": "hackernews", "enabled": True, "collector": "http"},
            {"id": "github_trending", "enabled": True, "collector": "http"},
            {"id": "reddit", "enabled": True, "collector": "http"},
            {"id": "producthunt", "enabled": True, "collector": "http"},
            {"id": "zhihu_hot", "enabled": False, "collector": "browser_cdp"},
            {"id": "zhihu_tech", "enabled": False, "collector": "browser_cdp"},
            {"id": "xiaohongshu_tech", "enabled": False, "collector": "browser_cdp"},
            {"id": "x_search", "enabled": False, "collector": "browser_cdp"},
            {"id": "youtube_tech", "enabled": False, "collector": "browser_cdp"},
        ],
        "session": {
            "persist": True,
            "browser_profile": "cdp",
            "store_hint": "~/.openclaw/browser/cdp-automation",
        },
    }


def default_hotspots_private_stub() -> dict:
    """Return a private config skeleton for per-user interests/session hints."""
    return {
        "topic": "",
        "keywords": [],
        "platforms": [],
        "session": {
            "persist": True,
            "browser_profile": "cdp",
            "note": "Fill this file with personal interests. Do not upload it to public repos.",
        },
        "upload": {
            "hide_private_keywords": True,
            "hide_private_accounts": True,
        },
        "accounts": {
            "x": {"enabled": False, "cookies_ref": ""},
            "zhihu": {"enabled": False, "cookies_ref": ""},
            "xiaohongshu": {"enabled": False, "cookies_ref": ""},
        },
    }


def write_hotspots_template(path: Path | str, force: bool = False) -> Path:
    target = _resolve_path(path)
    if target.exists() and not force:
        return target
    _write_json(target, default_hotspots_template())
    return target


def write_hotspots_private_stub(path: Path | str, force: bool = False) -> Path:
    target = _resolve_path(path)
    if target.exists() and not force:
        return target
    _write_json(target, default_hotspots_private_stub())
    return target


class HotspotsRunner:
    """Collect cross-platform hotspots in an independent Lite workflow."""

    USER_AGENT = "TrendR-Lite/2.1 (+https://github.com/gy-hou/trendr)"
    SUPPORTED_COLLECTORS = ("hackernews", "github_trending", "reddit", "producthunt")

    def __init__(
        self,
        project_dir: Path,
        topic: str | None = None,
        per_source_limit: int = 10,
        timeout_sec: int = 12,
        template_path: Path | str | None = None,
        private_path: Path | str | None = None,
        session_path: Path | str | None = None,
        use_private_config: bool = True,
        auto_init_config: bool = True,
    ):
        self.project_dir = _resolve_path(project_dir)
        self.per_source_limit = max(1, per_source_limit)
        self.timeout_sec = max(5, timeout_sec)
        self.logs_dir = self.project_dir / "logs"
        self.logs_dir.mkdir(parents=True, exist_ok=True)

        self.template_path = (
            _resolve_path(template_path) if template_path is not None else DEFAULT_TEMPLATE_PATH
        )
        self.private_path = (
            _resolve_path(private_path) if private_path is not None else DEFAULT_PRIVATE_PATH
        )
        self.session_path = (
            _resolve_path(session_path) if session_path is not None else DEFAULT_SESSION_PATH
        )

        if auto_init_config:
            write_hotspots_template(self.template_path, force=False)
            if use_private_config:
                write_hotspots_private_stub(self.private_path, force=False)

        self.template_cfg = _read_json(self.template_path) or default_hotspots_template()
        self.private_cfg = _read_json(self.private_path) if use_private_config else {}
        self.config = _merge_dict(self.template_cfg, self.private_cfg)

        if topic and topic.strip():
            self.config["topic"] = topic.strip()
        self.topic = str(self.config.get("topic") or "AI agents and LLM ecosystem")

        self.public_keywords = _normalize_keywords(self.template_cfg.get("keywords"))
        self.private_keywords = _normalize_keywords(self.private_cfg.get("keywords"))
        self.keywords = _normalize_keywords(self.public_keywords + self.private_keywords)

        self.enabled_platforms = self._resolve_platforms(self.config.get("platforms"))

        session_cfg = self.config.get("session", {}) if isinstance(self.config.get("session"), dict) else {}
        self.persist_session = bool(session_cfg.get("persist", True))
        self.session_browser_profile = str(session_cfg.get("browser_profile") or "cdp")

    @property
    def raw_path(self) -> Path:
        return self.project_dir / "hotspots_raw.json"

    @property
    def summary_path(self) -> Path:
        return self.project_dir / "hotspots_summary.json"

    @property
    def report_path(self) -> Path:
        return self.project_dir / "hotspots_report.md"

    def run(self) -> dict:
        previous_session = self._load_session() if self.persist_session else {}
        session_reused = bool(previous_session)

        source_results: list[dict] = []
        all_items: list[dict] = []

        collector_map = {
            "hackernews": self._fetch_hackernews,
            "github_trending": self._fetch_github_trending,
            "reddit": self._fetch_reddit,
            "producthunt": self._fetch_producthunt,
        }

        platforms = self.enabled_platforms or list(self.SUPPORTED_COLLECTORS)
        for source_name in platforms:
            fn = collector_map.get(source_name)
            if fn is None:
                source_results.append(
                    {
                        "source": source_name,
                        "status": "unsupported",
                        "count": 0,
                        "error": "collector_not_implemented_in_lite_runner",
                    }
                )
                continue
            try:
                items = fn()
                source_results.append(
                    {
                        "source": source_name,
                        "status": "ok",
                        "count": len(items),
                    }
                )
                all_items.extend(items)
            except Exception as e:
                source_results.append(
                    {
                        "source": source_name,
                        "status": "error",
                        "count": 0,
                        "error": str(e),
                    }
                )

        deduped_items = self._dedupe_items(all_items)
        selected_items, keyword_meta = self._apply_keyword_filter(deduped_items)
        top_items = selected_items[: self.per_source_limit * 4]

        payload = {
            "generated_at": _now_iso(),
            "topic": self.topic,
            "project": self.project_dir.name,
            "source_runs": source_results,
            "item_count_raw": len(all_items),
            "item_count_deduped": len(deduped_items),
            "item_count_selected": len(selected_items),
            "item_count_output": len(top_items),
            "items": top_items,
            "keyword_filter": keyword_meta,
            "privacy": {
                "private_config_loaded": bool(self.private_cfg),
                "private_keywords_hidden": True,
                "private_keyword_count": len(self.private_keywords),
            },
            "session": {
                "persist": self.persist_session,
                "reused": session_reused,
                "browser_profile": self.session_browser_profile,
            },
        }
        self.raw_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

        summary = self._build_summary(payload)
        self.summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
        self.report_path.write_text(self._build_report_markdown(payload, summary), encoding="utf-8")

        if self.persist_session:
            self._save_session(previous_session, source_results)

        return {
            "status": "completed",
            "project_dir": str(self.project_dir),
            "raw_path": str(self.raw_path),
            "summary_path": str(self.summary_path),
            "report_path": str(self.report_path),
            "item_count": len(top_items),
            "sources_ok": sum(1 for x in source_results if x["status"] == "ok"),
            "sources_total": len(source_results),
            "session_reused": session_reused,
            "template_path": str(self.template_path),
            "private_path": str(self.private_path),
            "session_path": str(self.session_path),
        }

    def _resolve_platforms(self, value) -> list[str]:
        if not isinstance(value, list):
            return list(self.SUPPORTED_COLLECTORS)

        out: list[str] = []
        seen: set[str] = set()
        for row in value:
            platform_id = ""
            enabled = True
            if isinstance(row, str):
                platform_id = row.strip()
            elif isinstance(row, dict):
                platform_id = str(row.get("id") or "").strip()
                enabled = bool(row.get("enabled", True))
            if not platform_id or not enabled:
                continue
            key = platform_id.lower()
            if key in seen:
                continue
            seen.add(key)
            out.append(platform_id)

        return out

    def _apply_keyword_filter(self, items: list[dict]) -> tuple[list[dict], dict]:
        if not self.keywords:
            return (
                items,
                {
                    "enabled": False,
                    "public_keyword_count": len(self.public_keywords),
                    "private_keyword_count": len(self.private_keywords),
                    "matched_items": len(items),
                    "fallback_to_unfiltered": False,
                },
            )

        needles = [k.lower() for k in self.keywords]
        matched: list[dict] = []
        for item in items:
            haystack = f"{item.get('title', '')} {item.get('url', '')}".lower()
            if any(n in haystack for n in needles):
                matched.append(item)

        if matched:
            return (
                matched,
                {
                    "enabled": True,
                    "public_keyword_count": len(self.public_keywords),
                    "private_keyword_count": len(self.private_keywords),
                    "matched_items": len(matched),
                    "fallback_to_unfiltered": False,
                },
            )

        return (
            items,
            {
                "enabled": True,
                "public_keyword_count": len(self.public_keywords),
                "private_keyword_count": len(self.private_keywords),
                "matched_items": 0,
                "fallback_to_unfiltered": True,
            },
        )

    def _http_get(self, url: str) -> str:
        request = urllib.request.Request(
            url,
            headers={"User-Agent": self.USER_AGENT, "Accept": "*/*"},
            method="GET",
        )
        with urllib.request.urlopen(request, timeout=self.timeout_sec) as response:
            return response.read().decode("utf-8", errors="replace")

    def _fetch_hackernews(self) -> list[dict]:
        ids_raw = self._http_get("https://hacker-news.firebaseio.com/v0/topstories.json")
        story_ids = json.loads(ids_raw)
        if not isinstance(story_ids, list):
            return []

        items: list[dict] = []
        for story_id in story_ids[: self.per_source_limit * 3]:
            try:
                item_raw = self._http_get(
                    f"https://hacker-news.firebaseio.com/v0/item/{int(story_id)}.json"
                )
                item = json.loads(item_raw)
            except Exception:
                continue
            if not isinstance(item, dict):
                continue
            title = (item.get("title") or "").strip()
            if not title:
                continue
            url = item.get("url") or f"https://news.ycombinator.com/item?id={item.get('id')}"
            items.append(
                {
                    "source": "hackernews",
                    "title": title,
                    "url": url,
                    "score": int(item.get("score") or 0),
                    "meta": {
                        "comments": int(item.get("descendants") or 0),
                        "id": item.get("id"),
                    },
                }
            )
            if len(items) >= self.per_source_limit:
                break
        return items

    def _fetch_github_trending(self) -> list[dict]:
        html = self._http_get("https://github.com/trending")
        blocks = re.findall(r"<article class=\"Box-row\".*?</article>", html, flags=re.DOTALL)
        items: list[dict] = []
        for block in blocks[: self.per_source_limit * 2]:
            repo_match = re.search(r"href=\"/([^\"/]+/[^\"/]+)\"", block)
            if not repo_match:
                continue
            repo = repo_match.group(1).strip()
            title = repo
            stars_match = re.search(r"([0-9,]+)\s*stars today", block)
            stars_today = stars_match.group(1) if stars_match else None
            items.append(
                {
                    "source": "github_trending",
                    "title": title,
                    "url": f"https://github.com/{repo}",
                    "score": 0,
                    "meta": {
                        "stars_today": stars_today,
                    },
                }
            )
            if len(items) >= self.per_source_limit:
                break
        return items

    def _fetch_reddit(self) -> list[dict]:
        subreddit_urls = [
            "https://www.reddit.com/r/MachineLearning/hot.json?limit=15",
            "https://www.reddit.com/r/artificial/hot.json?limit=15",
        ]
        items: list[dict] = []
        for url in subreddit_urls:
            try:
                payload = json.loads(self._http_get(url))
            except Exception:
                continue

            children = (
                payload.get("data", {}).get("children", [])
                if isinstance(payload, dict)
                else []
            )
            for child in children:
                data = child.get("data", {}) if isinstance(child, dict) else {}
                title = (data.get("title") or "").strip()
                if not title:
                    continue
                permalink = data.get("permalink") or ""
                full_url = f"https://www.reddit.com{permalink}" if permalink else data.get("url")
                items.append(
                    {
                        "source": "reddit",
                        "title": title,
                        "url": full_url,
                        "score": int(data.get("score") or 0),
                        "meta": {
                            "subreddit": data.get("subreddit"),
                            "comments": int(data.get("num_comments") or 0),
                        },
                    }
                )
                if len(items) >= self.per_source_limit:
                    return items
        return items

    def _fetch_producthunt(self) -> list[dict]:
        xml = self._http_get("https://www.producthunt.com/feed")
        item_blocks = re.findall(r"<item>(.*?)</item>", xml, flags=re.DOTALL | re.IGNORECASE)
        items: list[dict] = []
        for block in item_blocks[: self.per_source_limit * 2]:
            title_match = re.search(r"<title><!\[CDATA\[(.*?)\]\]></title>", block, flags=re.DOTALL)
            if not title_match:
                title_match = re.search(r"<title>(.*?)</title>", block, flags=re.DOTALL)
            link_match = re.search(r"<link>(.*?)</link>", block, flags=re.DOTALL)
            if not title_match:
                continue
            title = re.sub(r"\s+", " ", title_match.group(1)).strip()
            link = link_match.group(1).strip() if link_match else ""
            items.append(
                {
                    "source": "producthunt",
                    "title": title,
                    "url": link,
                    "score": 0,
                    "meta": {},
                }
            )
            if len(items) >= self.per_source_limit:
                break
        return items

    def _dedupe_items(self, items: list[dict]) -> list[dict]:
        seen: set[str] = set()
        deduped: list[dict] = []
        for item in items:
            key = (
                (item.get("url") or "").strip().lower()
                or (item.get("title") or "").strip().lower()
            )
            if not key or key in seen:
                continue
            seen.add(key)
            deduped.append(item)
        return deduped

    def _load_session(self) -> dict:
        return _read_json(self.session_path)

    def _save_session(self, previous: dict, source_results: list[dict]) -> None:
        run_count = int(previous.get("run_count", 0) or 0) + 1
        payload = {
            "version": 1,
            "updated_at": _now_iso(),
            "run_count": run_count,
            "browser_profile": self.session_browser_profile,
            "enabled_platforms": [x.get("source") for x in source_results if x.get("source")],
            "sources_ok": [x["source"] for x in source_results if x.get("status") == "ok"],
            "sources_failed": [
                {"source": x["source"], "status": x.get("status"), "error": x.get("error")}
                for x in source_results
                if x.get("status") != "ok"
            ],
        }
        _write_json(self.session_path, payload)

    def _build_summary(self, payload: dict) -> dict:
        items = payload.get("items", [])
        by_source: dict[str, int] = {}
        for item in items:
            source = item.get("source", "unknown")
            by_source[source] = by_source.get(source, 0) + 1

        return {
            "generated_at": payload.get("generated_at"),
            "topic": payload.get("topic"),
            "sources_ok": [x["source"] for x in payload.get("source_runs", []) if x.get("status") == "ok"],
            "sources_failed": [
                {"source": x["source"], "status": x.get("status"), "error": x.get("error", "unknown")}
                for x in payload.get("source_runs", [])
                if x.get("status") != "ok"
            ],
            "item_count": len(items),
            "item_count_by_source": by_source,
            "top_titles": [item.get("title", "N/A") for item in items[:10]],
            "keyword_filter": payload.get("keyword_filter", {}),
            "privacy": payload.get("privacy", {}),
            "session": payload.get("session", {}),
        }

    def _build_report_markdown(self, payload: dict, summary: dict) -> str:
        lines = []
        lines.append("# TrendR Lite Hotspots Report")
        lines.append("")
        lines.append(f"- Generated: {payload.get('generated_at')}")
        lines.append(f"- Topic: {payload.get('topic')}")
        lines.append(f"- Project: {payload.get('project')}")
        lines.append(f"- Sources OK: {len(summary.get('sources_ok', []))}")
        lines.append(f"- Total Items: {summary.get('item_count', 0)}")
        session_info = summary.get("session", {})
        lines.append(f"- Session Reused: {bool(session_info.get('reused', False))}")
        lines.append(f"- Browser Profile: {session_info.get('browser_profile', 'cdp')}")
        kf = summary.get("keyword_filter", {})
        lines.append(
            "- Keyword Filter: "
            f"enabled={bool(kf.get('enabled'))}, "
            f"matched={int(kf.get('matched_items', 0))}, "
            f"fallback={bool(kf.get('fallback_to_unfiltered', False))}"
        )
        lines.append("")

        failed = summary.get("sources_failed", [])
        if failed:
            lines.append("## Source Warnings")
            for row in failed:
                lines.append(
                    f"- `{row.get('source')}` ({row.get('status', 'unknown')}): "
                    f"{row.get('error')}"
                )
            lines.append("")

        lines.append("## Top Hotspots")
        lines.append("")
        lines.append("| # | Source | Title | URL |")
        lines.append("|---|---|---|---|")
        for idx, item in enumerate(payload.get("items", [])[:40], start=1):
            source = (item.get("source") or "N/A").replace("|", "/")
            title = (item.get("title") or "N/A").replace("|", "/")
            url = item.get("url") or ""
            lines.append(f"| {idx} | {source} | {title} | {url} |")
        lines.append("")
        return "\n".join(lines)
