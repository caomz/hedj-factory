#!/usr/bin/env bash
# smoke_test.sh — 兼容入口：直接跑 unittest 文件（勿用 python -m unittest /abs/path）。
# 用法：bash smoke_test.sh
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "${DIR}/test_extract_book.py" -v
