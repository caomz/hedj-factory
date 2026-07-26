# 功能：本地个人知识资产蒸馏

## 功能描述

增强现有女娲自我蒸馏流程，使用户可以提供大型本地知识目录，例如 `/Volumes/WorkSSD/Dev/openclaw_mz/knowledge/raw`，并获得两类相互配合的产物：

1. 一份精简的运行时 profile，供 `baokuan-factory` 注入用户的定位、判断标准、内容品味和表达风格。
2. 一套可追溯的个人资产库，沉淀用户的核心观点、做事原则、工作系统、实践证据、内容母题和可复用产品。

新模式必须区分用户原创内容、私有实践证据、改编资料和外部参考。不得复制原始知识库，不得泄露私聊内容，也不得把用户收藏的第三方资料误判为用户原创资产。

## 用户故事

作为一名拥有混合型本地知识库的 AI 内容创作者，我希望女娲能够识别并蒸馏真正代表我本人思考与实践的内容，从而让后续内容生产流程复用我的口吻和判断，同时避免泄露私有数据，也避免把收藏资料和原创知识混在一起。

## 问题说明

女娲目前支持少量本地书籍、访谈稿、文章或链接，但现有流程主要针对公众人物蒸馏，不适合 13,000 多个文件组成的混合知识库：

- Phase 0.5 会把本地素材复制或移动到生成的 skill 中，对大型知识库既不安全，也不现实。
- 当前六个研究维度和 `skill-template.md` 主要围绕公众人物、角色扮演、公开时间线和外界评价设计。
- 面对大型混合目录，目前没有确定性的文件盘点、来源归属策略、重复与版本处理、阅读预算。
- 私聊和工作记录可能包含姓名、内部上下文、账号标识和凭据。
- 当前只有一个 `SKILL.md` 输出；如果把全部证据和内容资产都写进去，会显著增加每次下游调用的上下文成本。
- 当前 onboarding 使用 `skills/<handle>/`，但 `.gitignore` 中可泛化保护个人 profile 的规则是 `skills/*-profile/`。
- 下游流程需要核心心智模型、内容品味分档、表达 DNA、价值观与反模式等固定章节，但女娲通用模板没有保证自我蒸馏一定产出这些内容。

## 建议方案

为女娲增加独立的 `self-local-corpus` 分支，同时保留现有公众人物蒸馏、主题蒸馏和小规模本地语料流程。

新流程：

1. 只盘点目录，不复制文件，也不进行语义读取。
2. 生成可供用户确认的来源策略，将路径划分为原创、私有证据、改编资料、外部参考或排除项。
3. 应用确定性的重复检测、文件准入、隐私和阅读预算规则。
4. 按六个自我蒸馏维度分析通过筛选的素材。
5. 生成精简的 `SKILL.md` 和按需加载的 `assets/` 资产库。
6. 通过自我 profile 专用质量门和隐私检查后，再更新 `~/.baokuan-factory/profile`。

新生成的自我 profile 统一保存到 `skills/<handle>-profile/`，与仓库已有的通用忽略规则一致。已有的 `skills/<handle>/` profile 继续有效，不自动迁移。

## 元数据

**功能类型：** enhancement
**复杂度：** high
**影响系统：** 女娲 skill 指令和模板、女娲辅助脚本、爆款工厂 onboarding、触发评测、文档、个人 profile 存储约定
**依赖：** Python 3 标准库、Markdown/YAML frontmatter、现有 `baokuan-factory` profile 标记文件；不引入新的包管理器或运行时依赖

## 上下文参考

### 实施前必须阅读

- `AGENTS.md`：仓库编码、验证和安全规则；目前是未跟踪文件，不得在本功能中隐式提交。
- `skills/nuwa-skill/SKILL.md`：现有公众人物、主题、本地语料、检查点、六维研究、更新和质量验证流程。
- `skills/nuwa-skill/references/extraction-framework.md`：心智模型验证、表达 DNA 测量、矛盾处理和来源质量规则。
- `skills/nuwa-skill/references/skill-template.md`：公众人物输出契约；非自我蒸馏流程必须保持不变。
- `skills/nuwa-skill/scripts/merge_research.py`：当前固定的 `01` 至 `06` 研究汇总约定。
- `skills/nuwa-skill/scripts/quality_check.py`：当前公众人物 profile 质量门和 CLI 行为。
- `skills/baokuan-factory/SKILL.md`：onboarding 路由、profile 标记文件和下游两个注入点需要的章节。
- `docs/SOP.md`：自我 profile、对标蒸馏、脚本写作、渲染和发布之间的正式流程。
- `.gitignore`：现有 `skills/*-profile/` 隐私规则和媒体产物排除规则。
- `.optimize/trigger-evals.json`：当前 onboarding 与独立 Nuwa 请求的正负触发样本。

### 需要创建或更新的文件

- `skills/nuwa-skill/SKILL.md`：增加 `self-local-corpus` 路由、检查点、来源规则、阅读预算、输出契约和失败处理。
- `skills/nuwa-skill/references/self-distill-workflow.md`：详细描述来源策略、研究维度、资产卡结构、隐私规则和增量更新。
- `skills/nuwa-skill/references/self-profile-template.md`：不包含公众人物角色扮演语义的运行时自我 profile 模板。
- `skills/nuwa-skill/scripts/inventory_local_corpus.py`：确定性的元数据、hash、文件盘点和来源策略应用工具。
- `skills/nuwa-skill/scripts/merge_research.py`：支持公众人物和自我研究标签，同时保持现有 CLI 兼容。
- `skills/nuwa-skill/scripts/quality_check.py`：自动识别自我 profile，并增加下游契约与隐私检查。
- `skills/baokuan-factory/SKILL.md`：Phase O 接受本地目录，并为新 profile 使用 `skills/<handle>-profile/`。
- `README.md` 和 `docs/SOP.md`：说明目录型自我蒸馏、双输出、隐私规则和兼容性。
- `.optimize/trigger-evals.json`：增加本地目录 onboarding 正向样本和独立人物蒸馏负向样本。
- `tests/test_nuwa_local_corpus.py`：使用标准库测试盘点、来源策略和质量门。
- `tests/fixtures/nuwa-self-distill/`：不含真实个人信息的合成语料和通过/失败 profile fixture。

### 相关文档

- 不需要外部 API 或第三方包文档。该功能完全在本地运行，仅使用 Python 标准库。
- 当前公开行为以 `README.md`、`docs/SOP.md` 和两个 skill 文件为兼容性契约。

### 现有代码模式

- **命名：** skill 是 `skills/` 下的一级目录；个人 profile 应使用已经被忽略的 `-profile` 后缀。
- **错误处理：** Python 脚本输出简洁且可执行的错误信息；输入不存在或验证失败时返回非零退出码。
- **日志：** 辅助脚本输出适合阅读的 Markdown 或 JSON；仓库没有统一日志框架。
- **测试：** 仓库没有根级测试运行器。使用标准库 `unittest`，不引入 `pytest`、`pyproject.toml` 或新的根级依赖文件。
- **注意事项：** `install.sh` 会把每个 `skills/*/` 一级目录建立 symlink，因此个人 profile 仍可被加载，但必须保持 Git 忽略。触发评测会改写已安装 skill 并调用外部 Claude 模型，不属于默认验证命令。

## 公共接口与输出契约

### 盘点 CLI

```bash
python3 skills/nuwa-skill/scripts/inventory_local_corpus.py \
  /absolute/path/to/raw \
  --profile-dir /absolute/path/to/skills/<handle>-profile \
  [--policy /absolute/path/to/source-policy.json] \
  [--max-file-bytes 2000000] \
  [--check]
```

行为约定：

- 解析并验证来源根目录和 profile 输出目录。
- 来源不存在、来源不是目录、输出目录位于来源树内部时拒绝执行。
- 默认跳过 symlink，避免语料扫描逃逸到声明范围之外。
- 盘点全部非隐藏普通文件，但只把受支持的文本格式标记为可进行语义分析。
- v1 支持的语义格式：`.md`、`.markdown`、`.txt`、`.json`、`.jsonl`、`.html`、`.htm`、`.yaml`、`.yml`、`.csv`。
- 不支持的文件和二进制文件只计数，不解析 SQLite、图片、视频、音频或未知格式。
- 记录相对路径、扩展名、字节数、修改时间、SHA-256、一级来源目录、重复组、是否可读取、策略分类和排除原因。
- 未提供 `--policy` 时，所有路径标记为 `unclassified`，生成盘点检查报告。
- 提供 `--policy` 时，按照规则顺序应用 glob，并报告未匹配路径。
- `--check` 只输出统计结果，不写入文件。

生成的私有研究文件：

```text
skills/<handle>-profile/
└── references/
    ├── source-policy.json
    ├── source-manifest.json
    └── research/
        └── 00-source-inventory.md
```

manifest 可以保留本机绝对根路径，因为整个 profile 目录都是私有且被忽略的。`SKILL.md` 和可发布资产只能使用相对来源标识，不得暴露绝对路径。

### 来源策略结构

```json
{
  "schema_version": 1,
  "rules": [
    {"class": "authored", "globs": ["path/**"]},
    {"class": "private-evidence", "globs": ["path/**"]},
    {"class": "adapted", "globs": ["path/**"]},
    {"class": "external", "globs": ["path/**"]},
    {"class": "excluded", "globs": ["path/**"]}
  ]
}
```

规则按文件顺序执行，第一条匹配规则生效。未匹配文件保持 `unclassified`，在完成确认或明确排除前阻止语义蒸馏。

### 自我 Profile 目录

```text
skills/<handle>-profile/
├── SKILL.md
├── assets/
│   ├── index.md
│   ├── positioning.md
│   ├── core-theses.md
│   ├── operating-principles.md
│   ├── systems-and-workflows.md
│   ├── cases-and-evidence.md
│   ├── content-motifs.md
│   └── reusable-products.md
└── references/
    ├── source-policy.json
    ├── source-manifest.json
    └── research/
        ├── 00-source-inventory.md
        ├── 01-positioning.md
        ├── 02-core-theses.md
        ├── 03-decisions-and-behavior.md
        ├── 04-systems-and-cases.md
        ├── 05-expression-dna.md
        └── 06-tensions-and-evolution.md
```

下游默认只加载 `SKILL.md`，目标长度为 3,000 至 6,000 tokens。只有需要深层证据或内容选题时，才读取较大的资产页面。

### 资产卡契约

每项独立资产必须包含：

```yaml
origin: authored | co-created | private-derived | adapted | external
evidence: observation | repeated | validated
visibility: private | sanitized | public-ready
confidence: stated | high | medium | speculation
sources:
  - relative/source/path
```

正文记录：资产结论、解决的问题、证据、适用范围、限制、可复用形式、内容机会和下一步验证。只有外部来源支持的观点不能登记为个人资产，只能作为背景或对比材料。

## 实施计划

### 阶段一：准备

- 在修改路由前，先增加自我蒸馏流程文档和自我 profile 模板。
- 明确精简运行时 profile、私有研究证据和可复用资产页面之间的边界。
- 固化来源优先级、版本选择、阅读预算和隐私默认值。
- 保持现有公众人物、主题流程及旧版 `skills/<handle>/` profile 兼容。

### 阶段二：核心实现

- 使用 Python 标准库实现本地知识目录盘点与来源策略 CLI。
- 在女娲中增加 `self-local-corpus` 分支：
  - 用户要求蒸馏自己并提供目录时触发。
  - 默认纯本地分析；除非用户明确要求外部佐证，否则不联网搜索。
  - 不复制或移动任何原始文件。
  - 盘点完成后暂停，让用户确认来源归属和隐私分类。
- 按六个自我研究维度分析，并保留准确的相对来源路径。
- 应用阅读预算：
  - 原创：每轮读取不超过 20 MB 的合格文件；更大集合拆成明确批次。
  - 私有证据：优先使用已有摘要或分析文件；默认每轮最多 100 个文件或 5 MB；不引用原始聊天内容。
  - 改编资料：每轮最多选择 30 个相关文件。
  - 外部资料：首次语义分析默认排除；只有验证或对比个人观点时才读取具体文件。
- 跳过 SHA-256 完全相同的文件。遇到 `v0.1`、`v0.2`、`v0.3` 等版本，以最高版本为当前版本，旧版本仅作为观点演化证据。
- 一项资产至少需要两个自有来源，或一个自有来源加一个真实决策/案例，才能标记为 `repeated` 或 `validated`。

### 阶段三：集成

- 使用自我模板生成 `SKILL.md`，不套用公众人物角色扮演模板。
- 保证下游所需章节存在：
  - 定位与受众；
  - 核心心智模型；
  - 决策启发式；
  - 表达 DNA；
  - 内容品味和强弱分档；
  - 价值观与反模式；
  - 证据边界；
  - 深层资产页面链接。
- 更新爆款工厂 Phase O，使其同时接受社交链接、文件和本地目录。
- 新 profile 使用 `skills/<handle>-profile/SKILL.md` 写入 `~/.baokuan-factory/profile`；已有合法旧 marker 继续使用，不自动迁移。
- 更新 README、SOP 和触发评测样本。

### 阶段四：测试与验证

- 为确定性盘点、glob 优先级、重复检测、symlink 跳过、不支持格式、大小限制和非法路径增加单元测试。
- 为现有公众人物质量检查增加回归测试。
- 为自我 profile 增加必需章节、来源可追溯、token 预算和隐私拒绝测试。
- 使用临时合成语料执行端到端测试；自动测试不得使用或复制用户真实私有知识库。
- 实现完成后，对真实目录执行只读 `--check`，验证规模和性能。
- 外部触发评测是可选项，因为它会改写已安装状态并消耗模型 quota。

## 有序任务

### CREATE `skills/nuwa-skill/references/self-distill-workflow.md`

- **IMPLEMENT：** 定义路由、来源类别、确认检查点、六个分析维度、阅读预算、版本优先级、资产评分、隐私脱敏、增量更新和输出边界。
- **PATTERN：** 沿用 `references/extraction-framework.md` 的详细方法论风格，但面向自我蒸馏而非公众人物角色扮演。
- **IMPORTS：** 无。
- **GOTCHA：** 不得把当前用户的中文目录名硬编码进公共功能，只能作为示例。
- **VALIDATE：** `git diff --check -- skills/nuwa-skill/references/self-distill-workflow.md`

### CREATE `skills/nuwa-skill/references/self-profile-template.md`

- **IMPLEMENT：** 提供包含所有爆款工厂依赖章节和资产链接的精简 profile 模板。
- **PATTERN：** 复用 `skill-template.md` 的 frontmatter 和证据约定，但将角色扮演规则替换为第一方协作规则，并加入“不得编造我的经历”硬约束。
- **IMPORTS：** 无。
- **GOTCHA：** 生成的运行时 profile 控制在 3,000 至 6,000 tokens，原始证据留在 `references/`。
- **VALIDATE：** `rg -n '^## (定位与受众|核心心智模型|决策启发式|表达DNA|内容品味与评分标准|价值观与反模式|诚实边界)' skills/nuwa-skill/references/self-profile-template.md`

### CREATE `skills/nuwa-skill/scripts/inventory_local_corpus.py`

- **IMPLEMENT：** 实现盘点 CLI、确定性遍历、SHA-256 重复分组、格式和大小准入、策略加载、顺序 glob 匹配、Markdown 摘要、JSON manifest 和 `--check`。
- **PATTERN：** 使用现有女娲脚本中的 `pathlib`、UTF-8、`argparse`、显式验证和非零退出码模式。
- **IMPORTS：** 仅使用 `argparse`、`fnmatch`、`hashlib`、`json`、`pathlib` 等 Python 标准库。
- **GOTCHA：** 不跟随 symlink；盘点阶段不解析来源正文；不在来源目录内写文件；不复制来源文件。
- **VALIDATE：** `python3 -m unittest tests.test_nuwa_local_corpus.LocalCorpusInventoryTests`

### UPDATE `skills/nuwa-skill/SKILL.md`

- **IMPLEMENT：** 增加 self-local-corpus 路由、盘点和策略确认点、纯本地默认值、阅读预算、六个自我研究文件、自我模板选择、隐私规则和增量更新语义。
- **PATTERN：** 保持现有 Phase 0 至 Phase 5 公众人物流程；新增明确分支，不把共享阶段改成含糊的混合逻辑。
- **IMPORTS：** 使用相对于 `skills/nuwa-skill/` 的路径引用新流程、模板和盘点脚本。
- **GOTCHA：** “所有研究必须自包含”规则需要增加自我 profile 例外：脱敏摘要保存在 profile 内，私有 raw 来源保留在外部且只读。
- **VALIDATE：** `python3 -c 'from pathlib import Path; t=Path("skills/nuwa-skill/SKILL.md").read_text(); assert "self-local-corpus" in t and "inventory_local_corpus.py" in t and "self-profile-template.md" in t'`

### UPDATE `skills/nuwa-skill/scripts/merge_research.py`

- **IMPLEMENT：** 增加 `--mode person|self` 或自动识别；现有 `01` 至 `06` 文件保持公众人物标签，自我 profile 使用六个自我研究标签和来源类别统计。
- **PATTERN：** 调用方只传 skill 目录时，保持当前默认输出和退出行为。
- **IMPORTS：** 仅使用标准库。
- **GOTCHA：** 本地来源可能没有 URL；自我模式按唯一相对来源引用计数，不能继续把 URL 数量等同于来源数量。
- **VALIDATE：** `python3 -m unittest tests.test_nuwa_local_corpus.MergeResearchCompatibilityTests`

### UPDATE `skills/nuwa-skill/scripts/quality_check.py`

- **IMPLEMENT：** 自动识别 `profile_type: self`；接受 profile 目录或 `SKILL.md`；保留现有公众人物检查；增加自我 profile 的下游必需章节、资产索引、证据链接、profile 大小和隐私标识检查。
- **PATTERN：** 所有必需检查通过时才返回零，并输出可执行的失败原因。
- **IMPORTS：** 仅使用标准库。
- **GOTCHA：** 扫描公开层 `SKILL.md` 和 `assets/*.md` 中的凭据赋值、`wxid_`、`@chatroom` 等标识；不能仅因为私有 manifest 中出现来源目录名就误报失败。
- **VALIDATE：** `python3 -m unittest tests.test_nuwa_local_corpus.QualityCheckTests`

### CREATE `tests/test_nuwa_local_corpus.py` 和合成 Fixtures

- **IMPLEMENT：** 覆盖成功盘点、来源不存在、输出位于来源内部、symlink 跳过、完全重复检测、策略顺序优先级、二进制文件记录、超大文件排除、相对路径稳定性、公众人物模式回归、自我模式通过、缺少章节失败、隐私失败。
- **PATTERN：** 使用 `unittest`、`tempfile.TemporaryDirectory`；只有验证 CLI 退出码时使用 subprocess。
- **IMPORTS：** 仅使用 Python 标准库。
- **GOTCHA：** fixture 不得包含真实个人数据或可用凭据，只使用明显的假值。
- **VALIDATE：** `python3 -m unittest discover -s tests -p 'test_nuwa_*.py' -v`

### UPDATE `skills/baokuan-factory/SKILL.md`

- **IMPLEMENT：** Phase O 接受本地目录，将其路由到女娲 self-local-corpus 模式；新 profile 使用 `skills/<handle>-profile/`；继续前先验证 marker。
- **PATTERN：** 爆款工厂继续只做编排；所有语料分析交给女娲。
- **IMPORTS：** 无。
- **GOTCHA：** 不重命名或破坏现有 `skills/<handle>/SKILL.md` profile。
- **VALIDATE：** `rg -n 'local directory|本地目录|<handle>-profile|self-local-corpus' skills/baokuan-factory/SKILL.md`

### UPDATE 文档和触发样本

- **IMPLEMENT：** 更新 `README.md`、`docs/SOP.md` 和 `.optimize/trigger-evals.json`，说明本地目录 onboarding、双输出、隐私默认值、忽略路径和兼容性。
- **PATTERN：** 保持现有五层流水线，只在线 A 增加新的输入方式。
- **IMPORTS：** 无。
- **GOTCHA：** 不得宣称已对每个文件进行语义阅读，也不得暗示第三方资料会成为用户个人资产。
- **VALIDATE：** `python3 -m json.tool .optimize/trigger-evals.json >/dev/null && git diff --check -- README.md docs/SOP.md .optimize/trigger-evals.json`

### RUN 合成端到端验证

- **IMPLEMENT：** 创建临时混合语料；无策略盘点；应用测试策略；重新盘点；填充 fixture 自我 profile；运行质量检查；确认来源文件未发生变化。
- **PATTERN：** 使用临时目录，并比较前后 SHA-256。
- **IMPORTS：** 无。
- **GOTCHA：** 不执行 `install.sh`、`sync.sh`、外部触发评测或发布工具。
- **VALIDATE：** `python3 -m unittest discover -s tests -p 'test_nuwa_*.py' -v`

### RUN 真实知识库只读规模检查

- **IMPLEMENT：** 对 `/Volumes/WorkSSD/Dev/openclaw_mz/knowledge/raw` 使用 `--check`，记录文件数、可读取文件数、跳过格式、重复组和耗时。
- **PATTERN：** 命令不得创建 profile，也不得写入知识库。
- **IMPORTS：** 无。
- **GOTCHA：** 报告不得输出文件正文、私有标识或检测到的凭据值。
- **VALIDATE：** `python3 skills/nuwa-skill/scripts/inventory_local_corpus.py /Volumes/WorkSSD/Dev/openclaw_mz/knowledge/raw --check`

## 测试策略

### 单元测试

- 目录遍历和来源根目录验证。
- 来源策略 JSON schema、顺序匹配和未分类阻断。
- Hash 重复分组和相对路径稳定性。
- 支持格式、超大文件、隐藏文件、symlink 和二进制文件准入。
- 自我/公众人物研究汇总兼容性。
- 自我 profile 必需章节、证据、大小和隐私检查。
- 当前公众人物质量检查行为回归。

### 集成测试

- 合成混合语料完成两次盘点。
- 生成的 manifest 和 Markdown 摘要仅使用相对文件路径，不包含来源正文。
- 合格自我 profile fixture 通过，包含隐私数据的 fixture 被拒绝。
- 爆款工厂路由继续把独立公众人物蒸馏交给女娲，而不是触发完整流水线。

### 手动验证

1. 在仓库根目录准备临时目录，包含原创笔记、私有摘要、改编笔记、外部文章、两个完全重复文件和一组版本文件。
2. 不提供策略运行盘点。
3. 确认结果只包含计数和路径分类，全部文件初始为 `unclassified`。
4. 增加来源策略并重新运行。
5. 确认第一条匹配规则优先、重复分组、当前版本选择规则正确，且没有复制 raw 文件。
6. 生成或使用合成自我 profile fixture，运行质量检查。
7. 确认下游必需章节存在；包含隐私标识的产物必须以可执行错误信息失败。
8. 对真实知识目录运行 `--check`，确认没有写文件，也没有暴露正文。
9. 获得明确 quota 授权后，可选执行一次触发评测并确认：
   - “阅读这个本地知识文件夹，蒸馏成我的个人资产和 profile”按约定路由到女娲或爆款工厂 onboarding。
   - “蒸馏某个公众人物”不会路由到完整爆款工厂。

## 验证命令

```bash
git status --short --branch
git diff --check

bash -n install.sh \
  skills/baokuan-factory/scripts/sync.sh \
  skills/nuwa-skill/scripts/download_subtitles.sh

python3 -c 'import ast,pathlib; [ast.parse(p.read_text(encoding="utf-8")) for p in pathlib.Path("skills/nuwa-skill/scripts").glob("*.py")]'
python3 -m unittest discover -s tests -p 'test_nuwa_*.py' -v
python3 -m json.tool .optimize/trigger-evals.json >/dev/null

python3 skills/nuwa-skill/scripts/inventory_local_corpus.py \
  /Volumes/WorkSSD/Dev/openclaw_mz/knowledge/raw \
  --check
```

以下命令只在用户明确授权后运行，因为它会改写已安装 skill 并消耗外部模型 quota：

```bash
BKF_RUNS=1 BKF_WORKERS=1 \
  python3 .optimize/bkf_eval.py \
  .optimize/trigger-evals.json \
  .optimize/desc_v2.txt
```

## 验收标准

- [ ] 用户可以在自我蒸馏时提供绝对本地目录，且流程不复制、不修改该目录。
- [ ] 盘点工具能够以 `--check` 处理当前 13,000 多个文件的知识库，并且只报告元数据。
- [ ] 每个可读取文件都必须被已确认的来源策略分类；否则以 `unclassified` 阻止语义蒸馏。
- [ ] 完全重复文件只读取一次；版本草稿有明确的当前版本规则。
- [ ] 仅由外部资料支持的观点不会被标记为用户原创个人资产。
- [ ] 私聊衍生资产不包含姓名、聊天标识、凭据、内部地址或原始对话。
- [ ] 新自我 profile 写入 `skills/<handle>-profile/`，并保持 Git 忽略。
- [ ] 现有公众人物女娲流程和旧版 profile marker 继续有效。
- [ ] 运行时 `SKILL.md` 包含爆款工厂需要的所有章节，并符合长度目标。
- [ ] 资产库包含定位、观点、原则、工作流、证据、内容母题和可复用产品页面，且来源可追溯。
- [ ] 自我 profile 和公众人物 profile 质量检查均通过各自 fixture。
- [ ] 单元/集成测试、Python AST 解析、JSON 验证和 `git diff --check` 全部通过。
- [ ] 未经单独授权，不执行安装、同步、发布、commit、push 或消耗外部模型 quota 的操作。

## 风险与回滚

- **风险：** 私聊或凭据进入生成资产。
  - **缓解：** 私有证据默认分类、不引用原始聊天、公开层隐私扫描、来源策略检查点、标记为 public-ready 前人工确认。
  - **回滚：** 恢复旧 profile marker，停止使用新 profile；原始知识库保持不变。
- **风险：** 第三方收藏内容被误判为用户原创。
  - **缓解：** 强制来源类别、外部资料禁止直接成为个人资产、设置证据门槛。
  - **回滚：** 调整来源策略，仅重新生成 research 和 assets；不修改 raw。
- **风险：** 大型知识库处理超出上下文，形成浅层总结。
  - **缓解：** 确定性盘点、完全重复消除、明确阅读预算、按维度分批和用户检查点。
  - **回滚：** 回退到现有小规模本地语料模式，只使用人工选择的子集。
- **风险：** 新自我流程破坏公众人物流程。
  - **缓解：** 独立模板、明确模式分支、回归 fixture、兼容原 CLI。
  - **回滚：** 移除 self-local-corpus 分支和新辅助工具，保留未改动的公众人物模板与流程。
- **风险：** 个人 profile 被意外提交。
  - **缓解：** 新输出统一使用已有忽略规则覆盖的 `skills/*-profile/`，并通过 `git status --ignored` 验证。
  - **回滚：** 只取消暂存精确 profile 路径；不使用广泛 reset 或批量删除。
- **风险：** 上一轮中断流程产生的 `AGENTS.md` 被意外纳入。
  - **缓解：** 把它视为独立未跟踪文件，除非用户单独要求，否则不包含在本功能提交或补丁中。
  - **回滚：** 保持该文件不动；本功能不需要对其采取操作。

## 置信度

首次实现成功率：8/10。

文件盘点、来源归属、兼容性和隐私质量门都较明确。剩余不确定性主要来自语义质量：基于 Prompt 的自我模型仍可能过度拟合 polished drafts 或自我描述，因此证据门槛和两个人工确认检查点是必要条件。
