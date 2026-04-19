---
name: chrome-cdp-setup
description: Chrome 146+ CDP remote debugging architecture — dual-instance setup, cookie sync, profile isolation, and troubleshooting "Allow remote debugging" popups.
read_when:
  - Setting up Chrome remote debugging for automation
  - Troubleshooting "Allow remote debugging" popup
  - Troubleshooting "selected page has been closed" errors
  - Configuring openclaw browser profiles
  - Launching Chrome with CDP debug port
  - Cookie/session sync between Chrome profiles
  - Running multiple Chrome instances simultaneously
metadata: {"openclaw": {}}
---

# Chrome CDP Setup (Chrome 146+)

## Runtime Router（必读）

识别当前 runtime，只读取对应 sibling，另一方休眠：

- `openclaw`    → 本文件内原有指令块仍然有效（`openclaw browser --browser-profile cdp`）
- `claude-code` → **跳过本文件的指令块**，读 `./claude-code.md` 获取 MCP chrome server 安装和使用方式
- `codex` / `cli` → **跳过本文件的指令块**，读 `./codex.md` 获取 Codex CDP / `scripts/cdp_browse.py` 使用方式

本节之后的章节描述 **共享知识**（CDP 架构、Chrome 配置约束）。指令块保持现状（OpenClaw 语法），Claude Code 读者请切换到 `./claude-code.md`，Codex/CLI 读者请切换到 `./codex.md`。

## Core Constraint

Chrome 146 introduced a hard security rule:

> `--remote-debugging-port` is REJECTED when `--user-data-dir` points to the **default** Chrome directory (`~/Library/Application Support/Google/Chrome`).

Error message: `DevTools remote debugging requires a non-default data directory. Specify this using --user-data-dir.`

This means you **cannot** enable CDP debugging on the user's daily Chrome profile directly. Any attempt triggers:
- "Allow remote debugging?" popup (repeated per CDP client connection)
- `selected page has been closed` errors (when using `existing-session` transport)
- `existing-session attach timed out` errors

## Architecture: Dual Chrome Instances

The solution is two Chrome instances side by side:

| Instance | Purpose | user-data-dir | Debug Port | Profile |
|----------|---------|---------------|------------|---------|
| **Daily Chrome** | User's normal browsing | `~/Library/Application Support/Google/Chrome` (default) | None | All user profiles |
| **Automation Chrome** | CDP automation | `~/.openclaw/browser/cdp-users/<user-key>` (recommended) or legacy `~/.openclaw/browser/cdp-automation` | 19222 | Default only (cookies synced from real profile) |

Both appear in the macOS Dock. They can run simultaneously because they use different `user-data-dir` paths.

## Cookie Sync Strategy

The automation Chrome uses a custom `user-data-dir` but needs login sessions from the real profile. macOS Chrome encrypts cookies using a keychain entry (`Chrome Safe Storage`) that is **per-application, not per-user-data-dir**. This means copied cookies decrypt correctly in the custom directory.

Synced files (from source profile to the dedicated automation store under `Default/`):

| File/Directory | What it carries |
|----------------|-----------------|
| `Cookies`, `Cookies-journal` | Site login sessions |
| `Login Data`, `Login Data-journal` | Saved passwords |
| `Web Data`, `Web Data-journal` | Autofill, payment methods |
| `Local Storage/` | Site-specific localStorage |
| `Session Storage/` | Session-scoped storage |
| `IndexedDB/` | Structured client-side data |
| `Sessions/` | Tab restore sessions |

**Do NOT sync `Local State`** — it contains profile registry info and would re-create extra profiles in the custom directory.

## Scripts

### start-chrome-cdp.sh

Location: `~/.openclaw/workspace/scripts/start-chrome-cdp.sh`

```bash
bash ~/.openclaw/workspace/scripts/start-chrome-cdp.sh
```

This default path keeps existing local users on the legacy `19222 + ~/.openclaw/browser/cdp-automation` setup.

Per-user isolation for a fresh user:

```bash
TRENDR_CDP_USER=<user-key> bash ~/.openclaw/workspace/scripts/start-chrome-cdp.sh
```

- Syncs cookies from real profile before launch (calls `sync-chrome-profile.sh`)
- Launches Chrome with `--remote-debugging-port=19222` and custom user-data-dir
- Existing local users keep the legacy `~/.openclaw/browser/cdp-automation` store
- New users should get a dedicated store under `~/.openclaw/browser/cdp-users/<user-key>`
- Idempotent: exits with `already_listening:19222` if Chrome is already up
- Waits up to 10s for CDP endpoint to be ready
- Configurable via env vars: `TRENDR_CDP_PORT`, `TRENDR_CDP_DATADIR`, `TRENDR_CHROME_PROFILE`, `TRENDR_CDP_USER`

### stop-chrome-cdp.sh

```bash
bash ~/.openclaw/workspace/scripts/stop-chrome-cdp.sh
```

- Kills the Chrome process listening on port 19222
- Graceful `kill` first, then `kill -9` if needed

### sync-chrome-profile.sh

```bash
bash ~/.openclaw/workspace/scripts/sync-chrome-profile.sh
```

- Copies auth/session files from a real Chrome profile to the active automation store's `Default/`
- Auto-detects the first non-Default profile, or specify: `sync-chrome-profile.sh "Profile 1"`
- Called automatically by `start-chrome-cdp.sh`
- Run manually if cookies become stale (sites show logged out)

## openclaw.json Browser Config

```json
{
  "browser": {
    "enabled": true,
    "attachOnly": true,
    "defaultProfile": "cdp",
    "profiles": {
      "cdp": {
        "cdpUrl": "http://127.0.0.1:19222",
        "attachOnly": true,
        "color": "#00AA00"
      }
    }
  }
}
```

Key points:
- Only ONE browser profile (`cdp`). Do not add `user` / `openclaw` / `existing-session` profiles.
- Transport is `cdp` (direct WebSocket), NOT `existing-session` (which triggers the popup).
- `attachOnly: true` — never launch Chrome automatically; always use the start script.
- Browser calls must always include `--browser-profile cdp`; never use an empty browser profile.
- Tell the user they can sign in inside the dedicated agent Chrome to the sites they want TrendR to read later.

## Profile Hygiene for the Automation Store

The custom `user-data-dir` should contain only a single `Default` profile. If extra profiles appear (from a stale `Local State` copy), clean them:

```bash
# Remove extra profile dirs
rm -rf ~/.openclaw/browser/cdp-automation/Profile\ *
rm -rf ~/.openclaw/browser/cdp-automation/Guest\ Profile

# Clean Local State
python3 -c "
import json
path = '$HOME/.openclaw/browser/cdp-automation/Local State'
ls = json.load(open(path))
ls['profile']['info_cache'] = {k: v for k, v in ls['profile']['info_cache'].items() if k == 'Default'}
json.dump(ls, open(path, 'w'), indent=2)
"
```

## Troubleshooting

### "Allow remote debugging?" popup keeps appearing

**Cause**: Something is connecting to a Chrome instance that was NOT launched with `--remote-debugging-port`.

**Fix**:
1. Check for stale profiles in `openclaw.json` — remove any `existing-session` or port-9222 profiles
2. Ensure daily Chrome has NO debug port (launched normally)
3. Ensure automation Chrome was launched via `start-chrome-cdp.sh` (has `--remote-debugging-port=19222`)

### "selected page has been closed"

**Cause**: CDP client connected to a tab that no longer exists (tab was closed or navigated away).

**Fix**:
1. Always capture tab ID after `open` and close it after extraction
2. Do not batch-open multiple tabs
3. Pattern:
```bash
OPEN_OUT=$(openclaw browser --browser-profile cdp open "<url>")
TAB_ID=$(printf '%s\n' "$OPEN_OUT" | awk '/^id:/{print $2}' | tail -n1)
# ... extract data ...
openclaw browser --browser-profile cdp close "$TAB_ID"
```

### "existing-session attach timed out"

**Cause**: Using `existing-session` transport instead of direct `cdp`.

**Fix**: Ensure `openclaw.json` has `cdpUrl` set, not `existing-session`. The `cdp` profile should use `"cdpUrl": "http://127.0.0.1:19222"`.

### CDP endpoint not responding after Chrome launch

**Cause**: Chrome started but debug port didn't bind (often due to stale lock files).

**Fix**:
```bash
# Kill all Chrome, clean locks, restart
bash stop-chrome-cdp.sh
pkill -9 -f "Google Chrome" 2>/dev/null
rm -f ~/Library/Application\ Support/Google/Chrome/SingletonLock
rm -f ~/Library/Application\ Support/Google/Chrome/SingletonSocket
rm -f ~/Library/Application\ Support/Google/Chrome/SingletonCookie
rm -f ~/.openclaw/browser/cdp-automation/SingletonLock
rm -f ~/.openclaw/browser/cdp-automation/SingletonSocket
rm -f ~/.openclaw/browser/cdp-automation/SingletonCookie
bash start-chrome-cdp.sh
```

### Cookies stale (sites show logged out in automation Chrome)

**Cause**: Cookies were synced at launch time but have since expired or been refreshed in the daily Chrome.

**Fix**:
```bash
bash stop-chrome-cdp.sh
bash sync-chrome-profile.sh
bash start-chrome-cdp.sh
```

### Two Chrome instances can't coexist

**Cause**: Same `user-data-dir` used by both (SingletonLock conflict).

**Fix**: Verify the two instances use different directories:
```bash
ps aux | grep '[G]oogle Chrome.app/Contents/MacOS/Google Chrome' | grep -v Helper
```
- Daily Chrome: no `--user-data-dir` flag (uses default)
- Automation Chrome: `--user-data-dir=~/.openclaw/browser/cdp-automation`

## Diagnostic Commands

```bash
# Port check
lsof -nP -iTCP -sTCP:LISTEN | grep -E '19222|9222|Chrome'

# CDP health
curl -s http://127.0.0.1:19222/json/version | python3 -m json.tool

# List CDP tabs
curl -s http://127.0.0.1:19222/json/list | python3 -m json.tool

# Chrome processes
ps aux | grep '[G]oogle Chrome.app/Contents/MacOS/Google Chrome' | grep -v Helper

# Profile check
python3 -c "
import json
ls = json.load(open('$HOME/.openclaw/browser/cdp-automation/Local State'))
for k,v in ls.get('profile',{}).get('info_cache',{}).items():
    print(f'{k}: {v.get(\"name\",\"?\")}')"
```

## Key Lessons Learned

1. **Never use `existing-session` transport** on Chrome 146+ — it triggers the Allow popup every time.
2. **Never copy `Local State`** to the custom dir — it brings all profile entries and creates ghost profiles.
3. **Chrome 146 rejects `--remote-debugging-port` on default user-data-dir** — this is a hard security constraint, not a bug.
4. **Cookie encryption key is per-app on macOS** (Keychain: "Chrome Safe Storage"), so cross-dir cookie copy works.
5. **`open -na` is required** to launch a second Chrome instance; `open -a` just activates the existing one.
6. **Tab hygiene matters** — unclosed tabs accumulate and cause `selected page has been closed` on re-attach.
