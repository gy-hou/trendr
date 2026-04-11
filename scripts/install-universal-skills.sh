#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SKILLS_ROOT="$REPO_ROOT/skills"

RUNTIME="all"
MODE="copy"
FORCE="false"

CORE_SKILLS=(
  "paper-scout"
  "paper-analyzer"
  "review-writer"
  "verifier"
  "research-vault"
  "trendr-watchdog"
  "platform-hotspots"
  "chrome-cdp-setup"
)

usage() {
  cat <<'EOF'
Usage:
  bash scripts/install-universal-skills.sh [--runtime all|codex|claude|claude-code] [--force] [--link|--copy]

Options:
  --runtime   Target runtime(s). Default: all
  --force     Replace existing installed skill directories.
  --link      Install via symlink (default is copy).
  --copy      Install via file copy.
  -h, --help  Show this help.
EOF
}

title_case() {
  python3 - "$1" <<'PY'
import sys
parts = [p for p in sys.argv[1].replace("_", "-").split("-") if p]
print(" ".join(p.capitalize() for p in parts))
PY
}

ensure_openai_yaml() {
  local skill_dir="$1"
  local skill_md="$skill_dir/SKILL.md"
  local agents_dir="$skill_dir/agents"
  local yaml_path="$agents_dir/openai.yaml"
  if [ -f "$yaml_path" ]; then
    return
  fi
  if [ ! -f "$skill_md" ]; then
    return
  fi

  local skill_name
  skill_name="$(awk -F': ' '/^name:/{print $2; exit}' "$skill_md" | tr -d '"' | tr -d "'")"
  if [ -z "$skill_name" ]; then
    skill_name="$(basename "$skill_dir")"
  fi
  local skill_desc
  skill_desc="$(awk -F': ' '/^description:/{print $2; exit}' "$skill_md" | tr -d '"' | tr -d "'")"
  if [ -z "$skill_desc" ]; then
    skill_desc="TrendR skill: ${skill_name}"
  fi
  local display
  display="$(title_case "$skill_name")"

  mkdir -p "$agents_dir"
  cat > "$yaml_path" <<EOF
interface:
  display_name: "${display}"
  short_description: "${skill_desc}"
  default_prompt: "Use \$${skill_name} for TrendR workflows."
EOF
}

install_one_skill() {
  local src="$1"
  local dest="$2"

  if [ -e "$dest" ] || [ -L "$dest" ]; then
    if [ "$FORCE" = "true" ]; then
      rm -rf "$dest"
    else
      echo "skip: $(basename "$dest") already exists at $dest (use --force to replace)"
      return
    fi
  fi

  if [ "$MODE" = "link" ]; then
    ln -s "$src" "$dest"
  else
    cp -R "$src" "$dest"
  fi

  ensure_openai_yaml "$dest"
  echo "installed: $(basename "$dest") -> $dest"
}

install_for_runtime() {
  local runtime="$1"
  local target_root=""
  case "$runtime" in
    codex)
      target_root="${CODEX_HOME:-$HOME/.codex}/skills"
      ;;
    claude|claude-code)
      target_root="$HOME/.claude/skills"
      ;;
    *)
      echo "error: unsupported runtime: $runtime" >&2
      exit 1
      ;;
  esac

  mkdir -p "$target_root"
  echo "target runtime: $runtime"
  echo "target path: $target_root"
  for skill in "${CORE_SKILLS[@]}"; do
    local src="$SKILLS_ROOT/$skill"
    local dest="$target_root/$skill"
    ensure_openai_yaml "$src"
    install_one_skill "$src" "$dest"
  done
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --runtime)
      [ "$#" -ge 2 ] || { echo "error: --runtime requires a value" >&2; exit 1; }
      RUNTIME="$2"
      shift 2
      ;;
    --force)
      FORCE="true"
      shift
      ;;
    --link)
      MODE="link"
      shift
      ;;
    --copy)
      MODE="copy"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "error: unknown argument: $1" >&2
      usage
      exit 1
      ;;
  esac
done

case "$RUNTIME" in
  all)
    install_for_runtime "codex"
    install_for_runtime "claude-code"
    ;;
  codex)
    install_for_runtime "codex"
    ;;
  claude|claude-code|claudecode)
    install_for_runtime "claude-code"
    ;;
  *)
    echo "error: invalid runtime '$RUNTIME' (use all|codex|claude|claude-code)" >&2
    exit 1
    ;;
esac

echo "done: universal skill installation completed."
