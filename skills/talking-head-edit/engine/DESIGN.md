# 成片风格系统 · DESIGN.md（可复用）

竖屏口播解说视频的统一视觉系统：中英双语字幕 + 证据/数字卡片 + 真实截图 + 分段章节进度条。
暗调、电影感、克制的高级感。一套 token 贯穿字幕和所有 widget。用 hyperframes 渲染。

> 复用方法：拷贝整个 `caption-build/` 工程到新视频目录，换掉 `video.mp4`、重跑转写对齐生成
> `groups.full.json`、按需改 `widgets.json` 和 `news/` 截图，`python3 build_caps.py` 重渲即可。
> 流程见文末「生产管线」。

---

## 1. 设计哲学

- **人话 vs 机器账本**：中文用人文黑体/衬线（人声），英文/数字用等宽 mono（机器、账本、冷数据）。两条轴对立。
- **钱是琥珀金**：唯一强调色，只给数字、金额、最狠的关键词。其余只有骨白和石墨灰。
- **三层不打架**：卡片在上 / 字幕在中下 / 进度条在底。人脸（画面中部）永远不挡。
- **实锤优先**：证据用真实新闻截图，不编不画（图表类例外，可自绘）。

## 2. 颜色 Token

| Token | 值 | 用途 |
|---|---|---|
| `--bone` | `#F4F1EA` | 主文字（中文主行、卡片标题） |
| `--bone-bright` | `#F8F5EE` | B 档强调字幕中文 |
| `--graphite` | `#9AA0A6` | 副文字（英文等宽行、译文、次要标签） |
| `--graphite-2` | `#C9CDD2` | 卡片正文标签 / 已播章节标签 |
| `--amber` | `#E9B949` | **唯一强调色**：数字/金额/关键词/激活态/来源角标 |
| `--ink` | `#0F1013`（卡底 0.74–0.76 透明 + 磨砂） | 卡片背景 |
| `--dim` | `#6B7075` | 未播章节标签 |
| 底部 scrim | `linear-gradient(transparent → rgba(0,0,0,.82))`，覆盖底部 46% | 字幕可读性 |

**可换主题（theme.json）**：上面是默认琥珀。本片 `build/theme.json` 可整套换色，`build_caps.py` 做 token 替换（含 ink/accent 的 rgb 三元组），无 theme.json 的旧片不受影响。已沉淀「**Claude 暖**」(珊瑚 `#D97757` + 暖奶白 `#F0EDE4`，accent_rgb `217,119,87`，ink `#1C1613`)。换主题只换这一个文件，字幕/卡片/标题卡/进度条全跟着变。预设方向：Claude 暖 / Linear 靛蓝冷 / 双色(红坑+琥珀真相) / Vercel 黑白。

## 3. 字体

| 角色 | 字体 | 权重 |
|---|---|---|
| 中文主行 / 卡片大标题 | **Noto Sans SC** | 900 |
| 中文正文标签 | Noto Sans SC | 500 |
| 卡片标题（书/引用，人文感） | **Noto Serif SC** | 700 |
| 英文 / 数字 / 来源 / mono 标签 | **IBM Plex Mono** | 600 |

- 张力来源：humanist CJK vs mechanical mono。禁止两个相似无衬线叠用。
- 字体子集化内联（@font-face base64）。子集脚本：Google Fonts `css2?...&text=<全脚本字符+ASCII>`，
  取返回的 `/l/font?kit=` woff2（**注意无 .woff2 后缀**，正则要匹配 `url(...)` 整体）。
- 复用见 `fonts/`（SC900/SC500/Serif700/Mono600）。换视频若有新字需重抓子集。

## 4. 字幕系统（A / B / 描金）

- **位置**：竖屏下三分之一，`bottom:360px`，居中，`padding:0 72px`。一次只显示一组。落在胸口暗区，不挡脸。
- **中文主行**：SC 900，A 档 60px / B 档 70px，`line-height:1.3`，`letter-spacing:-.01em`，`text-shadow:0 2px 18px rgba(0,0,0,.55)`，色 `--bone`（B 档 `--bone-bright`）。
- **英文副行**：Mono 600，31px，柔白 `#E7E4DC`（贴近中文主色，只略软一档做主次），**正常大小写**（不要全大写），`letter-spacing:.01em`，`margin-top:15px`。中英是同一条字幕的主次，不是两种东西，所以颜色要接近、字号别差太多、不要灰+全大写把英文做成"装饰标签"。
- **描金**：数字/关键词包 `<span class=hl>`，色 `--amber`（中英都描）。每组 0–2 个，宁缺毋滥。
- **A/B 分档**：A=默认（安静）；B=钩子 / 金句 / 主旨是数字的句子。
- **动效**：A=fade+上移24px，`power3.out`，.32s；B=scale-pop .92→1+上移，`back.out(1.6)`，.40s。每组硬退场 + `tl.set` kill at `end`（一次一组）。
- **分组**：6–14 个汉字一组；**必须贴实际录音**（脚本只作术语参照）。每组英文为精炼地道短句，不逐字直译。

## 5. 卡片 widget 系统（统一容器 C）

**通用卡壳** `.card`：`rgba(15,16,19,.76)` + `backdrop-filter:blur(26px) saturate(1.15)`，`border:1px solid rgba(255,255,255,.12)`，`border-radius:28px`，`padding:30px 32px 32px`，`box-shadow:0 30px 80px rgba(0,0,0,.55)`。
**位置**：`.wg{left:56px;right:56px;top:140px}`（上三分之一，背景区）。
**入场**：fade + 从上滑入 y:-30 + scale .97→1，`power3.out`，.55s；出场 fade+上移 + `tl.set` kill。
**公共件**：来源角标 `.wsrc`（amber 点 + mono 来源文字）；右上 `.wtag`（amber 实底"实锤/原话"角标）。

卡片类型（kind）：

| kind | 用途 | 结构要点 |
|---|---|---|
| `news` | 真实新闻证据 | 来源角标 + **真实标题截图条**（白底）+ 可选合照 + 大号 amber 数字 + 标签。数字 >6 字符降到 56px，否则 92px |
| `podcast` | 博客/播客来源 | 16:9 封面截图 + 居中播放键 + 来源 + SC900 标题 + mono 嘉宾行 |
| `book` | 书/理论 | 左书封(188×266) + 右大号 Serif 公式（如 r > g）+ 来源 + 标签 |
| `chart` | 数据/趋势 | 来源角标 + **自绘 SVG 双线**（amber 上升 vs grey 平）+ 图例 + 一句话 |
| `versus` | A vs B 对比 | 两列各：tag + 图(230h) + 大标题；中间 `VS`。新列用 amber 边框/标签 |
| `duel` | 两数字对决 | 左小灰（弱）vs 右大金（强），中间 VS，下方一句结论 |
| `quote` | 名人原话 | amber 引号 + Serif 大字引文 + mono 署名 |
| `clip` | **真访谈视频片段** | 卡内嵌 `<video>`（PiP：`.wg` 壳做透明度动画无 data 属性，内层 video 带 `data-start/duration/track-index/media-start`，**muted** B-roll）+ 来源角标 + mono 英文原话。片段先用 ffmpeg 精剪到金句（去音轨），`track-index` 用 ≥5 避开主视频(0)/音频(2） |
| `recap` | **总结/枚举卡（逐条点亮）** | SC900 标题 + mono 副标题 + N 行（amber 序号 + 名 + 灰色一句话）。每行 `{t}` 到点时从灰→金点亮（口播念到第几条就亮第几条）。用于结尾「N 个要点」回顾，或中段「X 的三种形态」枚举 |
| `titlecard` | **大字砸入报幕卡（学 TzFilm 杂志风）** | 无磨砂框，直接大字上画面：mono 大写 eyebrow（`坑 02 · THE TRAP`）+ SC900 大标题（92px，关键词 `accent` 上色），`\n` 换行。入场 **scale 1.18→1 砸入**（`back.out(1.8)`）。用于每段/每条报幕，质感拉满。`{eyebrow, title, accent}` |

## 6. 真实截图规范

- 用 gstack `/browse` 抓真实来源（CLAUDE.md 要求）。优先 CNBC/Fortune/TNW/CFODive 等正规媒体的 **2026** 报道。
- **标题截图**：`screenshot --selector h1`（多 h1 时先 `js` 查 class 再定位）。被浮层挡到时先 `js` 移除 `position:fixed/sticky` 和 promo/newsletter 类元素再截。
- **封面/配图**：取 `og:image` 用 curl 下；wikimedia 公开图可直接 curl（无需 cookie）。
- **裁切**：标题条裁紧到只剩标题；混入无关大字的缩略图，裁掉文字只留人物/主体。
- **诚实**：标题/数字/日期保持原文；口播是约数时卡片用准确数（或反之，二选一标清楚）。被爬虫封的来源（如 EPI）改用自绘图表。

## 7. 章节进度条（顶部）

- 位置：`#chapters{left:24px;right:24px;top:40px;display:flex;gap:9px;align-items:flex-start}`，在画面**最上方**、卡片之上。
- 顶部加 `#scrimtop`（上深下透的 15% 渐变）保证标签在亮画面上也清晰。
- 每段：上方 mono 23px 标签 + 下方 6px 圆角轨道(`rgba(255,255,255,.20)`)内 amber 填充条。
- **段宽按时长加权**：`flex-grow:(t1-t0)`，所以填充是真·时间进度。
- **三态**：未播=标签 `--dim` + 空轨；当前=标签 `--amber` + 填充动画 scaleX 0→1（`ease:none`，时长=该章时长）；已播=标签 `--graphite-2` + 满填。
- 章节数 5–7 个，标签 2–4 字（如 开场/痛苦/纠错/注意力/价值/孤独/护城河）。
- **本片数据**：章节和视频时长放 `build/chapters.json`（`{video_dur, chapters:[[t0,t1,label],...]}`），`build_caps.py` 读 CWD，缺省回退内置默认（向后兼容旧片）。

## 8. 图层与层级

```
最顶(top:40)     ── 分段章节进度条
上(top:140)      ── 卡片 widget（证据/数字/截图/真访谈片段）
中部             ── 人物（永不遮挡）
下三分之一(bottom:360) ── 中英双语字幕
全局             ── 顶/底 scrim 渐变（标签 + 字幕可读性）
```

## 9. What NOT to Do

- 不要霓虹/彩虹渐变；强调色只有琥珀金一种，且只给数字/关键词。
- 不要两个相似无衬线叠用；中文 vs 英文等宽的对立必须保留。
- 不要字幕挡脸；不要一句话铺满屏（6–14 字一组）。
- 不要 `#333`/`#3b82f6`/Roboto/Inter/Poppins 等默认值。
- 字幕**不准脱离录音**；编造证据截图一律禁止（图表可自绘但要标清）。
- 卡片不要 cards-in-cards 套娃；一张卡一个信息点。

## 10. 生产管线（可复用步骤）

1. **转写**：`ffmpeg` 抽 16k 单声道 wav → `whisper-cli -l zh -oj`（复用本地 turbo 模型，别重下）。
   - 词级（`-ml 1`）给对齐用；自然分句（默认）给切字幕用。
2. **切字幕**：`clean_segs.py` 从自然分段生成贴录音的中文组（修 ASR 错字 + 温和合并过短碎片）。
3. **配英文/样式**：`finalize_groups.py` 给每组加 en/style/hl/enhl → `groups.full.json`（时间用 whisper 段时间，精确）。
4. **抓证据**：`/browse` 抓真实截图存 `news/`；改 `widgets.json`（kind + 时间 + 内容）。
5. **构建**：`python3 build_caps.py groups.full.json` 生成 `index.html`（字体内联、字幕/卡片/章节条 + GSAP 时间轴）。
6. **校验**：`npx hyperframes lint`（0 error）。
7. **渲染**：**迭代用 `--quality draft`（~4min）**，**定稿才 `--quality high --fps 60`（~13min）**。
   - hyperframes 是整条时间轴渲染，无增量；改一处=全片重渲，所以**批量改、最后一次出 high**。

## 11. 依赖
- `ffmpeg`、`whisper-cli`（whisper.cpp，复用本地模型）、`node>=22`、`npx hyperframes`、Python(`fontTools`,`PIL`,`brotli`)、gstack `/browse`。
