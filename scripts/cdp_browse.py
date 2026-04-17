#!/usr/bin/env python3
"""TrendR CDP browser driver.

Provides a reusable WebSocket-based CDP client for scraping JS-heavy pages.
Requires: websocket-client (available in .venv or /usr/bin/python3 on macOS).

Usage (from CLI):
  python scripts/cdp_browse.py <url> <js_expression> [wait_seconds]

Usage (as library):
  from scripts.cdp_browse import cdp_nav_eval
  papers = cdp_nav_eval("https://huggingface.co/papers?q=...", JS_EXPR, wait=5)
"""

from __future__ import annotations

import json
import sys
import time
import urllib.request
from pathlib import Path

_CDP_HOST = "127.0.0.1"
_CDP_PORT = 19222
_msg_id = 0


def _get_ws():
    """Open a new CDP tab and return its WebSocket URL."""
    try:
        import websocket  # noqa: F401 — checked here to give a clear error
    except ImportError:
        sys.exit(
            "ERROR: websocket-client not found.\n"
            "Fix: use '.venv/bin/python3' or '/usr/bin/python3' (macOS system Python).\n"
            "     .venv/bin/pip install websocket-client"
        )

    base = f"http://{_CDP_HOST}:{_CDP_PORT}"
    req = urllib.request.Request(f"{base}/json/new", method="PUT")
    with urllib.request.urlopen(req, timeout=5) as r:
        return json.loads(r.read())["webSocketDebuggerUrl"]


def _send(ws, method: str, params: dict | None = None) -> dict:
    global _msg_id
    import websocket as _ws_mod  # noqa: F811

    _msg_id += 1
    mid = _msg_id
    ws.send(json.dumps({"id": mid, "method": method, "params": params or {}}))
    deadline = time.time() + 20
    while time.time() < deadline:
        try:
            ws.settimeout(2)
            msg = json.loads(ws.recv())
            if msg.get("id") == mid:
                return msg.get("result", {})
        except Exception:
            break
    return {}


def cdp_nav_eval(url: str, js_expr: str, wait: float = 5.0) -> object:
    """Navigate to url, wait, evaluate js_expr, return the JS return value."""
    import websocket

    ws_url = _get_ws()
    ws = websocket.create_connection(ws_url, timeout=25)
    try:
        _send(ws, "Page.enable")
        _send(ws, "Page.navigate", {"url": url})
        time.sleep(wait)
        result = _send(ws, "Runtime.evaluate", {
            "expression": js_expr,
            "returnByValue": True,
            "awaitPromise": False,
        })
        raw = result.get("result", {}).get("value")
        if isinstance(raw, str):
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                return raw
        return raw
    finally:
        ws.close()


def _detect_python() -> str:
    """Return the Python interpreter path that has websocket-client."""
    repo_root = Path(__file__).resolve().parents[1]
    candidates = [
        str(repo_root / ".venv" / "bin" / "python3"),  # project venv (preferred)
        "/usr/bin/python3",                             # macOS system Python 3.9
        sys.executable,
    ]
    for py in candidates:
        if not Path(py).exists():
            continue
        import subprocess
        rc = subprocess.run(
            [py, "-c", "import websocket"],
            capture_output=True
        ).returncode
        if rc == 0:
            return py
    return sys.executable


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python scripts/cdp_browse.py <url> <js_expr> [wait_sec]")
        sys.exit(1)

    url_arg = sys.argv[1]
    js_arg = sys.argv[2]
    wait_arg = float(sys.argv[3]) if len(sys.argv) > 3 else 5.0

    # Auto-reinvoke with correct Python if current one lacks websocket
    try:
        import websocket  # noqa: F401
    except ImportError:
        correct_py = _detect_python()
        if correct_py != sys.executable:
            import os
            os.execv(correct_py, [correct_py] + sys.argv)
        else:
            sys.exit("ERROR: websocket-client not installed. Run: .venv/bin/pip install websocket-client")

    result = cdp_nav_eval(url_arg, js_arg, wait=wait_arg)
    print(json.dumps(result, ensure_ascii=False, indent=2))
