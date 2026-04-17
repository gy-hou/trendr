#!/usr/bin/env bash
# render-commands.sh — render {{repo_root}} placeholder in slash command templates
# Usage: ./runtimes/claude-code/render-commands.sh [--dst DIR] [--repo-root DIR] [--user] [--dry-run]

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DST="$REPO_ROOT/.claude/commands"
DRY_RUN=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dst)       DST="$2"; shift 2;;
    --repo-root) REPO_ROOT="$2"; shift 2;;
    --user)      DST="$HOME/.claude/commands"; shift;;
    --dry-run)   DRY_RUN=1; shift;;
    -h|--help)
      echo "Usage: $0 [--dst DIR] [--repo-root DIR] [--user] [--dry-run]"
      echo "  --dst        Target directory (default: <repo>/.claude/commands)"
      echo "  --repo-root  TrendR repo root (default: auto-detected)"
      echo "  --user       Write to ~/.claude/commands"
      echo "  --dry-run    Print what would be written without making changes"
      exit 0;;
    *) echo "Unknown flag: $1" >&2; exit 2;;
  esac
done

SRC_DIR="$SCRIPT_DIR/commands"

if [[ ! -d "$SRC_DIR" ]]; then
  echo "Error: commands source directory not found: $SRC_DIR" >&2
  exit 1
fi

echo "render-commands.sh"
echo "  repo_root : $REPO_ROOT"
echo "  source    : $SRC_DIR"
echo "  dest      : $DST"
echo "  dry_run   : $DRY_RUN"
echo ""

render_file() {
  local src="$1"
  local dst_file="$2"

  # Replace {{repo_root}} with actual path, escaping for sed
  local escaped_root
  escaped_root=$(printf '%s\n' "$REPO_ROOT" | sed 's|[&/\]|\\&|g')
  local rendered
  rendered=$(sed "s|{{repo_root}}|${escaped_root}|g" "$src")

  if [[ $DRY_RUN -eq 1 ]]; then
    echo "  [dry-run] would write: $dst_file"
    echo "$rendered" | head -10
    echo "  ..."
    echo ""
  else
    mkdir -p "$(dirname "$dst_file")"
    echo "$rendered" > "$dst_file"
    echo "  written: $dst_file"
  fi
}

# Render all .md files under commands/
while IFS= read -r -d '' src_file; do
  # Calculate relative path from SRC_DIR
  rel="${src_file#$SRC_DIR/}"
  dst_file="$DST/$rel"
  render_file "$src_file" "$dst_file"
done < <(find "$SRC_DIR" -name "*.md" -print0)

echo ""
echo "Done. $(find "$SRC_DIR" -name "*.md" | wc -l | tr -d ' ') files processed."
