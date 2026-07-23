#!/usr/bin/env bash
# Git kancalarini kurar. Yeni makinede repo klonlandiginda bir kez calistir.
set -euo pipefail

ROOT=$(git rev-parse --show-toplevel)
install -m 755 "$ROOT/bin/hooks/pre-push" "$ROOT/.git/hooks/pre-push"
echo "pre-push kancasi kuruldu: $ROOT/.git/hooks/pre-push"
