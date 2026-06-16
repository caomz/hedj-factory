# 引擎（口播后期）

口播类视频的可复用后期引擎：中英双语字幕 + 证据/数字卡片 + 真实截图 + 底部章节进度条，
用 hyperframes 渲染成竖屏成片。风格规范见 [DESIGN.md](DESIGN.md)。

## 这是什么
- **引擎（本目录）= 逻辑**，跨视频复用，不放任何单片数据：
  - `clean_segs.py` — 从 whisper 自然分段切出贴录音的中文字幕组（修 ASR 错字 + 温和合并）
  - `finalize_groups.py` — 给每组配英文/A·B 样式/描金 → `groups.full.json`
  - `align.py` — （可选）difflib 模糊对齐字幕到词级时间轴
  - `build_caps.py` — 生成 `index.html`（字体内联 + 字幕/卡片/章节条 + GSAP 时间轴）
  - `DESIGN.md` — 风格系统（颜色/字体/字幕/卡片/截图/进度条规范）
- **单片数据**放在各视频自己的 `口播/<片名>/build/`：`groups.*.json`、`widgets.json`、
  `news/`(真实截图)、`fonts/`(子集字体)、`seg.json`/`words.json`(转写)、`index.html`、`video.mp4`(软链)。

脚本都读 **当前目录(CWD)**，所以在某个项目的 `build/` 里调用引擎即可。

## 新做一条口播（流程）
在 `口播/<片名>/build/` 下：

```bash
ENG=~/.claude/skills/talking-head-edit/engine    # 引擎目录(装好后的位置)，下面命令都用 $ENG 调
# 0) 准备：video.mp4 软链到本片成片素材；案例参考见 案例库/
# 1) 转写（复用本地 whisper turbo 模型，别重下）
ffmpeg -y -i video.mp4 -ar 16000 -ac 1 -c:a pcm_s16le audio.wav
whisper-cli -m <turbo模型> -l zh -f audio.wav -oj -of seg          # 自然分句→seg.json
whisper-cli -m <turbo模型> -l zh -f audio.wav -ml 1 -oj -of words  # 词级→words.json(对齐备用)

# 2-3) 切字幕 + 配英文/样式：在 build/ 写一个 make_groups.py（推荐做法，见五个杠杆/销售十坑）
#   纪律：cn = FIX.get(i, RAW[i]['cn']) —— 默认就是 whisper 逐字原话，
#   FIX 只改同音错字 + 用 "|" 切句，绝不往翻拍稿/书面语改（翻拍稿只在 garbled 时兜底）。
#   META[i] = (en, style, hl, enhl)，en 是翻译可自由。
python3 make_groups.py                          # → groups.full.json
#   自检：grep groups.full.json 无残留 "|"，抽几句对照 groups.raw.json 没改词
#   （旧脚本 clean_segs.py / finalize_groups.py 仅 AI替代人类 用过，已被 make_groups.py 取代）

# 4) 抓证据截图(/browse)存 news/，编辑 widgets.json（卡片类型+时间+内容）
#    字体子集：Google Fonts css2 ?...&text=<本片字符> 取 woff2 存 fonts/

# 5) 构建 + 审阅 + 校验
python3 "$ENG/build_caps.py" groups.full.json     # → index.html(套主题)
python3 "$ENG/review_page.py"                     # → review.html，open 一下让用户先审
npx hyperframes lint                              # 0 error

# 6) 渲染：迭代用 draft（~6min），审过出终版(默认 standard)
npx hyperframes render --quality draft --output draft.mp4              # 预览
npx hyperframes render --quality standard --output ../<片名>-成片.mp4   # 终版(要超清才 --quality high --fps 60)
```

## 关键纪律
- **字幕必须贴录音**，脚本只作术语参照。
- **证据用真实截图**（图表可自绘但标清）。强调色只有琥珀金，且只给数字/关键词。
- hyperframes 整条时间轴渲染、**无增量**：改一处=全片重渲 → **批量改，最后一次出 high**。

详见 [DESIGN.md](DESIGN.md)。
