---
name: baokuan-factory
description: |
  爆款工厂：把"别人的爆款短视频"变成"你自己口吻的成片 + 全平台文案"的一条龙总入口。串起四件事——①女娲蒸馏你自己的表达DNA（一次性 onboarding）②video-distill 蒸馏对标爆款→拆解/翻拍角度 ③hyperframes 把翻拍稿做成成片 ④四平台爆款文案。它是路由器/checklist，按顺序调度 nuwa-skill / video-distill / hyperframes，并在翻拍和文案两处注入你自己的 profile。
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
   取片 → 转写 → 拆解 → 翻拍角度◄注入①品味 → 〔hyperframes 成片〕 → 四平台文案◄注入②口吻
```

依赖的子 skill（install.sh 已一并装好）：
- **nuwa-skill**（女娲造人）——蒸馏一个人的思维操作系统成一个 Skill。这里用来蒸馏**用户自己**。
- **video-distill**（视频蒸馏）——取片/转写/拆解/翻拍角度/四平台文案。线B 的主力。
- **hyperframes 全家桶**（hyperframes / -cli / -registry / gsap / website-to-hyperframes）——把翻拍稿做成 HTML 视频合成并渲染成片。

详细全流程图见本 skill 同级或仓库的 `docs/SOP.md`。

## 开工前：先判断用户在哪一步（决策树）

按顺序自检，落在第一个不满足的地方就从那开始：

1. **装好了吗？** 检查 `~/.claude/skills/` 下是否有 `nuwa-skill`、`video-distill`、`hyperframes`。缺 → 让用户在仓库根跑 `./install.sh`（或指 README）。
2. **依赖齐吗？** `ffmpeg`、`whisper-cli`、`yt-dlp`、`bun`、`python3`。缺 → `install.sh` 会列出来，提示 `brew install ...`。
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

每条对标视频独立跑一遍。把用户给的链接/文件交给 **video-distill**，它内部有完整 Phase 0-5；本 skill 的职责是**确保两个注入点不被跳过**，以及在拆解后接上 hyperframes 成片。

**Step 1 · 取片 + 拆解**（video-distill Phase 0-3）
- 调用 video-distill，给对标视频链接/文件。它会取片（视频号用 sph 解析器、YouTube/抖音用 yt-dlp）、whisper 转写、产出 `拆解.md`（一句话选题/叙事骨架/为什么有效/金句/论点分档）。
- 这一步是**中性**的——跟用户是谁无关，先把"它为什么火"拆干净。

**Step 2 · 翻拍角度**（video-distill Phase 4）← **注入① 品味**
- 先 `Read ~/.baokuan-factory/profile` 指向的用户 profile，重点读「核心心智模型」「从夯到拉/评分品味」。
- 用它给原视频每个论点打档（夯/哈/拉），定翻拍打法：正着翻、反着锐评、还是元视频。写进 `拆解.md` 的「翻拍角度」节。
- 落差就在这：注入的是**立场**——用户站哪、锐评什么。

**Step 3 · 成片**（hyperframes）
- 把翻拍稿/分镜交给 hyperframes：用 HTML 合成（字幕、转场、音频驱动、TTS 旁白等），`hyperframes render` 出 mp4。
- 细节全在 hyperframes / hyperframes-cli skill 里，按它走。本 skill 只负责"拆解+翻拍稿就绪 → 转交 hyperframes"。
- 纯口播/真人出镜的不需要 hyperframes，可跳过本步直接发；hyperframes 主要解决"图文/动画/混剪"类成片。

**Step 4 · 四平台文案**（video-distill Phase 5）← **注入② 口吻**
- 先 `Read` 用户 profile，重点读「表达 DNA」「价值观与反模式」。
- 用它的口吻写**抖音 / 微信视频号 / 小红书（中文）+ X（英文）**的标题+正文+hashtag，每平台 2-3 个备选。贴成片实际内容，不套空模板、不造假数据、不用长破折号。
- 落差在这：注入的是**说话方式**——梗、节奏、忌讳词。

## 两个注入点（这是本 skill 的命根子，别跳过）

| 步骤 | 读 profile 的哪部分 | 注入的是 | 为什么分开 |
|------|------------------|---------|-----------|
| Step 2 翻拍角度 | 核心心智模型 / 从夯到拉品味 | **立场**：站哪、锐评啥、反着做哪点 | 换题材时品味骨架不变 |
| Step 4 平台文案 | 表达 DNA / 反模式 | **口吻**：梗、节奏、忌讳词 | 换号（如小红书走另一人设）只换这一处 |

立场和口吻是两回事。拆开注入，才能"同一条拆解，换个人设重新发一遍"而不用重做。

## 产物落位

沿用 video-distill 的约定：每条视频一个 `案例库/<slug>/` 子文件夹（video.mp4 软链 / audio.wav / caption.srt+txt / source.txt / 拆解.md / 平台文案.md）。成片 mp4 放同一文件夹或 hyperframes 工程目录，`source.txt` 记清来源链接和下载方式。

## 依赖与排错（速查）

- **视频号下载**：别上 mitmproxy。用在线解析器 `https://sph.litao.workers.dev/`（`POST /api/fetch_video_profile {"url": 分享链}`）拿明文真链直接 curl。详见 video-distill Phase 0。
- **缺 ffmpeg/whisper**：`brew install ffmpeg whisper-cpp`。whisper 模型优先复用机器上已有的，别重复下。
- **缺 yt-dlp / bun**：`brew install yt-dlp`；bun 见 install.sh。
- **profile 注入不准**：八成是 Phase O 蒸馏得糙，或 `~/.baokuan-factory/profile` 指错了。重蒸或改标记文件。
