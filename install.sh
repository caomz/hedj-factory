#!/usr/bin/env bash
# baokuan-factory installer — symlinks the bundled skills into ~/.claude/skills/
# and checks for the external tools the pipeline needs.
#
# 为什么 symlink 不 cp：① 改源即时生效，不用反复 reinstall；② 别的安装器（如 gstack
# setup）重写 ~/.claude/skills 时，symlink 受保护、拷贝会被删掉（6/22 就是这么丢的）。
#
# Usage:
#   ./install.sh            # symlink 部署（已是正确 symlink 就跳过；拷贝型会备份后换成 symlink）
#   ./install.sh --force    # 连"指向别处的 symlink"也强制改指到本仓库（慎用）
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
# 软依赖：gstack /browse（视频号取片 + 成片抓素材截图都靠它）。brew 装不了，但是公开仓库，自己一行装。
if [ -d "$HOME/.claude/skills/browse" ] || [ -d "$HOME/.claude/skills/gstack" ]; then
  ok "gstack /browse — 已装（视频号取片 + 抓素材截图可用）"
else
  warn "gstack /browse 没装：视频号取不了片、成片抓不了素材截图（成片质感命根子）。"
  warn "brew 装不了，但它是公开仓库（github.com/garrytan/gstack），自己一行装（需 Bun v1.0+ 和 Git）："
  printf "      git clone --single-branch --depth 1 https://github.com/garrytan/gstack.git ~/.claude/skills/gstack && cd ~/.claude/skills/gstack && ./setup\n"
  warn "（装完重开一轮 Claude Code 生效；临时不装也能跑：视频号改备选下载、截图手动塞进 build/news/）"
fi
# 软依赖（最后一环 · 发布）：social-auto-upload（sau CLI）。公开仓库，单独装，只有 Step 6 一键发号才用；不装不影响成片+文案。
SAU_DIR="$HOME/Desktop/workplace/social-auto-upload"
if [ -x "$SAU_DIR/.venv/bin/sau" ]; then
  ok "social-auto-upload（sau）— 已装（Step 6 一键发抖音/小红书/视频号可用；发前记得先 sau <平台> check）"
else
  warn "social-auto-upload 没装：不影响前面，只有走到 Step 6 一键发号才需要。公开仓库（github.com/dreammis/social-auto-upload，MIT，需 uv + python3.10~3.12），一段装："
  printf "      cd ~/Desktop/workplace && git clone https://github.com/dreammis/social-auto-upload.git && cd social-auto-upload && uv venv --python 3.12 && uv pip install -e . && PLAYWRIGHT_DOWNLOAD_HOST=\"https://npmmirror.com/mirrors/playwright\" .venv/bin/patchright install chromium && cp conf.example.py conf.py\n"
  warn "（装完各平台 sau <平台> login --account <你> --headed 扫码；首次登录若报错见 docs/SOP.md 排错「发布」）"
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
  link_to="${d%/}"                       # 源 skill 的绝对路径
  if [ -L "$target" ]; then
    cur="$(readlink "$target")"
    if [ "$cur" = "$link_to" ]; then
      ok "${name}（已 symlink，跳过）"
    elif [ "$FORCE" -eq 1 ]; then
      rm -f "$target"; ln -s "$link_to" "$target"; ok "${name}（symlink 改指到本仓库）"
    else
      # 指向别处的 symlink（比如 hyperframes 维护者链到自己的开发副本）——别动它。
      warn "${name} 是 symlink（指向 ${cur}），保留本地开发链接，不覆盖。"
    fi
  elif [ -e "$target" ]; then
    # 真目录/拷贝 → 备份后换成 symlink（治本：gstack 再清洗也冲不掉，改源即时生效）
    mkdir -p "$BAK"; mv "$target" "$BAK/${name}"
    ln -s "$link_to" "$target"
    ok "${name}（拷贝→已备份到 ~/.baokuan-factory/backups/${TS}/，改为 symlink）"
  else
    ln -s "$link_to" "$target"; ok "${name}（symlink）"
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
    · 发出去   → "把这条成片发到抖音/小红书/视频号"（Step 6，会先 check 登录、发前跟你确认）

  全流程图：docs/SOP.md
EOF
