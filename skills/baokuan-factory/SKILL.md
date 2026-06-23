---
name: baokuan-factory
description: |
  爆款工厂：把"别人的爆款短视频"变成"你自己口吻的成片 + 全平台文案"的一条龙总入口。串起四件事:①女娲蒸馏你自己的表达DNA（一次性 onboarding）②video-distill 蒸馏对标爆款→拆解/翻拍角度 ③talking-head-edit（口播）/hyperframes（图文混剪）把翻拍稿/录音做成成片 ④四平台爆款文案。它是路由器/checklist，按顺序调度 nuwa-skill / video-distill / talking-head-edit / hyperframes，并在翻拍和文案两处注入你自己的 profile。
  什么时候用（要 pushy 一点别漏触发，但只在"整条链路 / 团队上手"时当入口）：
  - 团队新人 onboarding，"装一下 / clone 了这套爆款翻拍 skill 不知道下一步 / 怎么开始用 / 要不要装依赖"——本 skill 亲自带 onboarding（查依赖 + 用女娲蒸馏你自己），别只顾自己跑 bash。
  - "我要开始做爆款翻拍 / 搭翻拍流程 / 从对标视频到成片到文案走一遍 / 系统化做翻拍号"。
  - "把这条对标视频（链接或文件）变成我自己口吻的成片和全平台文案"——要的是完整产物（成片+文案），不是单步。
  - "先蒸馏我自己再批量翻拍对标号"。
  边界（守住精度）：如果用户只要其中一步——只下载 / 只转写提字幕 / 只拆解一条视频结构 / 只写某平台文案标题 / 只蒸馏某个别人——那分别是 video-distill / nuwa-skill / hyperframes 的活，别抢；本 skill 只在要走完整链路或团队 onboarding 时当总入口。
---

# 爆款工厂 · Baokuan Factory

> 一句话：把**别人的爆款**变成**你自己口吻的成片 + 全平台文案**的一条龙。
> 你（Claude）在这里是**总调度**，不是亲自干所有活。每一步都委派给对应子 skill，本 skill 只负责**顺序、衔接、和把"用户自己的 profile"注入到该注入的地方**。

## 这套是什么（给第一次用的同事）

两条蒸馏线 + 剪辑 + 文案：

```
线A（一次性）  女娲蒸馏「你自己」 ── nuwa-skill ──► skills/<你>/SKILL.md
                                                  （表达DNA + 从夯到拉品味）
                                                          │ 反复复用，注入下游
线B（每条视频）video-distill 蒸馏「别人的爆款」
   取片 → 转写 → 拆解 → 翻拍角度◄注入①品味 → 〔录制 → talking-head-edit 口播成片 / hyperframes 图文混剪〕 → 四平台文案◄注入②口吻
```

依赖的子 skill（install.sh 已一并装好）：
- **nuwa-skill**（女娲造人）——蒸馏一个人的思维操作系统成一个 Skill。这里用来蒸馏**用户自己**。
- **video-distill**（视频蒸馏）——取片/转写/拆解/翻拍角度/四平台文案。线B 的主力。
- **talking-head-edit**（口播剪辑）——把真人出镜录好的口播做成带双语字幕 + 卡片 + 顶部章节条 + 可换主题的成片，内置合成引擎和踩过的坑。**口播号的主力成片工具**。
- **hyperframes 全家桶**（hyperframes / -cli / -registry / gsap / website-to-hyperframes）——把图文/动画/混剪类做成 HTML 视频合成并渲染（talking-head-edit 底层也用它）。

详细全流程图见本 skill 同级或仓库的 `docs/SOP.md`。

## 开工前：第 0 步永远是「拉最新」（每次都做）

**每次触发本 skill，动手前先跑一次同步**，把团队公共仓库拉到最新再开工——这样谁改了引擎/拆解套路/卡片样式，全队下一次用就自动拿到，不会各人跑各人的旧版：

```bash
bash ~/.claude/skills/baokuan-factory/scripts/sync.sh
```

它**永不阻塞**:离线 / 没装过 / 有本地改动 → 打一行提示就退，用当前版本继续。只有真拉到新 commit 才会重装（"已是最新"是 1 秒空操作）。看到它说"拉到更新…已更新到最新"，就知道这次用的是最新版；本次更新下次触发才完全生效（当前对话已加载旧 SKILL.md），如果它报告有重大更新，可提示用户重开一轮。

> 为什么放第 0 步：这套是给团队用的，引擎和套路一直在迭代。靠每人记得手动 `git pull` 必然有人落后；把"先同步"焊死在每次开工的第一步，才能保证全队跑同一个版本。标记文件 `~/.baokuan-factory/repo` 由 `install.sh` 写入，sync 靠它找到仓库。

## 然后：判断用户在哪一步（决策树）

同步完，按顺序自检，落在第一个不满足的地方就从那开始：

1. **装好了吗？** 检查 `~/.claude/skills/` 下是否有 `nuwa-skill`、`video-distill`、`talking-head-edit`、`hyperframes`。缺 → 让用户在仓库根跑 `./install.sh`（或指 README）。
2. **依赖齐吗？** `ffmpeg`、`whisper-cli`、`yt-dlp`、`bun`、`python3`。缺 → `install.sh` 会列出来，提示 `brew install ...`。
   - **还有一个软依赖容易漏:gstack `/browse`**(检查 `~/.claude/skills/gstack` 或 `~/.claude/skills/browse` 在不在)。它管两件事:**取片时驱动视频号解析器**、**成片时抓素材截图**——成片质感的命根子。`brew` 装不了,但**别被"内部包"带偏**:它是**公开仓库**(github.com/garrytan/gstack,MIT),不用找谁要,自己一行装(需 Bun v1.0+ 和 Git;Bun 见上一条):
     ```
     git clone --single-branch --depth 1 https://github.com/garrytan/gstack.git ~/.claude/skills/gstack && cd ~/.claude/skills/gstack && ./setup
     ```
     `./setup` 会把 `/browse` 等装进 `~/.claude/skills/`,**装完重开一轮 Claude Code** 才生效(当前会话已加载旧 skill 列表)。**临时不装也能跑**:视频号取片改备选工具(video-distill Phase 0 列了 `wx_channels_download`),抓截图改手动塞——让用户把权威截图存进本片 `build/news/`,你再套卡片。`install.sh` 也会顺带报它在不在、并打这条命令。详见排错区「没 gstack」。
3. **蒸馏过自己吗？** 读 `~/.baokuan-factory/profile`（一行，指向用户自己的 profile SKILL.md 路径）。
   - 文件不存在或指向的文件不在 → 走 **Phase O**（一次性 onboarding）。
   - 存在且有效 → 直接进 **Phase 1**，把该 profile 当注入源。

> 为什么用 `~/.baokuan-factory/profile` 这个标记文件：每个同事翻拍时都要注入**他自己**的口吻，机器上可能蒸馏过好几个人（对标对象也会被蒸馏）。用一个显式标记记住"我是谁"，避免每次猜或问。

## Phase O · 第一次：蒸馏你自己（一次性，约 15-30 分钟）

目标：产出**用户本人**的 `skills/<handle>/SKILL.md`，作为后续所有翻拍的口吻+品味注入源。

1. 问用户两件事：**handle**（英文短名，如 `0xkaiwen`）+ **素材入口**（X/小红书/播客/公众号/LinkedIn 链接，越多越准；至少给一个主阵地）。
2. 调用 **nuwa-skill**，让它蒸馏**用户自己**：把素材链接喂进去，按女娲的「蒸馏用户自己」路径走（女娲 SKILL.md 里有这个特殊场景）。
3. 产物落在仓库 `skills/<handle>/`。蒸馏完，把路径写进标记文件：
   ```bash
   mkdir -p ~/.baokuan-factory
   echo "<绝对路径>/skills/<handle>/SKILL.md" > ~/.baokuan-factory/profile
   ```
4. 跟用户确认：核心心智模型、表达DNA、从夯到拉品味是否像本人。不像就让 nuwa 再精炼一轮（女娲有「更新已有 Skill」流程）。

> 注意：蒸馏的是**用户自己**，不是对标对象。对标对象的人设如果也想要（比如要模仿某博主），那是另一次 nuwa 蒸馏，存成另一个 handle，别覆盖用户自己的。

## Phase 1..N · 每条对标爆款：拆解 → 翻拍 → 成片 → 文案

每条对标视频独立跑一遍。把用户给的链接/文件交给 **video-distill**，它内部有完整 Phase 0-5；本 skill 的职责是**确保两个注入点不被跳过**、**确保中间真的写出一份「翻拍稿」**（最容易被漏掉的一步），以及在翻拍稿之后接上成片。

> **整条链路五步，别在第 3 步断档**:`取片+拆解 → 翻拍角度 → 写翻拍稿 → 成片 → 文案`。最常见的翻车是**拆完直接想去成片，跳过了"写翻拍稿"**——结果没有可录的脚本,人没法录,口播引擎(卡片/截图/字幕)也就全没了。「翻拍角度」只是**立场建议**(写在 `拆解.md` 里),不是能照着念的稿子;真正能录的逐字脚本是 **`口播/<片名>/翻拍稿.md`**,必须单独写出来。

**Step 1 · 取片 + 拆解**（video-distill Phase 0-3）
- 调用 video-distill，给对标视频链接/文件。它会取片（视频号用 sph 解析器、YouTube/抖音用 yt-dlp）、whisper 转写、产出 `拆解.md`（一句话选题/叙事骨架/为什么有效/金句/论点分档）。
- 这一步是**中性**的——跟用户是谁无关，先把"它为什么火"拆干净。

**Step 2 · 翻拍角度**（video-distill Phase 4）← **注入① 品味**
- 先 `Read ~/.baokuan-factory/profile` 指向的用户 profile，重点读「核心心智模型」「从夯到拉/评分品味」。
- 用它给原视频每个论点打档（夯/哈/拉），定翻拍打法：正着翻、反着锐评、还是元视频。写进 `拆解.md` 的「翻拍角度」节。
- 落差就在这：注入的是**立场**——用户站哪、锐评什么。
- ⚠️ 这步只产出**角度/立场**(写进 `拆解.md`),**不是翻拍稿**。别在这里停手就去成片。

**Step 3 · 写翻拍稿**（video-distill Phase 3.5 洗稿）← **这步以前总被漏，是断链元凶**
- **产物**:`口播/<片名>/翻拍稿.md` —— 一份**能直接照着念的逐字口播脚本**(不是 bullet 角度)。这是 Step 4 成片的输入;没有它,人没法录、talking-head-edit 也没东西可剪。
- 跑 **video-distill Phase 3.5**:先做**个人元素审计**(把原作者的身份/经历/作品名/被点名/借用例子逐条揪出来,产一张映射表,跟用户对齐),再**洗稿**——骨架观点照搬,但把"原作者这个人"彻底换成用户自己(用户没有的亲身经历**标红问用户,绝不替他编**)。
- **开头黄金 5 秒**:第一句必须是钩(暴论/认同/反直觉框架),**别用自我介绍开场**;紧跟借名权威 + 浓缩承诺,第一句里就有"你"。(见 video-distill Phase 3.5 hook 段)
- 顺带读 profile 的「表达 DNA」给稿子定调,但**立场以 Step 2 拆解里的翻拍角度为准**。
- 写完跟用户过一遍:还剩没剩原作者的痕迹?hook 够不够炸?用户点头,才进成片。

**Step 4 · 成片**（按形态选 skill）
- **真人出镜口播（talking head）** → 用户照翻拍稿录好竖屏口播,把录音 mp4 交给 **talking-head-edit**:它产出双语字幕 + 卡片 widget + 顶部章节进度条 + 可换主题,`hyperframes render` 出成片。这是口播号的主路径。**别把素材/卡片当事后装饰——它是成片质感的命根子,跟字幕同等重要**,所以这一步明确包含三件事(都以 talking-head-edit 的引擎为准,见下「素材与样式的真源」):
  - **素材收集**:他每提一个术语/人/产品/数字/电影,就得配一张权威截图。用 gstack `/browse` 抓官网/权威媒体/Wikipedia 的图,存进本片 `build/news/`(截图)、`build/naval/`(剪入的真访谈片段)。素材要**权威、清晰、对题**,别拿不相干首页凑数。**没有 `/browse` 怎么办**:这是 gstack 的能力,没装就抓不了图。**绝不因此把这步跳过、或拿空卡/编的图糊弄**——明确告诉用户"我这边没有 /browse,抓不了截图",让他装 gstack 或手动把截图丢进 `build/news/`,你再继续套卡片。素材是成片质感的命根子,宁可停下要,也别出没素材的成片。
  - **卡片样式(widget)**:`news`(大字 stat/截图)、`duel`(左小灰 vs 右大金的数字/概念对决)、`quote`(名人金句)、`clip`(真访谈片段)、`book`(海报+大字)、`titlecard`(报幕大字坑)、`recap`(逐条点亮总结)。卡片要**密**(参考片几乎每几秒一张)、时间对齐他说那句话。
  - **组件/视觉样式**:主题配色(Claude 暖 / Linear 冷 / Vercel / 琥珀)、双语字幕 a/b 样式与描金、顶部章节进度条、字体子集。
  - 纪律:**字幕逐字贴音频**(翻拍稿只兜底)、**渲染前先出 `review.html` 给用户审**(素材权不权威/卡片对不对/主题色/时间点)、终版用 standard 别盲上 high。
- **图文/动画/纯混剪（无真人或大量动效）** → 直接用 **hyperframes** 全家桶手写 HTML 合成。
- 两条底层都是 hyperframes 渲染;talking-head-edit 给口播一套现成的字幕+卡片引擎,不用从零写 HTML。

> **素材与样式的真源(别在本 skill 里复制一份)**:卡片字段、组件样式、主题、素材收集纪律的**权威定义全在 talking-head-edit 引擎里**,装好后在 `~/.claude/skills/talking-head-edit/engine/`:`DESIGN.md`(颜色/字体/字幕/卡片/章节/主题的完整规范)、`build_caps.py`(各卡片实际怎么渲)、`review_page.py`(素材+卡片审阅页)、`make_groups.template.py`(字幕模板)。本 skill 只点名"这一步要做素材收集+套卡片/组件样式",**具体规格一律去读引擎的 `DESIGN.md`**——这样样式只有一处真源,迭代不漂移。

**Step 5 · 四平台文案**（video-distill Phase 5）← **注入② 口吻**
- 先 `Read` 用户 profile，重点读「表达 DNA」「价值观与反模式」。
- 用它的口吻写**抖音 / 微信视频号 / 小红书（中文）+ X（英文）**的标题+正文+hashtag，每平台 2-3 个备选。贴成片实际内容，不套空模板、不造假数据、不用长破折号。
- 落差在这：注入的是**说话方式**——梗、节奏、忌讳词。

## 两个注入点（这是本 skill 的命根子，别跳过）

| 步骤 | 读 profile 的哪部分 | 注入的是 | 为什么分开 |
|------|------------------|---------|-----------|
| Step 2 翻拍角度 | 核心心智模型 / 从夯到拉品味 | **立场**：站哪、锐评啥、反着做哪点 | 换题材时品味骨架不变 |
| Step 5 平台文案 | 表达 DNA / 反模式 | **口吻**：梗、节奏、忌讳词 | 换号（如小红书走另一人设）只换这一处 |

（Step 3 写翻拍稿也会读 profile 的「表达 DNA」给稿子定调，但它的产物是**口播脚本**本身，不在这张"注入对比表"里——这张表讲的是同一条拆解换人设复用时只动哪两处。）

立场和口吻是两回事。拆开注入，才能"同一条拆解，换个人设重新发一遍"而不用重做。

## 产物落位（两棵树，别混）

团队实际是**两个目录树**，一棵管"读懂别人",一棵管"做自己的成片"。照这个来，别自创结构：

```
<工作区>/                       # 如 clipping
├── 案例库/<slug>/             # 【蒸馏树】每条对标视频一个，video-distill 产出
│   ├── video.mp4              软链原片
│   ├── audio.wav  caption.srt  caption.txt
│   ├── source.txt             来源链接 + 下载方式 + 规格
│   └── 拆解.md                ★选题/骨架/手法/金句/翻拍角度(立场)
└── 口播/<片名>/               # 【生产树】每条要做的成片一个，翻拍稿 + 成片在这
    ├── 翻拍稿.md              ★Step 3 产出：能照着念的逐字脚本
    ├── build/                talking-head-edit 引擎工作目录
    │   ├── news/  naval/      素材截图 / 真访谈片段
    │   ├── fonts/  groups.full.json  widgets.json  theme.json  chapters.json
    │   ├── index.html  review.html
    │   └── video.mp4 → 录音文件
    └── <片名>-成片.mp4        终版渲染输出
```

- **蒸馏 → `案例库/<slug>/`**，**翻拍稿 + 成片 → `口播/<片名>/`**。slug 用对标视频的英文短名；片名用你这条成片的名字（可中文）。
- 平台文案 `平台文案.md` 跟成片走（放 `口播/<片名>/`）或跟拆解走都行，写清是哪条。
- 一条对标视频可能翻拍成多条成片：一个 `案例库/<slug>/` 对多个 `口播/<片名>/`，正常。

## 依赖与排错（速查）

- **视频号下载**：别上 mitmproxy。用在线解析器 `https://sph.litao.workers.dev/`（`POST /api/fetch_video_profile {"url": 分享链}`）拿明文真链直接 curl。详见 video-distill Phase 0。
- **缺 ffmpeg/whisper**：`brew install ffmpeg whisper-cpp`。whisper 模型优先复用机器上已有的，别重复下。
- **缺 yt-dlp / bun**：`brew install yt-dlp`；bun 见 install.sh。
- **没 gstack `/browse`**：视频号取不了片、成片抓不了素材截图（成片质感命根子）。gstack `brew` 装不了，但它是**公开仓库**（github.com/garrytan/gstack，MIT），**不用找团队要**，自己一行装（需 Bun v1.0+ 和 Git）：
  ```
  git clone --single-branch --depth 1 https://github.com/garrytan/gstack.git ~/.claude/skills/gstack && cd ~/.claude/skills/gstack && ./setup
  ```
  `./setup` 会把 `/browse` 等装进 `~/.claude/skills/`，**装完重开一轮 Claude Code** 生效；升级用 `/gstack-upgrade`。**临时没有照样能跑**：视频号取片改备选下载工具，截图让用户手动塞进 `build/news/`，别因此跳过素材或拿空卡糊弄。
- **拆完没有"翻拍稿"、没法成片**：这是最常见的断链——别跳过 **Step 3 写翻拍稿**（产出 `口播/<片名>/翻拍稿.md`）。「翻拍角度」只是立场，不是能念的稿。
- **没卡片/没截图**：八成是上一条（没翻拍稿就没录音、talking-head-edit 没被触发），或没 `/browse`。先补翻拍稿、补素材，再成片。
- **profile 注入不准**：八成是 Phase O 蒸馏得糙，或 `~/.baokuan-factory/profile` 指错了。重蒸或改标记文件。
