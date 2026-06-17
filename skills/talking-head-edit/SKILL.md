---
name: talking-head-edit
description: |
  口播视频后期剪辑：把一条录好的竖屏口播(0xKaiwen 出镜)做成成片,中英双语字幕 + 卡片 widget(新闻/截图/数字对决/名人金句/真访谈片段/大字坑标题/逐条点亮总结) + 顶部章节进度条 + 可换主题(Claude 暖/Linear 冷…),用 hyperframes 渲染。引擎(合成脚本 + 风格规范 DESIGN.md)内置在本 skill 的 `engine/`。
  触发词:「剪这条口播」「给这个录音加字幕和卡片」「做成片」「后期/剪辑这条视频」「上字幕+widget」「用口播引擎」「渲染成片」「加卡片/截图/数字卡」「换个主题色重渲」。
  给一条录好的口播 mp4 + 想要带双语字幕和高级卡片的成片时,就用这个 skill。
  注意:上游的蒸馏/翻拍稿/平台文案是 video-distill 的活;本 skill 只管「录音→成片」的后期。
---

# 口播剪辑 · talking-head-edit

> 把一条录好的口播做成有双语字幕 + 丰富卡片 + 章节条的高级成片。本 skill 是开机流程 + 踩过的坑。
>
> **引擎在哪**:脚本和风格规范在本 skill 的 `engine/`,装好后是 `~/.claude/skills/talking-head-edit/engine/`。
> 下文用 `<ENG>` 代指这个引擎目录,即 `~/.claude/skills/talking-head-edit/engine`(可以 `export ENG=~/.claude/skills/talking-head-edit/engine`,后面命令直接用 `$ENG`)。**动手前先读 `<ENG>/DESIGN.md`**(颜色/字体/字幕/卡片/章节/主题)。

## 工程结构

每条片一个工作目录,后期数据全在它的 `build/` 里(脚本都读 CWD,在 `build/` 里调引擎):
```
口播/<片名>/[录音目录]/build/
  make_groups.py   # 本片字幕作者数据(seg→groups.full)，每片一份
  groups.full.json / groups.raw.json
  widgets.json     # 卡片(类型+时间+内容)
  theme.json       # 主题配色(可选，缺省=琥珀)
  chapters.json    # 章节(video_dur + [[t0,t1,label],...])
  news/            # 卡片用的截图/封面(权威源)
  naval/           # 剪入的真访谈片段(muted B-roll)
  fonts/ seg.json index.html review.html
  video.mp4 → 录音文件
```
引擎脚本(都在 `<ENG>/`):`build_caps.py`(合成器) `subset_fonts.py`(字体子集) `review_page.py`(审阅页) `DESIGN.md`。

## 流程(SOP)

### 0. 准备 + 静音裁剪(★先 trim 再转写,顺序别反;★剪完必验)
`mkdir -p build && cd build`。**先把原片的静音收紧再开工**,口播停顿多,不剪整片拖沓:
1. **先看说话音量**:`ffmpeg -i ../<录音.mp4> -af volumedetect -f null -` 看 `mean_volume`。
2. **设门限**:`cut_silence.py` 的 `NOISE` 要**明显低于 mean_volume(再低 ~7dB)**,否则吃句尾字。默认 `-40dB`(车内/外景 mean 约 -33dB 适用;安静棚里 mean 高,可上 -45dB)。
   `python3 <ENG>/cut_silence.py ../<录音.mp4> 0000_tight.mp4`(出 `silence_keep.json`)。
3. **必验,别跳**:抽 tight 音频转写一遍,和原片转写 diff。**掉了句尾字 = 门限太高(太靠近说话音量),调低 5dB 重剪**:
   ```
   ffmpeg -y -i 0000_tight.mp4 -ar 16000 -ac 1 audio.wav   # tight 音频
   whisper-cli -m <turbo> -l zh -f audio.wav -oj -of seg
   # 和原片 seg 比字数,差几个句尾字就重剪(ai-layoff 第一版 -30dB 吃了 29 个句尾字,-40dB 才干净)
   ```
4. `ln -sf 0000_tight.mp4 video.mp4`(**video.mp4 指向 tight,不是原片**)。
> **为什么先剪**:后面字幕/卡片/章节时间全长在紧凑时间轴上,天然对齐。**反了**(先在原片建好再想剪)就得拿 `silence_keep.json` 把每个时间戳 remap 过去(数学等价但返工)。
> **`cut_silence` 会吃字的原理**:句尾尾音淡出,音量掉到门限以下被当成静音切掉。门限离说话音量越近、吃得越狠。所以宁可门限低、剪得少,也别吃字。个别句尾还被吃,往 `PROTECT` 加时间窗。

### 1. 转写(复用本地 whisper turbo,别重下;★两种都要)
`whisper-cli -m <turbo模型> -l zh -f audio.wav -oj -of seg`            → `seg.json`(自然分句,给切字幕用)
`whisper-cli -m <turbo模型> -l zh -f audio.wav -ml 1 -oj -of words`    → `words.json`(**词级,给 align.py 对齐用,别省**)
本机模型常在 `/opt/homebrew/share/whisper-cpp/ggml-large-v3-turbo.bin`。

### 2. 字幕(最容易翻车的一步,见纪律)
写 `build/make_groups.py`:从 seg.json 合并出自然分段(`groups.raw.json`),再产出 authored 字幕组。
**铁律:`cn = FIX.get(i, RAW[i]['cn'])`**,默认就是 whisper 逐字原话,`FIX` 字典只改**同音错字**(画术→话术、那玩儿→纳瓦尔、自动画→自动化、产品名 ASR 错音→真名)和用 `|` 把含两句的段切开。**绝不往翻拍稿/书面语改**。翻拍稿只在 whisper garbled、听不出他说啥时兜底参照术语。`META[i]=(en,style,hl,enhl)`,英文是翻译可自由,`style` a/b(b 给钩子/金句/坑标题/punchline),`hl` 描金只给数字+关键词(每组 0-2 个)。
**★时间用 align.py 词级对齐,别用段时间按字数比例分**(比例分会让多句段里的字幕和音频对不上,看着像"字被吞"):
```
python3 make_groups.py                                   # 先出 authored 组(时间先随便填/留空)
python3 <ENG>/align.py groups.authored.json groups.full.json   # difflib 把每组对到 words.json 的真实词时间
```
自检:`grep` groups.full.json 无残留 `|`;抽几句对照 groups.raw.json 没改词;抽几句对照音频时间点对得上。(模板见 `<ENG>/make_groups.template.py`)

### 3. 卡片要密、要权威(学 TzFilm)
写 `widgets.json`。**别只在金句处放一两张**,参考片几乎每几秒一张卡。他每提到一个术语/人/产品/数字/电影,就配一张:
- 提 **FDE** 这类术语 → 权威报道/官网截图卡(权威、清晰、对得上他在讲的点)
- 提**某概念对比** → `duel`(左小灰 vs 右大金,如 build便宜 vs sell稀缺)
- 提 **Naval 金句** → `quote` 卡 / 有原片就 `clip` 剪真访谈
- 提**电影/书** → `book` 卡(海报 + 大字)
- 提**数字** → `news` 卡大字 stat,或 `duel`
- 提**自己产品** → `news` 卡(官网截图 + 大字)
- 每段/每条开头 → `titlecard` 大字砸入报幕
- 结尾 → `recap` 逐条点亮总结
卡片类型和字段全在 DESIGN.md「卡片 widget 系统」。**截图要权威源**(官网/权威媒体/Wikipedia),用 gstack `/browse` 抓,存 `news/`。时间点要对上他说那句话(早了晚了都出戏)。卡片之间时间别重叠(都在 top:140 区)。
**没 `/browse` 时别硬凑**:gstack 没装就抓不了截图。这时**不要出没素材的空卡、也不要拿不相干的图凑**——直接告诉用户"我这没 /browse,抓不了截图",让他装 gstack 或把需要的截图手动放进 `news/`,你再套卡片。素材缺了,成片质感直接塌,值得停下来要。

### 4. 主题 + 字体
**默认就把 Claude 暖拷进来**(珊瑚 `#D97757` + 暖奶白,= 0xKaiwen 口播号当前主基调),别裸跑引擎兜底:
`cp <ENG>/theme.claude-warm.json theme.json`(或直接拷上一条片的 `build/theme.json`)。
> ⚠️ **没 theme.json 时引擎回退到 amber `#E9B949`,那只是兜底色、不是成片基调,直接出片会和往期片色不一致**(踩过:ai-layoff 第一版没拷 theme.json,整片成了 amber,和 Claude 暖的往期片对不上)。
> 要换别的色(Linear 靛蓝冷 / 双色红坑+真相 / Vercel 黑白,见 DESIGN.md)再改 `theme.json` 这一个文件,字幕/卡片/标题卡/进度条全跟着变。
`python3 <ENG>/subset_fonts.py`(扫全片字符抓 4 款字体子集到 fonts/)。

### 5. 章节
`chapters.json`:`{video_dur, chapters:[[t0,t1,label],...]}`,5-7 段,标签 2-4 字,边界对齐他的分段。

### 6. ★ 生成审阅页,让用户先审(渲染前必做)
```
python3 <ENG>/build_caps.py groups.full.json   # → index.html(套主题)
python3 <ENG>/review_page.py                   # → review.html
```
`review.html` 把**主题色板 + 全部素材(news/naval) + 全部卡片(静态原生渲染) + 字幕 A/B 样例**摆成一页。让用户 `open review.html` 审一遍:素材权不权威/清不清晰、卡片文字数字对不对、上没上对主题色、左右居不居中、时间点对不对、字幕逐不逐字。**用户点头再渲染**,别拿 18 分钟的 high 去试错。

### 7. 校验 + 渲染
`npx hyperframes lint`(0 error)。**先 draft 自己抽帧验**(~6min),审过再出终版:
`npx hyperframes render --quality draft --output draft.mp4`
`npx hyperframes render --quality standard --output ../<片名>-成片.mp4`   # 终版默认 standard(30fps,竖屏口播够用,比 high 60fps 快很多;要超清才上 --quality high --fps 60)
hyperframes 整条时间轴渲染、**无增量**:改一处=全片重渲 → 批量改、最后一次出终版。

## 几条踩过的坑(都是真教训)
- **字幕逐字贴音频**,翻拍稿只兜底,犯过多次,见记忆 captions-verbatim。
- **卡片素材要权威、清晰、对题**:别拿不相干的首页凑数(FDE 那次放了 Anthropic 首页,既没讲 FDE 也不对题,换成一篇专门讲 FDE 的报道才对)。
- **卡片时间对齐他说那句话**:Naval 卡别在他还没提播客时就冒出来。
- **渲染前先出 review.html 给用户审**,别直接 high。
- **draft 先验、别删**(用户要审)。**别想着并行加速**:单条渲染 hyperframes 已经按 CPU 核数起满 Chrome worker、吃满核了,再并行第二条只是抢同样的核、时间片轮转,不会更快还更容易崩。一条一条顺序渲最稳。想更快就**用 standard**(默认),别用 high 60fps。
- 字体改了文案要重抓子集;widgets.json 改了要重 build。

## 依赖
`ffmpeg`、`whisper-cli`、`node>=22`、`npx hyperframes`、Python(`fontTools`/`PIL`/`brotli`)、gstack `/browse`(抓截图)。引擎与风格规范见 `<ENG>/DESIGN.md` 与 `<ENG>/README.md`。
