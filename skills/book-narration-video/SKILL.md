---
name: book-narration-video
description: |
  讲书/说书视频：把一本书（或章节/摘录/听书稿）变成你自己口吻的口播成片 + 四平台文案。
  流程：书源获取 → 讲书拆解（核心论点/章节骨架/金句）→ 注入 profile 写讲书稿 → talking-head-edit 成片（book 卡为主）
  或 hyperframes TTS 旁白成片 → video-distill Phase 5 文案。
  触发词：「讲这本书」「把这本书做成视频」「说书视频」「书籍解读视频」「读书博主」「拆书视频」
  「这本书帮我做成口播」「书摘视频」「听书解读」。
  边界：只要拆书笔记/读书笔记不成片 → 不是本 skill；完整链路（书→成片→文案→发号/onboarding）→ hedj-factory 总入口；
  输入是对标短视频/链接不是书 → video-distill 的活；只拆解爆款视频结构 → video-distill；
  只要 TTS 旁白不做口播卡片 → hyperframes / website-to-hyperframes；只发不上号 → 别抢 social-auto-upload。
---

# 讲书视频 · book-narration-video

> 目标不是「把书念一遍」，而是**把一本书蒸馏成你能讲、观众想听的讲书视频**——核心主张 + 叙事骨架 + 金句 + 你的讲书角度。
> 和 video-distill 的「翻拍对标视频」是**平行线 C**（hedj-factory 线 B 是视频、线 C 是讲书）：输入从「别人的爆款视频」换成「一本书」，下游洗稿、注入 profile、成片、文案、发布全部复用。

## 核心理念

一份合格的讲书拆解，要能回答讲书者的三个问题：
1. **这本书真正在说什么**——抽掉章节细节后，剩下的那一句话主张。
2. **它怎么论证的**——章节/论点骨架，换一本书也能套同样的讲法。
3. **为什么值得讲**——可迁移的手法（钩子类型、情绪曲线、金句、反直觉点），不是夸「书写得好」，而是说清「好在哪个机关上」。

**关键区分**：讲的是**你的解读**，不是替作者念全书。解读式讲书 ≠ 整本朗读（版权风险见 Phase 0）。

---

## 执行流程

### Phase 0: 接活与书源

确认四件事（用户没说就用默认值直接推进，别来回问）：
1. **书是什么**：书名 + 作者 + 讲哪几章/哪一段（默认：全书核心 1-3 个论点，15-25 分钟口播量）。
2. **书源在哪**：用户提供的文字稿 / epub / pdf / 公众号书评 / 听书笔记 / 摘录。没有全文就按用户给的章节范围讲，**别自己去盗版站整本抓**。
3. **放哪**：默认 `案例库/<book-slug>/`（slug 用英文短名，如 `atomic-habits`）。封面图存 `cover.jpg`（喂 book 卡）。
4. **成片形态**：默认真人出镜口播 → talking-head-edit；用户明确要纯旁白/TTS → hyperframes TTS 路径。

#### 书源获取（按优先级）

- **用户已有文字稿/笔记**：直接 Read，最省事。
- **epub / pdf / txt / md**：用本 skill 的 `extract_book.py` 提取（用脚本，别手搓解析）。**路径必须绑到 skill 安装根**，别写相对 `scripts/...`（从工作室目录跑会找错）：

```bash
SKILL_ROOT="${CLAUDE_SKILL_ROOT:-$HOME/.claude/skills/book-narration-video}"
# 若本机是 symlink 到仓库：也可 SKILL_ROOT="$(dirname "$(dirname "$(readlink -f "$0")")")" 在包装脚本里
python3 "$SKILL_ROOT/scripts/extract_book.py" 书.epub --list
python3 "$SKILL_ROOT/scripts/extract_book.py" 书.epub --out 案例库/<book-slug>/ --chapters 2-5
python3 "$SKILL_ROOT/scripts/extract_book.py" 书.pdf  --out 案例库/<book-slug>/ --pages 10-25
# 已存在原文.txt 时默认拒绝覆盖；确认覆盖加 --force（先备份同目录 .bak）；预览用 --dry-run
```

  产出 `案例库/<book-slug>/原文.txt`（带章节分隔符）、人读 `source.txt`、机器可读 `extraction-manifest.json`（`schema_version: 1`；每次提取的**完整**输入/输出 SHA-256 都在记录里）。若已有 manifest **损坏或结构不对**，脚本 **fail-closed**：拒绝写入任何输出 / 备份 / 追加，避免 provenance 静默丢历史。epub 元数据自动读，txt/pdf 用 `--title`/`--author` 补。长书**先 `--list` 再按范围提取**，脚本默认 `--max-chars 60000`（禁止负数；`0`=不限）。pdf 优先 `pdftotext`（poppler）。`--name` 禁止绝对路径与 `..`，可含子目录（备份落在同子目录）。
- **只有书名**：让用户给 3-5 条他最想讲的点 + 一段**他自己确认过的摘录**；或公开书评/目录作**骨架参考**——**不得把二手书评写成「原书主张」**；拆解.md 须标注观点来源（原书摘录 / 用户口述 / 公开书评）。
- **封面图**：gstack `/browse` 搜书名 + 作者抓权威封面（Amazon/豆瓣/出版社），存 `案例库/<book-slug>/cover.jpg`；没 `/browse` 让用户手动给图。

#### 版权纪律（命根子，别跳过）

- **解读式讲书**（你的观点 + 书的核心论点 + 少量引用）——主流读书博主形态，优先走这条。
- **整章/整本朗读**——有版权风险，**默认不做**；用户坚持要朗读式，明确提醒风险并建议只讲摘录+解读。
- **引用**：金句可引用，注明出处；大段原文照念要克制。
- 产物 `source.txt` / `extraction-manifest.json`：书名、作者、ISBN（如有）、每次提取的输入路径与完整 SHA-256、输出文件与输出 SHA-256、讲书范围。

### Phase 1: 读原文 + 写讲书拆解

读完书源文本（用户给的书摘/章节，或 Phase 0 提取的 `原文.txt`），产出 `案例库/<book-slug>/拆解.md`。模板对齐 video-distill，但把「视频」换成「书」：

```markdown
# 拆解：《书名》— <一句话讲书角度>

> 来源：<作者> · <出版年/形式> · 讲书范围：<第几章/哪几个论点>。
> 素材见 `source.txt`，封面 `cover.jpg`。

## 一句话选题
**<抽掉章节细节后，这本书真正在主张的那一句>。** <可补一句点透它的钩子机制>

## 核心结构（章节/论证骨架）
1. **钩子**：<开场怎么抓人——反直觉结论/痛点/名人背书>
2. <逐段拆：抛问题/给框架/举证/案例/拔高/行动号召>
   ...
N. **结尾**：<怎么收的，留什么行动/思考题>

## 为什么值得讲（可迁移的手法）
- **<手法名>**：<这个机关具体怎么起作用>
- ...

## 金句 / 可引用原话
- "<书中可直接截图传播的原话>"
- ...

## 章节要点表（可选）
| # | 章节/论点 | 内核 | 一句话 |
|---|----------|------|--------|

## 讲书角度（给<目标风格>的改造建议）
- **立场**：<你站哪、锐评什么、和主流解读有何不同>
- **形式建议**：<口播/卡片密度/案例替换>
- **风险点**：<数字核对、引用边界、别替作者扩写未提及的观点>
```

写拆解的心法同 video-distill Phase 3：**骨架可迁移、手法说机关、金句单独拎、讲书角度要落地**。

### Phase 2: 讲书角度 ← **注入① 品味**

先 `Read ~/.hedj-factory/profile` 指向的用户 profile，重点读「核心心智模型」「从夯到拉/评分品味」。

用它给书的每个论点打档（夯/顶级/拉），定讲书打法：顺着作者讲、反着锐评、还是「这本书好/坏在哪」。写进 `拆解.md` 的「讲书角度」节。

⚠️ 这步只产出**角度/立场**，**不是讲书稿**。别在这里停手就去成片。

### Phase 3: 写讲书稿 → `口播/<片名>/讲书稿.md`

**产物**：一份**能直接照着念的逐字口播脚本**。没有它，人没法录、talking-head-edit 也没东西可剪。

#### 3.1 个人元素审计（讲书版）

通读拆解，逐条揪出需要「换成你」的东西：

| 类型 | 在书里/拆解里长啥样 | 怎么处理 |
|------|---------------------|----------|
| **作者身份/经历** | 作者的第一人称轶事 | 换成你的等价经历；**你没有的标红问用户，绝不编** |
| **读者假设** | 「你一定经历过…」 | 换成你的受众画像 |
| **案例/场景** | 书里的行业案例 | 换成你圈子里的等价场景 |
| **价值观腔调** | 作者的招牌话术 | 换成 profile 的表达 DNA |

**保留不动**：书的客观论点、可引用金句、普世框架（如「复利」「杠杆」）。

#### 3.2 写稿纪律

- **引用 video-distill Phase 3.5 的黄金 5 秒 hook**：第一句必须是钩，**别用自我介绍开场**。
- 读 profile「表达 DNA」定调；**立场以 Phase 2 讲书角度为准**。
- 每提到一本书/一个理论 → 标记后续上 **`book` 卡**（封面用 `cover.jpg`）。
- 每引用金句 → 标记后续上 **`quote` 卡**。
- 结尾枚举要点 → 标记 **`recap` 卡**。
- 洗完通读：还剩作者个人痕迹吗？hook 够不够炸？用户点头才进成片。

**禁忌**：别写成读书笔记体（「第一章讲了…第二章讲了…」）；要是**口播脚本**，有节奏、有「你」。

### Phase 4: 成片

#### 路径 A · 真人出镜口播（默认）→ talking-head-edit

用户照讲书稿录好竖屏口播，把录音 mp4 交给 **talking-head-edit**。

讲书片的卡片纪律（规格**只读** `<ENG>/DESIGN.md`，别在本 skill 复制）：
- **`book` 卡**：每深入讲一本书/一个理论就上；左书封（`cover.jpg`）+ 右大号公式/关键词 + 来源。
- **`quote` 卡**：引用原话时上。
- **`chart` / `duel` 卡**：书里有数据/对比时用。
- **`recap` 卡**：结尾「N 个 takeaway」逐条点亮。
- **卡片要密**：讲书片几乎每 10-20 秒一张，对齐他说那句话的时间点。

素材收集：书封、作者照片、权威媒体对书的报道截图 → `build/news/`。没 gstack `/browse` 就让用户手动给图，**别拿空卡糊弄**。

#### 路径 B · 纯旁白/TTS → hyperframes

用户不要真人出镜时：
1. 讲书稿 → `npx hyperframes tts` 生成 `narration.wav`（中文音色见 hyperframes `references/tts.md`）。
2. `npx hyperframes transcribe narration.wav` → `transcript.json`。
3. 按 **website-to-hyperframes** 的 storyboard → build → render 流程出片；卡片用 HTML 合成而非 talking-head-edit widget。

两条路径底层都是 hyperframes 渲染；口播号默认走路径 A。

### Phase 5: 四平台文案 ← **注入② 口吻**

**直接引用 video-distill Phase 5**，不复制规格：
- 先 `Read` 用户 profile 的「表达 DNA」「价值观与反模式」。
- 写抖音 / 微信视频号 / 小红书（中文）+ X（英文）标题+正文+hashtag。
- 内容贴成片实际内容，不套空模板，不造假数据，不用长破折号。
- 写进 `口播/<片名>/平台文案.md`。

### Phase 6: 一键发布（可选）

走 **hedj-factory Step 6** / social-auto-upload（`sau` CLI）。发前逐条确认，详见 hedj-factory 依赖区。

---

## 两个注入点（和 hedj-factory 对齐）

| 步骤 | 读 profile 的哪部分 | 注入的是 |
|------|---------------------|---------|
| Phase 2 讲书角度 | 核心心智模型 / 品味 | **立场**：站哪、锐评啥 |
| Phase 5 平台文案 | 表达 DNA / 反模式 | **口吻**：梗、节奏、忌讳词 |

Phase 3 写讲书稿也会读「表达 DNA」定调，但产物是**口播脚本**本身。

---

## 产物落位（两棵树，别混）

```
<工作区>/
├── 案例库/<book-slug>/          # 【蒸馏树】每本书一个
│   ├── cover.jpg                书封（book 卡用）
│   ├── source.txt               人读来源记录（每条提取含完整输入/输出 SHA256）
│   ├── extraction-manifest.json 机器可读 provenance（接 source_lock / content-package）
│   ├── 原文.txt                 extract_book.py 提取的书源文本（按范围；覆盖需 --force）
│   └── 拆解.md                  ★讲书角度/骨架/金句
└── 口播/<片名>/                 # 【生产树】每条讲书成片一个
    ├── 讲书稿.md                ★Step 3 产出：逐字口播脚本
    ├── build/                   talking-head-edit 工作目录
    └── <片名>-成片.mp4          终版渲染输出
```

一本书可能讲成多条成片（如分上/下集）：一个 `案例库/<book-slug>/` 对多个 `口播/<片名>/`，正常。

---

## 依赖

- **profile**：`~/.hedj-factory/profile` 指向的用户 SKILL.md（Phase O 用 nuwa-skill 蒸馏）。
- **talking-head-edit**：口播成片引擎（路径 A）。
- **hyperframes 全家桶**：TTS + 渲染（路径 B）；规格见 `references/tts.md`。
- **video-distill Phase 5**：平台文案口吻纪律（只引用，不复制）。
- **gstack `/browse`**：抓书封/权威截图（软依赖，见 hedj-factory 排错区）。
- **social-auto-upload**：发布（可选，Step 6）。

---

## 排错

- **没讲书稿就想去成片**：先写 `口播/<片名>/讲书稿.md`，和「讲书角度」是两回事。
- **book 卡没书封**：检查 `cover.jpg` 是否在 `案例库/<book-slug>/`，build 时复制或软链到 `build/news/`。
- **讲成读书笔记**：稿子是给观众听的，不是给编辑看的；加 hook、加「你」、加卡片锚点。
- **书太长**：只讲 1-3 个核心论点，别试图一条视频讲完整本书；提取时先 `--list` 再按范围取，别整本进上下文。
- **输出已存在 / 路径报错**：默认拒绝覆盖；加 `--force` 会先备份 `.bak`。`--name` 不能含 `..` 或绝对路径。预览用 `--dry-run`。
- **pdf 提取出来是空/乱码**：多半是扫描版（要 OCR，本脚本不管）或没装 poppler——`brew install poppler` / `apt install poppler-utils` 后重跑；内置纯 Python 兜底只吃简单 pdf。
- **和 video-distill 抢触发**：用户给的是**书**不是**视频链接**才用本 skill；给抖音/视频号链接 → video-distill。
- **测试**：`python3 "$SKILL_ROOT/scripts/test_extract_book.py" -v`（或 `bash "$SKILL_ROOT/scripts/smoke_test.sh"`；勿用 `python -m unittest /abs/path`）。

---

## 移植到 content-package v2 / 状态机版（衔接备忘）

**完整步骤与文件清单**见：[references/transplant-to-state-machine.md](references/transplant-to-state-machine.md)。

本仓库 GitHub `main` 暂无 `source_lock.py`；若你本地已是状态机版，**不要整文件覆盖 SKILL**，也**不要** `git merge` Cloud `main`。建议：

```bash
# 打包可拷贝文件（在 Cloud clone）
python3 skills/book-narration-video/scripts/pack_transplant_bundle.py --out /tmp/book-extract-bundle
# 或在本地状态机仓库：git fetch + checkout 仅 scripts（见 reference）
```

| 本 skill 产物 | 状态机接法 |
|---|---|
| `extraction-manifest.json` 的 `input_sha256` | 上游 provenance |
| `案例库/<slug>/原文.txt` | `source_lock.py create … --source … --source-type adapted` |
| `source.txt` | 人读记录，**不作**状态真源 |
| `拆解.md` | → 项目内 `制作准备.md` / `artifacts.brief` |
| `讲书稿.md` | → **统一为** `口播/<项目>/口播稿.md`（勿并存两个正式稿名） |
| `cover.jpg` | 独立参考素材 |
| `平台文案.md` | `artifacts.platform_copy` |

健康内容另加 `--risk-domain health`（以本地 CLI 为准）。
