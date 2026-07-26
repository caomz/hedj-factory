# PRD: Local Knowledge Self-Distillation

## Introduction / Overview

增强现有女娲（`nuwa-skill`）自我蒸馏流程，使用户可提供大型本地知识目录（例如 `/Volumes/WorkSSD/Dev/openclaw_mz/knowledge/raw`），并得到两类相互配合的产物：

1. **精简运行时 profile（`SKILL.md`）**：供 `baokuan-factory` 注入定位、判断、品味与表达 DNA。
2. **可追溯个人资产库（`assets/`）**：沉淀核心观点、做事原则、工作系统、实践证据、内容母题与可复用产品。

新模式 `self-local-corpus` 必须区分用户原创、私有证据、改编资料与外部参考；不得复制原始语料、不得泄露私聊内容、不得把第三方收藏误标为个人原创资产。现有公众人物蒸馏与小规模本地素材路径保持不变。

## Executor Assumption

- 本 PRD 准备交给 MiniMax M3、Ralph 或 Claude Code autonomous loop 按 story 顺序执行。
- 执行模型按弱模型处理：一次只执行一个 story，不得自行合并 story，不得猜测未声明的路径、schema、命令或验收口径。
- 每个 story 完成后必须运行该 story 的验证命令并读取结果；“文件已修改”“代码看起来正确”不算完成。
- 不执行 `git commit`、`push`、`pull`、merge、rebase、reset、`install.sh`、`sync.sh`、发布命令或外部模型评测，除非用户在当前执行轮明确授权。
- 如果目标文件不存在、Python 3 不可用、真实语料目录不可读、发现需要新依赖、测试无法启动、或需要用户确认的 policy 尚未确认，立即停止该 story 并报告具体阻塞证据，不得继续猜测。

## 已锁定产品决策

- 完整范围：inventory → source policy → 六维蒸馏 → `SKILL.md` + `assets/` → baokuan 接入 → 测试与文档。
- 无 policy 时，CLI 只生成 `unclassified` manifest 和 inventory review；Nuwa 基于 inventory 提出 policy 草稿，用户明确确认后才进入语义蒸馏。
- 独立“蒸馏我自己 + 本地目录”请求由 `nuwa-skill` 处理；完整爆款工厂 onboarding 请求由 `baokuan-factory` 编排并委托 Nuwa。
- 本里程碑允许全量重跑，不实现真正的增量语义重蒸馏。
- 自动化测试只使用合成语料；真实语料只运行只读 `--check`。

## Goals

- 用户可对绝对路径本地目录做自我蒸馏，且**不复制、不修改**源目录。
- 对 13,000+ 文件语料，`--check` 在当前工作机上 120 秒内完成，并只输出元数据统计。
- 每个可语义读取的文件要么被已批准 policy 分类，要么保持 `unclassified` 并阻塞语义蒸馏。
- 精确重复只读一次；版本序列有明确“当前版本”规则。
- 外部-only 材料不得标为用户原创个人资产。
- 私聊衍生资产不含姓名、聊天标识、凭据、内部地址或原文摘录。
- 新自我 profile 写入 `skills/<handle>-profile/`，被现有 `.gitignore` 的 `skills/*-profile/` 忽略。
- 运行时 `SKILL.md` 包含 baokuan 下游所需全部章节，目标体量 3,000–6,000 tokens。
- 公众人物流程与遗留 `skills/<handle>/` profile 标记继续可用。
- 标准库 `unittest`、AST 解析、JSON 校验与 `git diff --check` 全部通过。

## User Stories

### US-001: 编写自我蒸馏工作流参考文档
**描述：** 作为实施者，我需要一份权威的 `self-distill-workflow.md`，以便后续路由、盘点与蒸馏步骤有统一规范。

**Acceptance Criteria：**
- [ ] 文件存在于 `skills/nuwa-skill/references/self-distill-workflow.md`
- [ ] 文档明确包含：路由触发条件、五类来源 class、用户确认检查点、六个自我研究维度、阅读预算、版本优先级、资产评分、隐私脱敏、增量刷新语义（允许全量重跑）、输出边界
- [ ] 文档不以当前用户真实中文目录名作为硬编码规则，仅可作为示例
- [ ] `git diff --check -- skills/nuwa-skill/references/self-distill-workflow.md` 通过

### US-002: 编写自我 profile 运行时模板
**描述：** 作为实施者，我需要不包含公众人物角色扮演语义的自我 profile 模板，以便生成可被 baokuan 注入的 `SKILL.md`。

**Acceptance Criteria：**
- [ ] 文件存在于 `skills/nuwa-skill/references/self-profile-template.md`
- [ ] 模板包含以下章节标题（可用 `rg` 命中）：`定位与受众`、`核心心智模型`、`决策启发式`、`表达DNA`、`内容品味与评分标准`、`价值观与反模式`、`诚实边界`
- [ ] 模板含指向 `assets/` 更深页面的链接约定
- [ ] 模板明确“不得编造用户经历”规则，且无公众人物角色扮演指令
- [ ] 模板说明运行时目标体量 3,000–6,000 tokens，原始证据放 `references/`
- [ ] `git diff --check` 对该文件通过

### US-003: 实现 inventory CLI 骨架与路径校验
**描述：** 作为用户，我想用命令盘点本地知识目录，以便在不读取正文的前提下得到确定性清单。

**Acceptance Criteria：**
- [ ] 存在可执行脚本 `skills/nuwa-skill/scripts/inventory_local_corpus.py`
- [ ] 支持参数：源根路径、`--profile-dir`、可选 `--policy`、可选 `--max-file-bytes`（默认 2000000）、`--check`
- [ ] 源根缺失、非目录、或 `--profile-dir` 位于源树内部时，打印可执行错误并以非零退出码结束
- [ ] `--check` 模式不写入任何文件
- [ ] 仅使用 Python 标准库
- [ ] `python3 -c 'import ast; ast.parse(open("skills/nuwa-skill/scripts/inventory_local_corpus.py", encoding="utf-8").read())'` 通过

### US-004: 实现确定性遍历与文件资格判定
**描述：** 作为用户，我希望盘点结果对同一目录稳定可复现，以便后续 policy 与阅读预算可依赖。

**Acceptance Criteria：**
- [ ] 默认跳过 symlink（不跟随）
- [ ] 盘点所有非隐藏常规文件；仅对支持的文本扩展名标记为语义合格：`.md` `.markdown` `.txt` `.json` `.jsonl` `.html` `.htm` `.yaml` `.yml` `.csv`
- [ ] 不支持/二进制格式只计数量，不解析 SQLite/图片/音视频/未知格式正文
- [ ] 每条基础记录包含：相对路径、扩展名、字节大小、修改时间、顶层 family、eligibility、policy class、exclusion reason；SHA-256 与 duplicate group 由 US-007 增加
- [ ] 超过 `--max-file-bytes` 的文件标记为不合格并给出 exclusion reason
- [ ] 盘点过程不读取文件正文做语义分析（仅元数据与哈希）
- [ ] 对应 `unittest` 至少覆盖：成功遍历、symlink 跳过、超大文件排除、不支持格式只计数

### US-005: 实现无 policy 盘点输出
**描述：** 作为用户，我希望首次盘点后得到未分类 manifest 和 inventory review，以便女娲在不读取正文的前提下提出来源归属建议。

**Acceptance Criteria：**
- [ ] 无 `--policy` 时，所有文件 class 为 `unclassified`，并生成 inventory 审阅材料
- [ ] 非 `--check` 且提供 `--profile-dir` 时，写入：
  - `references/source-manifest.json`
  - `references/research/00-source-inventory.md`
- [ ] CLI 不自动猜测来源归属，也不在无 policy 时生成已生效的 `source-policy.json`
- [ ] `SKILL.md` 与可发布 `assets/` 不得写入源目录绝对路径；manifest 可保留绝对 root（因 profile 目录私有且被 ignore）
- [ ] 绝不把源文件复制或移动到 profile 目录
- [ ] 测试：无 policy 盘点后，所有条目为 `unclassified`，两个约定输出文件存在且可读取，源文件 SHA-256 前后不变

### US-006: 应用已确认 policy（有序 glob，先匹配先生效）
**描述：** 作为用户，我想在确认 policy 后重新盘点，以便按归属类过滤可蒸馏材料。

**Acceptance Criteria：**
- [ ] 支持 `--policy /path/to/source-policy.json`
- [ ] 规则按文件顺序求值，first match wins
- [ ] 合法 class 仅：`authored` | `private-evidence` | `adapted` | `external` | `excluded`
- [ ] 未匹配路径保持 `unclassified`，并在摘要中报告 unmatched 数量/列表摘要
- [ ] 存在任何 `unclassified` 时，工作流文档与 skill 路由明确：**阻塞语义蒸馏**，直到用户排除或补规则
- [ ] 测试覆盖：有序优先级、未匹配阻塞语义、非法 class 非零退出

### US-007: 重复文件与版本序列规则
**描述：** 作为用户，我希望精确重复只处理一次，版本草稿有明确当前版，以便控制阅读预算。

**Acceptance Criteria：**
- [ ] 相同 SHA-256 的文件归入同一 duplicate group；语义读取时只选一个代表
- [ ] 对文件名中的 `v0.1` / `v0.2` / `v0.3` 这类版本，选择最高版本为 current；旧版仅可作为演化证据保留指引
- [ ] inventory Markdown 摘要可见 duplicate 统计与 version current 提示
- [ ] 对应 unittest 覆盖精确重复与版本序列

### US-008: 扩展 `merge_research.py` 支持 self 模式
**描述：** 作为实施者，我需要合并自我研究笔记时使用 self 标签，同时不破坏现有公众人物 CLI。

**Acceptance Criteria：**
- [ ] 增加 `--mode person|self` 或等价自动检测；仅传 skill 目录时默认行为与现网一致
- [ ] person 模式仍使用现有 `01`–`06` 公众人物标签
- [ ] self 模式使用六个自我维度标签，并统计来源 class 计数
- [ ] self 模式以唯一相对源路径计数证据，不要求 URL
- [ ] `python3 -m unittest` 中 `MergeResearchCompatibilityTests`（或等价）通过

### US-009: 扩展 `quality_check.py` 支持自我 profile
**描述：** 作为用户，我希望自我 profile 在写入 baokuan 标记前通过专用质量与隐私门，以免下游注入不合格或泄密内容。

**Acceptance Criteria：**
- [ ] 自动识别 `profile_type: self`（或约定 frontmatter/路径规则），并接受 profile 目录或 `SKILL.md` 路径
- [ ] 保留现有公众人物检查，回归 fixture 仍通过
- [ ] self 检查至少包含：下游必需章节、`assets/index.md` 存在、证据链接、体量预算、隐私扫描
- [ ] 隐私扫描覆盖公开面的 `SKILL.md` 与 `assets/*.md`：凭据赋值、`wxid_`、`@chatroom` 等；不得仅因私有 manifest 中出现源 family 名而失败
- [ ] 全部通过时退出码 0；失败时打印可执行错误且非零退出
- [ ] 对应 `QualityCheckTests` 覆盖：self 通过、缺章节失败、隐私污染失败、person 回归

### US-010: 将 `self-local-corpus` 分支写入女娲 `SKILL.md`
**描述：** 作为用户，当我要求蒸馏自己并提供本地目录时，女娲应走新分支而非复制式小素材流程。

**Acceptance Criteria：**
- [ ] `skills/nuwa-skill/SKILL.md` 含明确路由分支名 `self-local-corpus`
- [ ] 触发条件：用户蒸馏自己 **且** 提供目录
- [ ] 独立自我蒸馏请求由 Nuwa 处理；只有用户要求完整 onboarding 或后续爆款工厂链路时才由 baokuan 总入口编排
- [ ] 默认纯本地分析；除非用户明确要求，不浏览网页做外部佐证
- [ ] 流程要求：先 inventory → Nuwa 根据目录 family 提出 `source-policy.json` 草稿 → 用户明确确认 → 使用 `--policy` 重跑 → 再语义蒸馏；不复制/移动源文件
- [ ] 写入阅读预算：authored ≤20MB/pass（更大则显式分批）；private-evidence 优先摘要、默认 ≤100 文件或 5MB/pass 且不引用原文聊天；adapted ≤30 文件/pass；external 首轮排除，仅在核实/对照个人主张时按需读取
- [ ] 选择 `self-profile-template.md`，并引用 `self-distill-workflow.md` 与 `inventory_local_corpus.py`
- [ ] 文档声明：sanitize 摘要可进 profile，私有原文源保持外部只读（对“研究须自包含”规则的自我例外）
- [ ] 增量刷新：文档说明语义；本里程碑允许全量重跑
- [ ] 校验：`python3 -c 'from pathlib import Path; t=Path("skills/nuwa-skill/SKILL.md").read_text(); assert "self-local-corpus" in t and "inventory_local_corpus.py" in t and "self-profile-template.md" in t'`

### US-011: 定义资产卡契约与 `assets/` 页面结构
**描述：** 作为创作者，我希望个人资产有统一卡片字段与页面集合，以便按需加载且可追溯。

**Acceptance Criteria：**
- [ ] 工作流或模板文档规定每张资产卡必含 YAML 字段：`origin`、`evidence`、`visibility`、`confidence`、`sources`（相对路径列表）
- [ ] `origin` 枚举：`authored | co-created | private-derived | adapted | external`
- [ ] 规定 external-only 想法不得作为个人资产，仅可作对照/背景
- [ ] 规定 `repeated`/`validated` 需：两个 owned 源，或一个 owned 源 + 真实决策/案例
- [ ] 目录约定存在：`assets/index.md`、`positioning.md`、`core-theses.md`、`operating-principles.md`、`systems-and-workflows.md`、`cases-and-evidence.md`、`content-motifs.md`、`reusable-products.md`
- [ ] 合成 fixture profile 可按该结构被 quality check 接受

### US-012: 新增合成测试语料与 unittest 套件
**描述：** 作为实施者，我需要不含真实隐私的合成语料与 fixture，以便自动化验证盘点与质量门。

**Acceptance Criteria：**
- [ ] 存在 `tests/test_nuwa_local_corpus.py` 与 `tests/fixtures/nuwa-self-distill/`
- [ ] fixture 不含真实个人信息或工作密钥；敏感样例必须明显伪造
- [ ] 覆盖：成功 inventory、缺根、输出在源内拒绝、symlink 跳过、精确重复、有序 policy、不支持二进制、超大文件、相对路径稳定、person 回归、self 通过、缺章节失败、隐私失败
- [ ] `python3 -m unittest discover -s tests -p 'test_nuwa_*.py' -v` 全部通过
- [ ] 仅标准库（`unittest` / `tempfile` / 必要时 `subprocess`），不引入 pytest 或根级依赖清单

### US-013: 更新 baokuan Phase O 接受本地目录与 `-profile` 约定
**描述：** 作为用户，我希望在爆款工厂 onboarding 时直接给本地知识文件夹，并写入被 ignore 的新 profile 路径。

**Acceptance Criteria：**
- [ ] `skills/baokuan-factory/SKILL.md` Phase O 接受社交链接/文件 **或** 本地目录
- [ ] 本地目录路径委托女娲 `self-local-corpus`，baokuan 自身不做语料分析
- [ ] 新自我 profile 写入 `skills/<handle>-profile/SKILL.md`，并写入 `~/.baokuan-factory/profile`
- [ ] 已有合法遗留 `skills/<handle>/SKILL.md` 标记继续接受，不自动迁移/重命名
- [ ] `rg -n 'local directory|本地目录|<handle>-profile|self-local-corpus' skills/baokuan-factory/SKILL.md` 至少命中约定文案
- [ ] `git diff --check` 对该文件通过

### US-014: 更新 README、SOP 与触发评测样本
**描述：** 作为维护者，我需要文档与路由样本反映目录型自我蒸馏，以免 onboarding 与独立蒸馏路由混淆。

**Acceptance Criteria：**
- [ ] `README.md` 与 `docs/SOP.md` 说明：本地文件夹自我蒸馏、双输出、隐私默认、`skills/*-profile/` ignore、遗留兼容
- [ ] 文档不暗示“每个文件都会被语义阅读”，也不暗示第三方归档会变成个人资产
- [ ] `.optimize/trigger-evals.json` 增加至少一条 baokuan 正向：用户明确要求 onboarding，并提供本地知识文件夹
- [ ] 增加至少两条 baokuan 负向：仅蒸馏自己 + 本地目录、蒸馏公众人物；两者都不走完整 baokuan 管线
- [ ] `python3 -m json.tool .optimize/trigger-evals.json >/dev/null` 通过
- [ ] `git diff --check -- README.md docs/SOP.md .optimize/trigger-evals.json` 通过
- [ ] 不默认运行会改写已安装 skill、消耗外部模型 quota 的 trigger evaluator（除非用户另批）

### US-015: 合成语料端到端验证（无真实隐私）
**描述：** 作为实施者，我需要在临时混合语料上跑通盘点→policy→质量门，并证明源文件未被改动。

**Acceptance Criteria：**
- [ ] 使用临时目录构造：原创笔记、私有摘要、改编笔记、外部文章、两个精确重复、一组版本序列
- [ ] 先无 policy 盘点：可见计数与 path family，初始全部 `unclassified`
- [ ] 写入测试 policy 后重跑：first-match、duplicate group、current-version 指引符合预期
- [ ] 前后 SHA-256 inventory 证明源树零写入/零复制到 profile 的原文
- [ ] 使用合成 self profile 跑 quality check：通过；隐私污染 fixture：失败且信息可执行
- [ ] 不运行 `install.sh`、`sync.sh`、外部 trigger evaluator、发布工具
- [ ] `python3 -m unittest discover -s tests -p 'test_nuwa_*.py' -v` 通过

### US-016: 真实语料只读规模验收
**描述：** 作为用户，我需要确认真实 13,000+ 文件目录可被只读盘点，以便该功能在真实规模下可用。

**Acceptance Criteria：**
- [ ] 在仓库根执行：
  ```bash
  python3 skills/nuwa-skill/scripts/inventory_local_corpus.py \
    /Volumes/WorkSSD/Dev/openclaw_mz/knowledge/raw \
    --check
  ```
- [ ] 命令退出码为 0
- [ ] 输出包含文件总数、语义合格数、跳过格式统计、重复统计、耗时（或等价可观测字段）
- [ ] 命令不创建 profile，不向知识库写入任何文件
- [ ] 报告/日志不打印文件正文、私有标识符或检测到的凭据值

### US-017: 闭环集成验证（目录 → profile 契约 → baokuan 标记约定）
**描述：** 作为用户，我希望从“给本地目录”到“下游可注入的自我 profile 约定”整条链路在仓库内可验证，而不是只验证散落脚本。

**Acceptance Criteria：**
- [ ] 合成语料走完：inventory（无 policy）→ 建议/测试 policy → inventory（有 policy）→ 生成或装填合成 `skills/<handle>-profile/` 结构（`SKILL.md` + `assets/` + `references/`）
- [ ] `quality_check.py` 对合成 self profile 退出码 0
- [ ] `SKILL.md` 含 baokuan 所需章节，并链接到 `assets/` 页面
- [ ] `assets/` 中至少一张资产卡含完整 provenance 字段且 `sources` 为相对路径
- [ ] 文档/skill 约定：新 profile 路径形态为 `skills/<handle>-profile/SKILL.md`，可写入 `~/.baokuan-factory/profile`（本 story 可用文档断言 + 路径存在性检查；不强制改写用户本机真实 marker）
- [ ] 公众人物 quality fixture 仍通过（无回归）
- [ ] 真实语料 US-016 `--check` 已通过
- [ ] 仓库验证命令集合通过：
  ```bash
  git diff --check
  python3 -c 'import ast,pathlib; [ast.parse(p.read_text(encoding="utf-8")) for p in pathlib.Path("skills/nuwa-skill/scripts").glob("*.py")]'
  python3 -m unittest discover -s tests -p 'test_nuwa_*.py' -v
  python3 -m json.tool .optimize/trigger-evals.json >/dev/null
  ```

## Functional Requirements

- FR-1: 系统必须提供 `inventory_local_corpus.py`，对本地目录做确定性元数据盘点，默认不跟随 symlink，不复制源文件。
- FR-2: 无 policy 时所有文件必须为 `unclassified`，CLI 仅生成 manifest 与 inventory review；Nuwa 负责提出 policy 草稿，用户确认后才生效。
- FR-3: 有 policy 时必须按规则顺序 first-match 分类；`unclassified` 必须阻塞语义蒸馏。
- FR-4: 支持的语义格式仅限文档列出的文本扩展名；其余只计数不解析。
- FR-5: 必须按 SHA-256 去重，并对 `vN` 文件名版本选出 current。
- FR-6: 女娲必须新增独立路由分支 `self-local-corpus`，默认纯本地、先盘点后蒸馏、使用自我模板。
- FR-7: 必须执行文档化的阅读预算与隐私默认（私有证据不引用原始聊天）。
- FR-8: 输出目录必须为 `skills/<handle>-profile/`，包含精简 `SKILL.md`、`assets/`、`references/` 研究材料。
- FR-9: 资产卡必须带 provenance/evidence/visibility/confidence/sources；external-only 不得成为个人资产。
- FR-10: `merge_research.py` 必须兼容 person 默认行为，并支持 self 标签与相对源计数。
- FR-11: `quality_check.py` 必须自动区分 self/person，并对 self 做下游章节、体量与公开面隐私扫描。
- FR-12: `baokuan-factory` Phase O 必须接受本地目录并委托女娲；新 profile 用 `-profile` 后缀；遗留 marker 继续有效。
- FR-13: README/SOP/trigger-evals 必须更新目录型自我蒸馏与路由正负样本。
- FR-14: 必须提供标准库 unittest 与合成 fixture；真实语料 `--check` 必须作为正式验收。
- FR-15: 本功能不得引入新的包管理器、根级 lockfile，或默认执行 install/sync/publish/外部 trigger eval。

## Non-Goals

- 不自动迁移已有 `skills/<handle>/` 自我 profile 到 `-profile`。
- 不实现真正的增量只重蒸馏变更文件（本里程碑文档化语义即可，允许全量重跑）。
- 不把原始知识库复制进 skill，也不解析 SQLite/媒体等非 v1 文本格式。
- 不把第三方收藏自动标为用户原创 IP。
- 不默认联网佐证自我主张（除非用户明确要求）。
- 不修改或强化提交 `AGENTS.md` 等与本功能无关的未跟踪文件。
- 不运行 `install.sh`、`sync.sh`、`sau` 发布、或消耗外部模型 quota 的 trigger evaluator（除非用户另批）。
- 不引入 pytest / 根级 `pyproject.toml` / 新运行时依赖。

## Design Considerations

- 双层输出：默认只加载精简 `SKILL.md`；深证据按需读 `assets/`。
- 来源 class 对用户可见、可编辑；建议 policy 必须经确认再进入语义阶段。
- 公开面（`SKILL.md` + `assets/`）与私有面（`references/source-manifest.json` 等）严格分离。
- 中文章节名需与 baokuan 现有注入点对齐（心智模型、表达 DNA、品味、反模式等）。

## Technical Considerations

- 仅 Python 3 标准库：`pathlib`、`argparse`、`hashlib`、`json`、`fnmatch` 等。
- 错误处理：简洁可执行错误 + 非零退出码。
- `SKILL.md` token 估算使用零依赖近似：`CJK 字符数 + ceil(非 CJK 字符数 / 4)`；估算值高于 6,000 视为失败，低于 3,000 只警告不阻塞。
- `install.sh` 会 symlink 每个 `skills/*/`；个人 profile 仍可加载，但必须保持 gitignore。
- 公众人物 `skill-template.md` 与现有 Phase 0–5 不得被自我分支改坏。
- 真实语料路径仅用于只读 `--check`；自动化测试只用合成语料。
- `AGENTS.md` 若仍为未跟踪文件，不得在本功能提交中顺带纳入。

## Success Metrics

- 真实语料 `--check` 在当前工作机上 120 秒内成功返回统计且零写入。
- 合成 E2E：源 SHA 不变 + quality gate 对 clean/dirty fixture 行为正确。
- 新 profile 路径匹配 `skills/*-profile/`，`git status --ignored` 可见被忽略。
- 运行时 `SKILL.md` 落在 3,000–6,000 tokens 目标带，并含全部下游必需章节。
- 公众人物 quality/merge 回归零失败。
- 相关静态检查与 `unittest` 全绿。

## Open Questions

- 当前无阻塞性产品问题。
- v1 不维护硬编码的“目录名 → class”全局映射；Nuwa 根据当前 inventory 提出草稿，用户逐项确认。
- policy 确认采用对话内摘要 + 用户明确确认 + 写入 JSON 后重跑 CLI，不开发独立 UI。
- CI 只跑合成语料。US-016 必须在能读取指定真实目录的当前工作机上人工签收；路径不可读时，该 story 停止并记录 blocked，功能不得宣称全部完成。

## 执行顺序、完成条件与停止条件

- 下一步从 `US-001` 开始，严格按 `US-001` → `US-017` 顺序执行。
- 功能完成条件：`US-001` 至 `US-017` 的 Acceptance Criteria 全部有可读回证据，US-015 合成闭环通过，US-016 真实目录只读检查通过，US-017 全量验证命令通过。
- 必须停止的条件：来源目录不可读、存在未确认 `unclassified` 来源却准备进入语义阶段、隐私扫描失败、公众人物回归失败、需要新增根级依赖、或需要执行未获授权的安装/同步/发布/Git/API quota 动作。
- 回滚原则：只回退本功能精确文件；不修改 `raw/`，不删除个人知识目录，不使用 `git reset --hard` 或批量删除命令。

## 检查清单（PRD 作者自检）

- [x] 源计划已经决策完整，因此按 skill 规则跳过不必要的澄清问题；未虚构用户答案
- [x] 已写明 Executor Assumption，按 MiniMax M3 / Ralph / Claude Code 弱模型执行
- [x] User Stories 按依赖顺序排列，ID 稳定
- [x] Acceptance Criteria 可通过文件、命令、JSON 或退出码读取证据
- [x] 解析、写入、批量盘点和隐私检查均包含失败路径或停止条件
- [x] 跨 story 功能含最终集成验证（US-017）
- [x] Functional Requirements 已编号且无歧义
- [x] Non-Goals 与授权边界清晰
- [x] 已说明下一 story、完成条件、停止条件和回滚原则
- [x] 保存至 `tasks/prd-local-knowledge-self-distillation.md`
