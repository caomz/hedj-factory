#!/usr/bin/env bash
# extract_book.sh — extract_book.py 的薄封装：找 python3、原样转发参数。
# 用法同 extract_book.py：
#   extract_book.sh <书源文件> --list
#   extract_book.sh 书.epub --out 案例库/<book-slug>/ --chapters 2-5
#   extract_book.sh 书.pdf  --out 案例库/<book-slug>/ --pages 10-25
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
command -v python3 >/dev/null || { echo "❌ 缺 python3（macOS: brew install python / xcode-select --install）" >&2; exit 1; }
exec python3 "${DIR}/extract_book.py" "$@"
