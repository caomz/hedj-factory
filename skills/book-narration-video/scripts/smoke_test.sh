#!/usr/bin/env bash
# smoke_test.sh — 兼容入口：转调 Python unittest（无 rm -rf，fixture 全在临时目录）。
# 用法：bash smoke_test.sh
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 -m unittest "${DIR}/test_extract_book.py" -v
