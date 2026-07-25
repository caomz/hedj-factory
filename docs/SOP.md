# 爆款工厂 · 全流程 SOP

两条蒸馏线：一条蒸馏「你自己」（一次性、反复复用），一条蒸馏「别人的爆款」（每条视频跑一遍）。前者作为**口吻 + 品味层**注入后者。

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
║                         │  记到 ~/.baokuan-factory/profile           ║
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
```

## 一句话 SOP

1. **女娲先蒸馏你自己** → `skills/<你>-profile/SKILL.md`。一次性建的资产，后面每条视频都复用(旧 `skills/<你>/SKILL.md` marker 继续接受、不自动迁移)。
2. **取片 + 转写 + 拆解**（video-distill Phase 0-3）→ `案例库/<slug>/拆解.md`。把别人的爆款变成可读文字 + "为什么火"的骨架。**这步中性**，跟谁翻拍无关。
3. **翻拍角度**（Step 2）→ **第一次读你的 profile**：用「从夯到拉」给每个论点打档，决定正翻还是反着锐评。写进 `拆解.md`。注入的是**立场**（只是角度，不是稿）。
4. **写翻拍稿**（Step 3，video-distill Phase 3.5）→ **`口播/<片名>/翻拍稿.md`**。个人元素审计 → 洗稿，把原作者换成你自己，开头黄金 5 秒 hook。**这步最常被漏掉，漏了就没东西可录、没法成片**——「角度」不是能念的稿。
5. **成片**（Step 4）→ 口播号(真人出镜)走 **talking-head-edit**：照 `翻拍稿.md` 录好竖屏口播交给它，配双语字幕 + 卡片素材(用 `/browse` 抓权威截图存 `build/news/`) + 章节条 + 主题，渲染前先出 `review.html` 给用户审。卡片/组件/主题的规格全在 `talking-head-edit/engine/DESIGN.md`(单一真源)。图文/混剪走 **hyperframes** 手写 HTML。
6. **四平台文案**（Step 5）→ **第二次读你的 profile**：用「表达 DNA」口吻写四平台标题+正文+hashtag。注入的是**口吻**。
7. **一键发号**（Step 6，可选）→ 用 **social-auto-upload（`sau` CLI）** 把 `<片名>-成片.mp4` + `平台文案.md` 发到抖音/小红书/视频号。真浏览器自动化（不是 API），**先 `sau <平台> check` 查登录**，`invalid` 就 `login --headed` 扫码。**发布是对外不可逆动作，发哪个号/哪些平台/立即还是定时，必须逐条跟用户确认再发**。视频号只发视频（图文没实现）。

## 两个注入点为什么分开

| 注入点 | 读 profile 的哪部分 | 作用 |
|--------|------------------|------|
| Step 2 翻拍角度 | 从夯到拉 / 核心心智模型 | **内容立场**——站哪、锐评什么、反着做哪点 |
| Step 5 平台文案 | 表达 DNA / 反模式 | **说话方式**——梗、节奏、忌讳词 |

**立场**和**口吻**是两回事。拆开注入，才能"同一条拆解，换个人设重新发一遍"而不用重做——比如小红书想走另一个人设（认知长文 lens），只换 Step 5 的 profile，Step 2 的拆解和品味骨架不动。（Step 3 写翻拍稿也会读「表达 DNA」给稿子定调，但它产出的是脚本本身，不在这张"换人设只动两处"的表里。）

## 产物落位（两棵树，别混）

蒸馏一棵、生产一棵。蒸馏 → `案例库/<slug>/`；翻拍稿 + 成片 → `口播/<片名>/`。

```
案例库/<slug>/              # 读懂别人（每条对标视频一个）
├── video.mp4              软链到原片
├── audio.wav  caption.srt/.txt  source.txt
└── 拆解.md                ★选题/骨架/手法/金句/翻拍角度(立场)

口播/<片名>/                # 做自己的成片（每条要发的成片一个）
├── 翻拍稿.md              ★能照着念的逐字脚本（Step 3 产出，别漏）
├── build/                talking-head-edit 引擎：news/ 素材、字幕、卡片、渲染
│   └── news/ naval/ fonts/ widgets.json theme.json index.html review.html
├── <片名>-成片.mp4        终版
└── 平台文案.md            抖音/视频号/小红书/X 标题+正文+hashtag
```

一条蒸馏可对多条成片：一个 `案例库/<slug>/` ↔ 多个 `口播/<片名>/`。

## 线 A 详：女娲自我蒸馏(两种入口)

线 A 的产物路径固定为 `skills/<你>-profile/`(被仓库 `.gitignore` 的 `skills/*-profile/` 忽略);**旧** `skills/<你>/SKILL.md` marker 继续接受,不自动迁移、不自动重命名。两种入口共用同一条下游链路(baokuan 注入),只在上游采集阶段不同:

| 入口 | 例子 | 走 Nuwa 哪条分支 | 产物 |
|------|------|------------------|------|
| 少量素材 | 几篇笔记 / 一两个文件 | nuwa-skill「蒸馏用户自己」小素材路径 | `skills/<你>-profile/SKILL.md` |
| **本地目录** | `/Volumes/WorkSSD/Dev/openclaw_mz/knowledge/raw` 这类含 ≥ 数十个文件的文件夹 | nuwa-skill `self-local-corpus` 分支 | 精简 `SKILL.md` + 按需 `assets/*.md` + 私有 `references/` |

### 本地目录(`self-local-corpus`)的四步硬顺序

按 nuwa-skill `SKILL.md` 锁定的路由执行,每一步未达通过标准就停下,不得跳步:

1. **无 policy inventory**:`python3 skills/nuwa-skill/scripts/inventory_local_corpus.py <source_root> --profile-dir <profile-dir>` 生成 `references/source-manifest.json`(全部 `policy_class: unclassified`、`can_distill: false`)与 `references/research/00-source-inventory.md`。源目录**只读**,**不复制、不修改、不移动**任何文件,profile 目录不出现源文件正文副本。
2. **source-policy 确认**:Nuwa 读 inventory review 后,按 `references/self-distill-workflow.md` §2 的五类来源 class(`authored` / `private-evidence` / `adapted` / `external` / `excluded`)为每个 family 起草 glob,逐条向用户解释匹配原因并取得明确确认后写入 `references/source-policy.json`。
3. **带 policy 重跑 + 六维蒸馏**:`inventory --policy` 重跑,`can_distill: true` 才进入六维研究(`references/research/01-positioning.md` 到 `06-tensions-and-evolution.md`),并按 `references/self-distill-workflow.md` §4 控制阅读预算(`authored` ≤ 20MB、`private-evidence` ≤ 100 文件或 5MB、`adapted` ≤ 30、`external` 首轮 0)。
4. **assets + SKILL.md + quality gate**:同步生成 `assets/index.md` 与八张资产卡,精简 `SKILL.md` 目标 3,000–6,000 estimated tokens(CJK 字符数 + ceil(非 CJK 字符数 / 4));写入正式路径前必须 `python3 skills/nuwa-skill/scripts/quality_check.py <profile-dir>` 退出码 0。

### 硬边界(把"看起来在蒸馏"和"真的在蒸馏"分开)

- **不是每个文件都进 profile**:`excluded` 整类不读;同名精确重复按 SHA-256 只读一份 representative;`v0.1`/`v0.2` 这类版本序列只读 `current_version`,旧版仅作观点演化证据;`assets/` 是按需加载,不会一次性预热成大目录摘要。
- **外部归档不自动成为个人原创资产**:`external` 类的他人文章、播客转写、新闻报道只能作为 `references/research/` 里的背景对照,**不得**登记到 `assets/`;`external-only` 不得登记为个人资产,即使 confidence=high。
- **私有聊天只允许脱敏抽象**:私聊、日记原文保持外部只读;能进 `SKILL.md` / `assets/` 的只有脱敏后的主题归纳或 summaries/analysis;公开面(`SKILL.md` + `assets/*.md`)由 `quality_check.py` 的隐私扫描守住四个稳定 rule id(`CREDENTIAL_ASSIGNMENT` / `WECHAT_ID` / `CHATROOM_ID` / `PRIVATE_IPV4`),`references/` 不被扫描。
- **baokuan 不越界做盘点**:如果 baokuan 入口接的是本地目录,它只做"接到路径 → 调 Nuwa → 等 quality gate 通过 → 写 `~/.baokuan-factory/profile`",**不读** `source_root`、**不写** `source-policy.json` / `source-manifest.json` / 资产卡 / SKILL.md,这些一律由 Nuwa 自己处理。

## 排错

- **拆完没翻拍稿、没法成片**：最常见的断链——别漏 **Step 3 写翻拍稿**（`口播/<片名>/翻拍稿.md`）。「翻拍角度」只是立场，不是能念的稿。
- **没卡片/没截图**：八成是没翻拍稿（→没录音→talking-head-edit 没被触发），或没 gstack `/browse`。先补稿、补素材再成片。
- **视频号下载**：用 `https://sph.litao.workers.dev/`（`POST /api/fetch_video_profile {"url": 分享链}`）拿明文真链 curl 直下。别上 mitmproxy。需要 gstack `/browse` 驱动解析器。
- **缺依赖**：`brew install ffmpeg whisper-cpp yt-dlp`；bun 见 install.sh。whisper 模型复用机器已有的。
- **gstack `/browse` 怎么装**：`brew` 装不了，但它是**公开仓库**（github.com/garrytan/gstack），**不用找团队要**，自己一行装（需 Bun v1.0+ 和 Git）：`git clone --single-branch --depth 1 https://github.com/garrytan/gstack.git ~/.claude/skills/gstack && cd ~/.claude/skills/gstack && ./setup`。装完重开一轮生效，升级用 `/gstack-upgrade`。临时不装也能跑：视频号改备选下载、截图手动塞进 `build/news/`。
- **profile 注入不准**：Phase O 蒸馏得糙，或 `~/.baokuan-factory/profile` 指错。重蒸或改标记文件。
- **本地目录蒸馏被 baokuan 越界做盘点**：Phase O 必须把目录路径原样转给 nuwa-skill `self-local-corpus` 分支;baokuan **不**读 `source_root`、**不**写 `source-policy.json` / `source-manifest.json` / 资产卡 / SKILL.md。如果发现 baokuan 直接读目录、或源文件被复制到工作区,立即停止并把目录路径写进笔记。
- **profile 路径形态不对**:新蒸馏必须写到 `skills/<handle>-profile/SKILL.md`(被 `.gitignore` 的 `skills/*-profile/` 忽略),不要写到旧 `skills/<handle>/SKILL.md`;旧 marker 继续接受,但新蒸馏一律用 `-profile` 后缀路径。`git status --ignored` 应该能看到 `skills/<handle>-profile/`。
- **质量门跑不过就写 marker**:Phase O 写 `~/.baokuan-factory/profile` 之前必须 `python3 skills/nuwa-skill/scripts/quality_check.py skills/<handle>-profile` 退出码 0;非零就停下,把失败项交给 Nuwa 修,**绝不用一份没通过质量门的 SKILL.md 覆盖 `~/.baokuan-factory/profile`**。
- **发布：social-auto-upload 装法**（Step 6 用，公开仓库 github.com/dreammis/social-auto-upload，MIT）：`cd ~/Desktop/workplace && git clone https://github.com/dreammis/social-auto-upload.git && cd social-auto-upload && uv venv --python 3.12 && uv pip install -e . && PLAYWRIGHT_DOWNLOAD_HOST="https://npmmirror.com/mirrors/playwright" .venv/bin/patchright install chromium && cp conf.example.py conf.py`。之后 `source .venv/bin/activate && sau --help`。
- **发布：登录/cookie**：cookie 是平台会话，几天到两周过期，**每次发前先 `sau <平台> check --account <h>`**，`invalid` 就 `sau <平台> login --account <h> --headed` 扫码（抖音扫抖音 App、小红书扫小红书 App、视频号扫微信）。
- **发布：首次登录报错**是 upstream 已知 bug（fresh clone 会踩）。**最快：打本仓库带的补丁**——`cd ~/Desktop/workplace/social-auto-upload && git apply <baokuan-factory clone>/docs/patches/social-auto-upload-login-fixes.patch`。补丁内容：抖音 `_wait_for_douyin_login` 的 `original_url`/`saw_2fa`/`i` 未定义要补；三平台登录 `page.goto` 加 `timeout=90000, wait_until="domcontentloaded"`；视频号 `_build_launch_kwargs` 把 `channel="chrome"` 改 `"chromium"`、二维码改截微信 OAuth iframe 元素、`_is_tencent_login_completed` 放宽到落 `/platform/*` 即成功。补丁若因上游版本变化打不上，就照这几条手动改。
- **发布：视频号图文发不了**：`sau tencent` 只有 `upload-video`（图文是骨架 `NotImplementedError`）；抖音/小红书图文用 `upload-note`。
