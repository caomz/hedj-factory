#!/usr/bin/env bash
# baokuan-factory installer — copies the bundled skills into ~/.claude/skills/
# and checks for the external tools the pipeline needs.
#
# Usage:
#   ./install.sh            # install (skips skills that already exist)
#   ./install.sh --force    # overwrite existing skills (backs them up first)
#
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="$HERE/skills"
DEST="$HOME/.claude/skills"
FORCE=0
[ "${1:-}" = "--force" ] && FORCE=1

bold() { printf "\033[1m%s\033[0m\n" "$1"; }
ok()   { printf "  \033[32m✓\033[0m %s\n" "$1"; }
warn() { printf "  \033[33m!\033[0m %s\n" "$1"; }
err()  { printf "  \033[31m✗\033[0m %s\n" "$1"; }

bold "爆款工厂 · baokuan-factory installer"
echo

# --- 1. dependency check (report only, never auto-install) -------------------
bold "1) 检查外部依赖（缺了会列出 brew 命令，不自动装）"
declare -a MISSING=()
check() {
  if command -v "$1" >/dev/null 2>&1; then ok "$1 — $(command -v "$1")"; else err "$1 缺失"; MISSING+=("$2"); fi
}
check ffmpeg       "ffmpeg"
check whisper-cli  "whisper-cpp"
check yt-dlp       "yt-dlp"
check python3      "python"
check bun          "bun（或见 https://bun.sh）"
if [ "${#MISSING[@]}" -gt 0 ]; then
  echo
  warn "缺以下依赖，装上再用全功能（转写/取片/剪辑）："
  printf "      brew install"; for m in "${MISSING[@]}"; do printf " %s" "$m"; done; printf "\n"
  warn "（bun 若 brew 装不了：curl -fsSL https://bun.sh/install | bash）"
fi
# 软依赖：gstack /browse（视频号取片 + 成片抓素材截图都靠它）。不是 brew 包，装不了就报一下。
if [ -d "$HOME/.claude/skills/browse" ] || [ -d "$HOME/.claude/skills/gstack" ]; then
  ok "gstack /browse — 已装（视频号取片 + 抓素材截图可用）"
else
  warn "gstack /browse 没装：视频号取不了片、成片抓不了素材截图。它是内部 skill 包（非 brew），找团队拿来装到 ~/.claude/skills/。"
fi
echo

# --- 2. install skills -------------------------------------------------------
bold "2) 安装 skills 到 $DEST"
mkdir -p "$DEST"
TS="$(date +%Y%m%d-%H%M%S)"
# 备份放到 skills 目录【外面】——放里面的话，带 SKILL.md 的备份会被当成一个幽灵重复 skill 加载。
BAK="$HOME/.baokuan-factory/backups/$TS"
for d in "$SRC"/*/; do
  name="$(basename "$d")"
  target="$DEST/$name"
  if [ -L "$target" ]; then
    # symlink = 有人把这个 skill 链到自己的开发副本(比如 hyperframes 维护者)。别动它，
    # 否则每次自动同步都会把他的开发链接覆盖成冻结的副本。
    warn "${name} 是 symlink（指向 $(readlink "$target")），保留本地开发链接，不覆盖。"
  elif [ -e "$target" ]; then
    if [ "$FORCE" -eq 1 ]; then
      mkdir -p "$BAK"; mv "$target" "$BAK/${name}"
      cp -R "$d" "$target"; ok "${name}（已覆盖，旧版备份到 ~/.baokuan-factory/backups/${TS}/）"
    else
      warn "${name} 已存在，跳过（要覆盖：./install.sh --force）"
    fi
  else
    cp -R "$d" "$target"; ok "${name}"
  fi
done
echo

# --- 3. record repo location (lets the skill auto-pull latest on every use) ---
mkdir -p "$HOME/.baokuan-factory"
printf "%s\n" "$HERE" > "$HOME/.baokuan-factory/repo"
ok "记下仓库位置 → ~/.baokuan-factory/repo（之后每次用 skill 会自动从这里拉最新）"
echo

# --- 4. next steps -----------------------------------------------------------
bold "4) 装好了。下一步："
cat <<'EOF'
  在 Claude Code 里说一句任意触发：
    · 第一次用 → "用爆款工厂帮我 onboarding"（会先装/查依赖 + 用女娲蒸馏你自己）
    · 翻拍一条 → "我要翻拍这条视频 <对标链接>，做成我自己口吻的成片和文案"

  全流程图：docs/SOP.md
EOF
