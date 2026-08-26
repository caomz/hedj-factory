# hedj-factory · 全流程 SOP

三条蒸馏/生产线：一条蒸馏「你自己」（一次性、反复复用），一条蒸馏「别人的爆款视频」（每条视频跑一遍），一条讲书（每本书跑一遍）。前者作为**口吻 + 品味层**注入后两者。

```
╔══════════════════════════════════════════════════════════════════════╗
║  线 A · 女娲蒸馏「你自己」 = nuwa-skill            【一次性资产，复用】 ║
╠══════════════════════════════════════════════════════════════════════╣
║   多源采集(并行 agent swarm)        框架提炼            双 agent 精炼   ║
║   X / 小红书 / 播客 / 文章   ──►  6 心智模型      ──►  去水分、对齐     ║
║                                    9 决策启发式                        ║
║                                    表达 DNA                           ║
║                         │ 产出（你的"思维操作系统"）                   ║
║                         ▼                                            ║
║         skills/<你的 handle>/SKILL.md                                 ║
║         ├─ 表达 DNA：你的梗 / 节奏 / 高低反差 / 忌讳词                 ║
║         ├─ 从夯到拉：你的锐评品味（哪算夯、哪算哈、哪算拉）            ║
║         └─ 核心心智模型 + 价值观与反模式                              ║
║                         │  记到 ~/.hedj-factory/profile           ║
╚═════════════════════════╪════════════════════════════════════════════╝
                          │  这一层 = 「口吻 + 品味」，往下游注入两次
╔═════════════════════════╪════════════════════════════════════════════╗
║  线 B · video-distill + hyperframes 蒸馏「别人的爆款」 【每条视频一遍】║
╠═════════════════════════╪════════════════════════════════════════════╣
║  Step1 取片+拆解        │  video-distill Phase 0-3                    ║
║         视频号→sph解析器 / YT抖音→yt-dlp ──► video.mp4               ║
║         whisper ──► caption ──► 拆解.md（骨架/手法/金句/论点分档）    ║
║                         │  〔中性：跟你是谁无关〕                     ║
║  Step2 翻拍角度    ◄─────┤ 注入①「从夯到拉」品味 = 立场             ║
║         给每个论点打 tier，定打法（正翻 / 反着锐评 / 元视频）         ║
║  Step3 写翻拍稿         │  Phase 3.5 洗稿 ─► 口播/<片名>/翻拍稿.md   ║
║         个人元素审计→换人→黄金5秒 hook（别漏！没稿没法录没卡片）     ║
║  Step4 成片             │  口播→talking-head-edit / 图文→hyperframes ║
║         字幕+卡片素材+章节条+主题，HTML 合成→render→成片 mp4         ║
║  Step5 四平台文案  ◄─────┘ 注入②「表达 DNA」口吻 = 说话方式         ║
║         抖音/视频号/小红书(中) + X(英)，各 2-3 备选                   ║
║  Step6 一键发号   ◄─────  social-auto-upload(sau) → 抖音/小红书/视频号║
║         先 check 登录 → 传成片+文案；发前必跟用户确认（对外不可逆） ║
╚══════════════════════════════════════════════════════════════════════╝

╔══════════════════════════════════════════════════════════════════════╗
║  线 C · book-narration-video 讲书视频               【每本书一遍】    ║
╠══════════════════════════════════════════════════════════════════════╣
║  Step1 书源+讲书拆解    │  book-narration-video Phase 0-1             ║
║         文字稿/epub/pdf/摘录 ──► extract_book.py → 原文.txt          ║
║         读章节 ──► cover.jpg + source.txt + 拆解.md（骨架/金句）     ║
║                         │  〔解读式讲书，非整本朗读；版权纪律见 skill〕║
║  Step2 讲书角度    ◄─────┤ 注入①「从夯到拉」品味 = 立场             ║
║         给书的论点打 tier，定讲法（顺着讲 / 反着锐评 / 只讲一章）     ║
║  Step3 写讲书稿         │  Phase 3 洗稿 ─► 口播/<片名>/讲书稿.md     ║
║         个人元素审计→换成你的口吻→黄金5秒 hook（别漏！）             ║
║  Step4 成片             │  口播→talking-head-edit（book/quote/recap卡）║
║         或纯旁白→hyperframes TTS + website-to-hyperframes 式渲染     ║
║  Step5 四平台文案  ◄─────┘ 注入②「表达 DNA」口吻（复用 video-distill）║
║  Step6 一键发号   ◄─────  同线 B Step 6                               ║
╚══════════════════════════════════════════════════════════════════════╝
```

## 一句话 SOP

### 线 B · 翻拍对标视频（video-distill）

1. **女娲先蒸馏你自己** → `skills/<你>/SKILL.md`。一次性建的资产，后面每条视频都复用。
2. **取片 + 转写 + 拆解**（video-distill Phase 0-3）→ `案例库/<slug>/拆解.md`。把别人的爆款变成可读文字 + "为什么火"的骨架。**这步中性**，跟谁翻拍无关。
3. **翻拍角度**（Step 2）→ **第一次读你的 profile**：用「从夯到拉」给每个论点打档，决定正翻还是反着锐评。写进 `拆解.md`。注入的是**立场**（只是角度，不是稿）。
4. **写翻拍稿**（Step 3，video-distill Phase 3.5）→ **`口播/<片名>/翻拍稿.md`**。个人元素审计 → 洗稿，把原作者换成你自己，开头黄金 5 秒 hook。**这步最常被漏掉，漏了就没东西可录、没法成片**——「角度」不是能念的稿。
5. **成片**（Step 4）→ 口播号(真人出镜)走 **talking-head-edit**：照 `翻拍稿.md` 录好竖屏口播交给它，配双语字幕 + 卡片素材(用 `/browse` 抓权威截图存 `build/news/`) + 章节条 + 主题，渲染前先出 `review.html` 给用户审。卡片/组件/主题的规格全在 `talking-head-edit/engine/DESIGN.md`(单一真源)。图文/混剪走 **hyperframes** 手写 HTML。
6. **四平台文案**（Step 5）→ **第二次读你的 profile**：用「表达 DNA」口吻写四平台标题+正文+hashtag。注入的是**口吻**。
7. **一键发号**（Step 6，可选）→ 用 **social-auto-upload（`sau` CLI）** 把 `<片名>-成片.mp4` + `平台文案.md` 发到抖音/小红书/视频号。真浏览器自动化（不是 API），**先 `sau <平台> check` 查登录**，`invalid` 就 `login --headed` 扫码。**发布是对外不可逆动作，发哪个号/哪些平台/立即还是定时，必须逐条跟用户确认再发**。视频号只发视频（图文没实现）。

### 线 C · 讲书视频（book-narration-video）

1. **女娲先蒸馏你自己**（同线 A，若尚未 onboarding）。
2. **书源 + 讲书拆解**（Phase 0-1）→ `案例库/<book-slug>/`：用 `scripts/extract_book.py` 提取（先 `--list` 再按 `--chapters`/`--pages` 取）→ `原文.txt` + `source.txt` + `cover.jpg` + `拆解.md`。**解读式讲书**，不是整本朗读；长书只讲 1-3 个核心论点。
3. **讲书角度**（Phase 2）→ **第一次读 profile**：给书的论点打档，定讲法。写进 `拆解.md` 的「讲书角度」节。
4. **写讲书稿**（Phase 3）→ **`口播/<片名>/讲书稿.md`**。个人元素审计 + 黄金 5 秒 hook + 标记 book/quote/recap 卡锚点。**别跳过，和「讲书角度」不是一回事**。
5. **成片**（Phase 4）→ 默认 **talking-head-edit**（book 卡密集）；纯旁白走 **hyperframes TTS**。
6. **四平台文案**（Phase 5）→ **第二次读 profile**，口吻纪律同 video-distill Phase 5。
7. **一键发号**（Phase 6，可选）→ 同线 B Step 6。

**路由规则**：用户给的是**书/章节/书摘** → 线 C；给的是**视频链接/文件** → 线 B。完整链路（书→成片→文案→发号）走 **hedj-factory** 总入口调度。

## 两个注入点为什么分开

| 注入点 | 读 profile 的哪部分 | 作用 |
|--------|------------------|------|
| Step 2 翻拍角度 / 讲书角度 | 从夯到拉 / 核心心智模型 | **内容立场**——站哪、锐评什么、反着做哪点 |
| Step 5 平台文案 | 表达 DNA / 反模式 | **说话方式**——梗、节奏、忌讳词 |

**立场**和**口吻**是两回事。拆开注入，才能"同一条拆解，换个人设重新发一遍"而不用重做——比如小红书想走另一个人设（认知长文 lens），只换 Step 5 的 profile，Step 2 的拆解和品味骨架不动。（Step 3 写翻拍稿/讲书稿也会读「表达 DNA」给稿子定调，但它产出的是脚本本身，不在这张"换人设只动两处"的表里。）

## 产物落位（两棵树，别混）

蒸馏一棵、生产一棵。蒸馏 → `案例库/<slug>/`；翻拍稿/讲书稿 + 成片 → `口播/<片名>/`。

```
案例库/<slug>/              # 读懂别人/书（每条对标视频或每本书一个）
├── video.mp4              软链到原片（视频才有）
├── cover.jpg              书封（讲书才有）
├── audio.wav  caption.srt/.txt  source.txt   # 视频才有 caption
└── 拆解.md                ★选题/骨架/手法/金句/翻拍角度或讲书角度

口播/<片名>/                # 做自己的成片（每条要发的成片一个）
├── 翻拍稿.md / 讲书稿.md  ★能照着念的逐字脚本（Step 3 产出，别漏）
├── build/                talking-head-edit 引擎：news/ 素材、字幕、卡片、渲染
│   └── news/ naval/ fonts/ widgets.json theme.json index.html review.html
├── <片名>-成片.mp4        终版
└── 平台文案.md            抖音/视频号/小红书/X 标题+正文+hashtag
```

一条蒸馏可对多条成片：一个 `案例库/<slug>/` ↔ 多个 `口播/<片名>/`（一本书也可分上/下集讲成多条）。

## 排错

- **拆完没翻拍稿/讲书稿、没法成片**：最常见的断链——别漏 **Step 3 写稿**（`口播/<片名>/翻拍稿.md` 或 `讲书稿.md`）。「翻拍角度/讲书角度」只是立场，不是能念的稿。
- **讲书 book 卡没书封**：检查 `案例库/<book-slug>/cover.jpg`，build 时复制或软链到 `build/news/`。
- **讲书和翻拍搞混**：给的是视频链接 → video-distill（线 B）；给的是书/章节 → book-narration-video（线 C）。
- **书源提取**：`SKILL_ROOT="$HOME/.claude/skills/book-narration-video"`；`python3 "$SKILL_ROOT/scripts/extract_book.py" 书.epub --list`，再 `--out 案例库/<slug>/ --chapters 2-5`。覆盖加 `--force`，预览加 `--dry-run`。测试：`python3 "$SKILL_ROOT/scripts/test_extract_book.py" -v`（或 `bash …/smoke_test.sh`）。
- **没卡片/没截图**：八成是没稿（→没录音→talking-head-edit 没被触发），或没 gstack `/browse`。先补稿、补素材再成片。
- **视频号下载**：用 `https://sph.litao.workers.dev/`（`POST /api/fetch_video_profile {"url": 分享链}`）拿明文真链 curl 直下。别上 mitmproxy。需要 gstack `/browse` 驱动解析器。
- **缺依赖**：`brew install ffmpeg whisper-cpp yt-dlp`；bun 见 install.sh。whisper 模型复用机器已有的。
- **gstack `/browse` 怎么装**：`brew` 装不了，但它是**公开仓库**（github.com/garrytan/gstack），**不用找团队要**，自己一行装（需 Bun v1.0+ 和 Git）：`git clone --single-branch --depth 1 https://github.com/garrytan/gstack.git ~/.claude/skills/gstack && cd ~/.claude/skills/gstack && ./setup`。装完重开一轮生效，升级用 `/gstack-upgrade`。临时不装也能跑：视频号改备选下载、截图手动塞进 `build/news/`。
- **profile 注入不准**：Phase O 蒸馏得糙，或 `~/.hedj-factory/profile` 指错。重蒸或改标记文件。
- **发布：social-auto-upload 装法**（Step 6 用，公开仓库 github.com/dreammis/social-auto-upload，MIT）：clone 到任意目录：`git clone https://github.com/dreammis/social-auto-upload.git && cd social-auto-upload && uv venv --python 3.12 && uv pip install -e . && PLAYWRIGHT_DOWNLOAD_HOST="https://npmmirror.com/mirrors/playwright" .venv/bin/patchright install chromium && cp conf.example.py conf.py`。之后 `source .venv/bin/activate && sau --help`。装完重跑一次本仓库 `./install.sh`，让它把 sau 位置记进 `~/.hedj-factory/sau_dir`（skill 靠这个找到它）。
- **发布：登录/cookie**：cookie 是平台会话，几天到两周过期，**每次发前先 `sau <平台> check --account <h>`**，`invalid` 就 `sau <平台> login --account <h> --headed` 扫码（抖音扫抖音 App、小红书扫小红书 App、视频号扫微信）。
- **发布：首次登录报错**是 upstream 已知 bug（fresh clone 会踩）。**最快：打本仓库带的补丁**——`cd "$(cat ~/.hedj-factory/sau_dir)" && git apply <hedj-factory clone>/docs/patches/social-auto-upload-login-fixes.patch`。补丁内容：抖音 `_wait_for_douyin_login` 的 `original_url`/`saw_2fa`/`i` 未定义要补；三平台登录 `page.goto` 加 `timeout=90000, wait_until="domcontentloaded"`；视频号 `_build_launch_kwargs` 把 `channel="chrome"` 改 `"chromium"`、二维码改截微信 OAuth iframe 元素、`_is_tencent_login_completed` 放宽到落 `/platform/*` 即成功。补丁若因上游版本变化打不上，就照这几条手动改。
- **发布：视频号图文发不了**：`sau tencent` 只有 `upload-video`（图文是骨架 `NotImplementedError`）；抖音/小红书图文用 `upload-note`。
