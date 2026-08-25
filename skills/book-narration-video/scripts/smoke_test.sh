#!/usr/bin/env bash
# smoke_test.sh — extract_book.py 冒烟测试：合成微型 txt/epub/pdf 书源，跑一遍提取全链路。
# 不依赖任何真书、不联网；pdftotext 没装也能过（会走纯 stdlib 兜底）。
# 用法：bash smoke_test.sh
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXTRACT="python3 ${DIR}/extract_book.py"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

PASS=0
FAIL=0
check() { # check <描述> <文件> <必须包含的字符串>
  local desc="$1" file="$2" needle="$3"
  if grep -qF -- "$needle" "$file"; then
    echo "  ✓ $desc"; PASS=$((PASS + 1))
  else
    echo "  ✗ $desc — 没找到: $needle（见 $file）"; FAIL=$((FAIL + 1))
  fi
}

echo "── 0. 生成合成书源 fixtures ──"
python3 "${DIR}/make_fixtures.py"

echo "── 1. --help 可用 ──"
$EXTRACT --help > "$TMP/help.txt"
check "--help 输出用法" "$TMP/help.txt" "--chapters"

echo "── 2. txt：--list + 按章提取 ──"
$EXTRACT "${DIR}/fixtures/sample.txt" --list > "$TMP/txt-list.txt"
check "列出第二章" "$TMP/txt-list.txt" "第二章 环境的杠杆"
# 注意编号含卷首段：--list 里 第三章 是第 4 段
$EXTRACT "${DIR}/fixtures/sample.txt" --out "$TMP/案例库/tiny-habits-txt" --chapters 4 \
  --title "微型习惯手册" --author "测试员" > "$TMP/txt-run.txt"
check "只含第三章正文" "$TMP/案例库/tiny-habits-txt/原文.txt" "身份的复利"
if grep -qF "环境的杠杆" "$TMP/案例库/tiny-habits-txt/原文.txt"; then
  echo "  ✗ 章节范围没生效：第二章混进来了"; FAIL=$((FAIL + 1))
else
  echo "  ✓ 范围外章节被排除"; PASS=$((PASS + 1))
fi
check "source.txt 记了书名" "$TMP/案例库/tiny-habits-txt/source.txt" "书名：微型习惯手册"
check "source.txt 记了范围" "$TMP/案例库/tiny-habits-txt/source.txt" "范围：章节段 4"

echo "── 3. epub：--list + 元数据 + 按章提取 + source.txt 追加 ──"
$EXTRACT "${DIR}/fixtures/sample.epub" --list > "$TMP/epub-list.txt"
check "读出 epub 书名" "$TMP/epub-list.txt" "微型习惯手册"
check "列出 3 个章节段" "$TMP/epub-list.txt" "共 3 个章节段"
$EXTRACT "${DIR}/fixtures/sample.epub" --out "$TMP/案例库/tiny-habits" --chapters 1-2 > "$TMP/epub-run.txt"
check "含第一章" "$TMP/案例库/tiny-habits/原文.txt" "俯卧撑"
check "含第二章金句" "$TMP/案例库/tiny-habits/原文.txt" "你不是缺自律"
if grep -qF "身份的复利" "$TMP/案例库/tiny-habits/原文.txt"; then
  echo "  ✗ 章节范围没生效：第三章混进来了"; FAIL=$((FAIL + 1))
else
  echo "  ✓ 范围外章节被排除"; PASS=$((PASS + 1))
fi
check "source.txt 自动读到作者" "$TMP/案例库/tiny-habits/source.txt" "作者：测试员"
# 再提取一次 → source.txt 应追加记录而不是覆盖
$EXTRACT "${DIR}/fixtures/sample.epub" --out "$TMP/案例库/tiny-habits" --chapters 3 --name 原文-ch3.txt > /dev/null
[ "$(grep -c "extract_book.py" "$TMP/案例库/tiny-habits/source.txt")" -eq 2 ] \
  && { echo "  ✓ source.txt 追加第二条提取记录"; PASS=$((PASS + 1)); } \
  || { echo "  ✗ source.txt 追加记录失败"; FAIL=$((FAIL + 1)); }

echo "── 4. pdf：--list + 按页提取（pdftotext 或纯 stdlib 兜底）──"
command -v pdftotext >/dev/null && echo "  （本机有 pdftotext，走 poppler 路径）" || echo "  （本机没 pdftotext，走纯 stdlib 兜底路径）"
$EXTRACT "${DIR}/fixtures/sample.pdf" --list > "$TMP/pdf-list.txt"
check "读出 2 页" "$TMP/pdf-list.txt" "共 2 页"
$EXTRACT "${DIR}/fixtures/sample.pdf" --out "$TMP/案例库/tiny-habits-pdf" --pages 2 \
  --title "Tiny Habits Field Notes" 2> "$TMP/pdf-warn.txt" > "$TMP/pdf-run.txt"
check "只含第 2 页" "$TMP/案例库/tiny-habits-pdf/原文.txt" "Page two marker"
if grep -qF "Chapter one" "$TMP/案例库/tiny-habits-pdf/原文.txt"; then
  echo "  ✗ 页码范围没生效：第 1 页混进来了"; FAIL=$((FAIL + 1))
else
  echo "  ✓ 范围外页被排除"; PASS=$((PASS + 1))
fi
check "source.txt 记了 pdf 来源" "$TMP/案例库/tiny-habits-pdf/source.txt" "sample.pdf（pdf"

echo "── 5. --max-chars 截断 ──"
$EXTRACT "${DIR}/fixtures/sample.txt" --max-chars 260 > "$TMP/trunc.txt" 2> "$TMP/trunc-warn.txt"
check "截断标注写进正文" "$TMP/trunc.txt" "[已截断"

echo ""
if [ "$FAIL" -eq 0 ]; then
  echo "✅ smoke test 全过：$PASS 项"
else
  echo "❌ smoke test 挂了 $FAIL 项（过 $PASS 项）"
  exit 1
fi
