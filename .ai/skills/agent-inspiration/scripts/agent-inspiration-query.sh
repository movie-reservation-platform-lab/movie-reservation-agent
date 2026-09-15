#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
INDEX_ROOT="${AGENT_INSPIRATION_INDEX:-/home/patex1987/development/gh_agent_projects/_index}"
PROJECT_KNOWLEDGE="${AGENT_INSPIRATION_PROJECT_KNOWLEDGE:-$REPO_ROOT/docs/knowledge}"

usage() {
  cat <<'USAGE'
Usage:
  agent-inspiration-query.sh tags
  agent-inspiration-query.sh tag <tag>
  agent-inspiration-query.sh search <terms...>
  agent-inspiration-query.sh files

Environment:
  AGENT_INSPIRATION_INDEX             Override local inspiration index path.
  AGENT_INSPIRATION_PROJECT_KNOWLEDGE Override project knowledge path.
USAGE
}

require_index() {
  if [ ! -d "$INDEX_ROOT" ]; then
    echo "Missing inspiration index: $INDEX_ROOT" >&2
    exit 2
  fi
}

command="${1:-help}"
shift || true

case "$command" in
  tags)
    require_index
    rg -o '`[a-z0-9-]+`' "$INDEX_ROOT/tag-map.md" \
      | tr -d '`' \
      | sort -u
    ;;
  tag)
    require_index
    tag="${1:-}"
    if [ -z "$tag" ]; then
      echo "tag is required" >&2
      usage
      exit 2
    fi
    rg -n -F "$tag" "$PROJECT_KNOWLEDGE" "$INDEX_ROOT"
    ;;
  search)
    require_index
    if [ "$#" -eq 0 ]; then
      echo "search terms are required" >&2
      usage
      exit 2
    fi
    rg -n -i "$*" "$PROJECT_KNOWLEDGE" "$INDEX_ROOT"
    ;;
  files)
    require_index
    find "$PROJECT_KNOWLEDGE" "$INDEX_ROOT" -type f -name '*.md' | sort
    ;;
  help|-h|--help)
    usage
    ;;
  *)
    echo "Unknown command: $command" >&2
    usage
    exit 2
    ;;
esac

