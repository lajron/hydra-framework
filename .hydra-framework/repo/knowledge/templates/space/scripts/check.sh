#!/usr/bin/env bash
set -u

NODE_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REPO_ROOT="$NODE_ROOT"
while [ "$REPO_ROOT" != "/" ] && [ ! -d "$REPO_ROOT/.hydra-framework" ]; do
  REPO_ROOT="$(dirname "$REPO_ROOT")"
done

if [ ! -f "$REPO_ROOT/.hydra-framework/scripts/hydra.py" ]; then
  echo "Could not find .hydra-framework/scripts/hydra.py" >&2
  exit 2
fi

python3 "$REPO_ROOT/.hydra-framework/scripts/hydra.py" validate-package-docs --path "$NODE_ROOT" "$@"
