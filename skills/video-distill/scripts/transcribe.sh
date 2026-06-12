#!/usr/bin/env bash
# transcribe.sh — 把一个视频转成 16k 单声道 wav + 中文字幕 (caption.srt / caption.txt)
#
# 用法：
#   transcribe.sh <视频路径> <输出目录> [语言=zh]
#
# 设计要点：
# - 复用机器上已有的 whisper.cpp 模型，绝不重复下载（用户明确踩过这个坑）。
#   只有一个模型都找不到时，才下载 large-v3-turbo。
# - 输出 audio.wav / caption.srt / caption.txt 到输出目录。

set -euo pipefail

VIDEO="${1:?用法: transcribe.sh <视频路径> <输出目录> [语言=zh]}"
OUTDIR="${2:?需要输出目录}"
LANG="${3:-zh}"

[ -f "$VIDEO" ] || { echo "❌ 找不到视频: $VIDEO" >&2; exit 1; }
command -v ffmpeg   >/dev/null || { echo "❌ 缺 ffmpeg (brew install ffmpeg)" >&2; exit 1; }
command -v whisper-cli >/dev/null || { echo "❌ 缺 whisper-cli (brew install whisper-cpp)" >&2; exit 1; }
mkdir -p "$OUTDIR"

# --- 找一个已有的 ggml 模型（按质量优先），找不到才下载 ---
find_model() {
  # 优先用大/turbo 模型；medium 也行。搜常见落点。
  local candidates
  candidates=$(
    {
      ls /opt/homebrew/share/whisper-cpp/ggml-*.bin 2>/dev/null
      ls "$HOME"/.cache/hyperframes/whisper/models/ggml-*.bin 2>/dev/null
      ls "$HOME"/.cache/whisper*/ggml-*.bin 2>/dev/null
      find "$HOME"/Library/Caches -iname 'ggml-*.bin' 2>/dev/null
    } | grep -v -- '-tiny' || true
  )
  # 偏好顺序：large-v3-turbo > large > medium > 其它
  for pat in 'large-v3-turbo' 'large-v3' 'large' 'medium'; do
    local hit
    hit=$(echo "$candidates" | grep "$pat" | head -1 || true)
    [ -n "$hit" ] && { echo "$hit"; return 0; }
  done
  # 没匹配到偏好，就用找到的第一个非 tiny 模型
  echo "$candidates" | head -1
}

MODEL="$(find_model)"
if [ -z "$MODEL" ] || [ ! -f "$MODEL" ]; then
  echo "⚠️  本地没找到可用 whisper 模型，下载 large-v3-turbo (~1.5G) ..." >&2
  MODEL=/opt/homebrew/share/whisper-cpp/ggml-large-v3-turbo.bin
  curl -L -o "$MODEL" \
    "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3-turbo.bin"
else
  echo "✅ 复用已有模型: $MODEL" >&2
fi

# --- 抽音频 16k 单声道 ---
echo "🎬 抽音频 ..." >&2
ffmpeg -y -loglevel error -i "$VIDEO" -ar 16000 -ac 1 -c:a pcm_s16le "$OUTDIR/audio.wav"

# --- 转写 ---
echo "📝 转写 ($LANG) ..." >&2
whisper-cli -m "$MODEL" -l "$LANG" -f "$OUTDIR/audio.wav" \
  -osrt -otxt -of "$OUTDIR/caption" >/dev/null 2>&1

echo "✅ 完成: $OUTDIR/caption.srt  $OUTDIR/caption.txt" >&2
