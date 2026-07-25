# 自我蒸馏工作流参考（Self-Local-Corpus Distillation Workflow）

> 本文档是 `nuwa-skill` 中 `self-local-corpus` 分支的单一规范。任何 story 在执行自我蒸馏前都必须先阅读并遵循本文；不得从 `SKILL.md` 或其他文件重新猜测来源分类、检查点、输出边界或隐私默认。

本文锁定的事实：

1. 五类来源 class（authored / private-evidence / adapted / external / excluded）的定义与边界。
2. source policy 校验顺序、first-match 语义与非法输入处理。
3. 六个自我研究维度及其产出文件名。
4. 蒸馏每一轮的阅读预算与代表性选择规则。
5. 版本序列 current 判定规则。
6. 资产卡证据门槛。
7. 公开面（`SKILL.md` + `assets/`）与私有面（`references/`）的边界，以及隐私脱敏默认。
8. 全量重跑与增量刷新语义（本里程碑允许全量重跑）。
9. 输出目录与文件约定。

本文不重复 `SKILL.md` 中的入口路由和命令模板；如需命令用法，请回到 `SKILL.md`。

---

## 1. 三层输出与文件职责

自我蒸馏的产物必须落到**三层**，每层职责单一且互斥：

| 层 | 默认加载 | 内容性质 | 是否对外可发布 | 路径约定 |
|----|---------|---------|---------------|---------|
| 精简 `SKILL.md` | 每次 | 运行时 profile，供下游 `baokuan-factory` 注入 | 是 | `skills/<handle>-profile/SKILL.md` |
| `assets/` | 按需加载 | 个人资产卡片与索引 | 是（脱敏后） | `skills/<handle>-profile/assets/*.md` |
| `references/` | 不自动加载 | 调研材料、私有 manifest、私有研究 | 否（私有面） | `skills/<handle>-profile/references/` |

**约束**：

- `SKILL.md` 必须包含 baokuan 下游必需的全部章节，且目标体量 3,000–6,000 estimated tokens（CJK 字符数 + ceil(非 CJK 字符数 / 4)）。任何超 6,000 的运行结果被 quality gate 拒绝。
- `assets/` 是个人资产的**唯一**登记位置。公开面禁止回显凭据、聊天标识、私有 IP、原文摘录。
- `references/` 允许包含绝对 source_root 路径与逐文件 evidence 引用，但**禁止任何下游 skill 自动读取 `references/`**。它是手工审计与回溯用的私有面。
- 任何 profile 写入之前，必须先经过 `scripts/quality_check.py` 退出码 0，否则不算完成。

---

## 2. 五类来源 class（Source Classes）

`source-policy.json` 的 `rules[].class` 仅允许以下五个枚举值（小写，连字符分隔）：

| Class | 含义 | 典型来源 | 可蒸馏的字段 | 默认隐私等级 |
|-------|------|----------|--------------|--------------|
| `authored` | 用户本人原创或在用户主导下产出 | 用户笔记、用户文章草稿、用户录音文字稿、用户决策备忘录 | 全文、标题、术语、表达片段 | 公开面可用，但须保留时间戳与可追溯证据 |
| `private-evidence` | 用户自有但仅脱敏摘要可用的私有材料 | 私聊摘录、日记、内部备忘录 | **仅 summaries / analysis**，禁止引用原始聊天正文 | 必须脱敏后才可进入 `SKILL.md` / `assets/` |
| `adapted` | 用户对他人材料进行改写、二创或吸收后的产物 | 改编笔记、读后感、二创脚本 | 用户自己的改写部分，原作者观点须标注 `origin: adapted` | 公开面可用，须注明改写来源 |
| `external` | 用户未参与创作的他人材料 | 公开文章、他人著作、新闻报道、播客转写 | 仅作背景对照；不登记为个人资产 | 仅在 `references/research/` 出现，不出现在 `assets/` |
| `excluded` | 明确排除的材料 | 含敏感凭据的日志、训练语料下载、二进制缓存 | 不计入阅读预算，不出现在 manifest 的语义区 | 不出现 |

**first-match wins**：

- `source-policy.json` 中规则的顺序就是求值顺序；第一条 glob 命中的规则生效。
- 未命中任何规则的 eligible 文件保持 `policy_class: unclassified`，在 manifest 中标记 `can_distill: false`，并阻塞整个语义蒸馏阶段。
- `excluded` 命中的文件不计入阅读预算；其余四类中，`authored` 与 `private-evidence` 可进入语义蒸馏，`adapted` 仅在用户要求或资产卡引用时按需读取，`external` 首轮默认不读取。

**禁止行为**：

- CLI 不自动写 `source-policy.json`；只生成 `references/source-manifest.json` 和 `references/research/00-source-inventory.md`，并把所有 eligible 文件置为 `unclassified`。
- Nuwa 仅基于 inventory review 提出 policy 草稿；**未经用户明确确认的 policy 不进入语义阶段**。
- 不允许把 `external-only` 材料登记为个人资产（详见 §6）。

---

## 3. Source Policy 确认检查点（不可跳过）

工作流中存在四个不可绕过的确认点。任何 story 在缺确认的情况下进入下一阶段，必须立即停止并把阻塞原因写入 `notes`。

### Checkpoint A：policy 草稿确认

- 触发：`inventory` 无 policy 跑完后，Nuwa 已阅读 `references/research/00-source-inventory.md` 与 `source-manifest.json`。
- 行动：Nuwa 根据 family 摘要提出 `source-policy.json` 草稿，并逐条向用户解释「为什么这个 glob 属于这个 class」。
- 通过标准：用户逐条确认（或修改后确认）每一条规则。
- 不通过：禁止执行 `inventory --policy` 重跑，禁止进入语义蒸馏。

### Checkpoint B：manifest 通过

- 触发：使用确认后的 `source-policy.json` 重跑 `inventory`。
- 通过标准：所有 eligible 文件均被分类（`can_distill: true`），或保留 `unclassified` 但用户明确排除该文件进入语义阶段。
- 不通过：所有 `unclassified` 文件的相对路径必须出现在 inventory review 的「unmatched」段，并由用户决定补规则或显式排除。

### Checkpoint C：语义蒸馏预算确认

- 触发：在进入六维研究文件撰写前。
- 行动：Nuwa 给出本轮将读取的 authored 总字节、private-evidence 摘要文件数与 adapted 文件数。
- 通过标准：每项均不超过 §4 的预算上限；超出时必须显式分批并重新跑 Checkpoint C。
- 不通过：禁止开始 `01–06` 研究文件撰写。

### Checkpoint D：质量门

- 触发：profile 草稿（`SKILL.md` + `assets/` + `references/`）写完后，写入正式 profile 路径之前。
- 行动：运行 `python3 skills/nuwa-skill/scripts/quality_check.py <profile-dir>`，必须退出码 0。
- 不通过：禁止写入 `skills/<handle>-profile/`；禁止写入 `~/.baokuan-factory/profile`；失败原因必须出现在 `notes`。

---

## 4. 阅读预算（Reading Budget）

每个语义蒸馏轮次必须遵守下列上限。Nuwa 在 Checkpoint C 必须主动报告本轮预计消耗。

| 来源 class | 单轮上限 | 超出处理 |
|-----------|---------|----------|
| `authored` | 总量 ≤ 20 MB（20MB） | 显式分批；每批单独跑 Checkpoint C |
| `private-evidence` | 默认 ≤ 100 文件或 5 MB（5MB），先到者优先；优先读 `summaries/`、`analysis/` 目录 | 禁止引用原始聊天正文；只引用脱敏摘要或主题归纳 |
| `adapted` | ≤ 30 文件 | 必须记录用户改写部分，不可整段引用原作者 |
| `external` | 首轮 0 文件 | 仅当用于核实或对照用户个人主张时按需读取，且不进入个人资产登记 |

**重复与版本序列预算优化**：

- 精确重复（同 SHA-256）只读一次；由 inventory 的 duplicate_group 选择最小相对路径字典序的 eligible 文件作为 representative；其余标记 `semantic_read: false`。
- 版本序列（`vN` / `vN.N`）只读 current_version 文件；evolution_only 文件标记为观点演化证据，不重复计入主张计数。
- binary / 未知格式只计数不读取，绝不解析正文。

---

## 5. 六个自我研究维度

自我蒸馏使用以下六个研究维度，固定文件名：

| 序号 | 文件名 | 维度 | 主要来源 class | 必含内容 |
|------|--------|------|----------------|----------|
| 01 | `01-positioning.md` | 定位与受众 | authored + adapted | 用户定位、目标受众、与同类视角的差异 |
| 02 | `02-core-theses.md` | 核心心智模型 | authored + adapted | 反复出现的核心论点、自创术语、跨域复现 |
| 03 | `03-decisions-and-behavior.md` | 决策启发式与行为 | authored + private-evidence(摘要) | 「如果 X 则 Y」型规则、决策案例、事后反思 |
| 04 | `04-systems-and-cases.md` | 系统与案例 | authored + adapted | 工作流、复盘、可复用方法、SOP |
| 05 | `05-expression-dna.md` | 表达 DNA | authored | 句式、词汇、节奏、幽默、确定性语气 |
| 06 | `06-tensions-and-evolution.md` | 张力与演化 | authored + adapted | 内在矛盾、立场演化、近期转向 |

**合并行为**：

- `scripts/merge_research.py --mode self` 必须扫描 `references/research/01–06.md` 的 frontmatter 中的 `sources` 列表，按相对路径去重计数证据。
- 同一相对路径只计一次；URL 不是必填项。
- self 模式不修改 person 模式的现有行为；未传 `--mode` 时，`merge_research.py` 保持原有 person 默认行为不变。

---

## 6. 资产卡（Asset Card）证据门槛

`assets/*.md` 中每张资产卡必须包含以下 YAML frontmatter 字段：

```yaml
origin: authored | co-created | private-derived | adapted | external
evidence: <string, 描述支撑证据, 不回显原文摘录>
visibility: public | public-redacted | private
confidence: high | medium | low
sources:
  - <相对路径，不含绝对路径>
```

**门槛**：

- `external-only` 的想法**不得**登记为个人资产（即使 confidence=high）。
- `repeated` / `validated` 标签必须满足下列任一条件：
  - 两个或以上的 `sources` 中至少一个是 `authored` 或 `adapted` 且其他来源支持；或
  - 一个 `authored` / `adapted` 来源 + 一个真实决策或案例（出现在 `03-decisions-and-behavior.md` 或 `04-systems-and-cases.md` 中）。
- `visibility: public` 不得携带聊天标识、私有 IP、凭据赋值、原文摘录；如不可避免，仅可 `visibility: private` 并留在 `references/`。
- 资产卡字段缺失或非法时，`quality_check.py` 必须以非零退出码结束并指出缺失字段。

---

## 7. 版本序列 current 判定

- 识别文件名中的大小写不敏感版本标记：`vN` 或 `vN.N`，例如 `v0.1`、`v0.2`、`v1`。
- 同一父目录 + 相同去版本基础名 + 相同扩展名组成一个 `version_group`。
- 按数字 tuple 比较版本：`(0, 2) > (0, 1)`、`(1, 0) > (0, 9)`。
- 最高版本标记 `current_version: true`；其余 `evolution_only: true`。
- 没有版本标记的文件不被错误分组。
- inventory review 显示 `version_group` 数量与每个 group 的 current 相对路径，不输出文件正文。

---

## 8. 隐私脱敏默认（Privacy Redaction）

公开面（`SKILL.md` 与 `assets/*.md`）写入前必须经过隐私扫描。扫描规则至少覆盖：

| Rule ID | 检测对象 | 命中行为 |
|---------|---------|----------|
| `CREDENTIAL_ASSIGNMENT` | `token=...`、`password: ...`、`secret = "..."` 等凭据赋值 | 失败并指明文件+行号，不回显完整值 |
| `WECHAT_ID` | `wxid_` 前缀字符串 | 同上 |
| `CHATROOM_ID` | `@chatroom` 字样 | 同上 |
| `PRIVATE_IPV4` | RFC1918 内网 IPv4 | 同上 |

**范围限定**：

- 隐私扫描只检查 `SKILL.md` 与 `assets/*.md`，**不扫描** `references/source-manifest.json` 与 `references/research/`。
- 仅在 `references/source-manifest.json` 或 source family 中出现 `chatlog` / `微信` 字样不会误报；因为它们不带上述四种 rule id。
- 公开面命中任何一条规则 → `quality_check.py` 退出非零 → profile 不写入正式路径。

**sanitize 摘要例外**：

- 私有原文（聊天原文、日记原文）保持外部只读；本工作流明确把「sanitize 后的主题归纳 / 摘要」视为可进 profile 的合法输入。这是「研究须自包含」规则在 self 模式下的例外。

---

## 9. 全量重跑语义（Re-run Semantics）

本里程碑允许全量重跑，不实现真正的增量语义重蒸馏。

- 每次重跑 inventory 都重新生成 `source-manifest.json` 与 `references/research/00-source-inventory.md`。
- 源目录文件 SHA-256 集合在 inventory 前后必须保持一致；不允许复制或移动任何源文件到 profile 目录。
- profile 目录内不存在源文件正文副本；任何 story 如发现 profile 内出现源文件路径内容，必须立即停止并把路径写入 `notes`。
- 重跑研究文件时，旧版本必须先归档到 `references/research/archive/<timestamp>/`，不得直接覆盖。

---

## 10. 输出目录约定（固定）

```
skills/<handle>-profile/
├── SKILL.md                       # 精简运行时 profile（3,000–6,000 tokens）
├── assets/
│   ├── index.md                   # 资产索引（必须存在）
│   ├── positioning.md
│   ├── core-theses.md
│   ├── operating-principles.md
│   ├── systems-and-workflows.md
│   ├── cases-and-evidence.md
│   ├── content-motifs.md
│   └── reusable-products.md
└── references/
    ├── source-policy.json         # 用户确认后的 policy
    ├── source-manifest.json       # inventory 私有产物
    └── research/
        ├── 00-source-inventory.md
        ├── 01-positioning.md
        ├── 02-core-theses.md
        ├── 03-decisions-and-behavior.md
        ├── 04-systems-and-cases.md
        ├── 05-expression-dna.md
        └── 06-tensions-and-evolution.md
```

**写入顺序**：

1. `references/source-manifest.json` 与 `references/research/00-source-inventory.md`（首次 inventory）。
2. 用户确认 → `references/source-policy.json`（手工写入或 Nuwa 协助落盘）。
3. 二次 inventory → `can_distill: true` 后才允许写 `01–06.md`。
4. 同步生成 `assets/*.md` 八张页面与 `assets/index.md`。
5. `SKILL.md` 在最后生成；写入 `skills/<handle>-profile/` 之前必须 quality gate 退出码 0。

---

## 11. 失败与停止条件（不可妥协）

- 源目录不可读 → 该 story 阻塞并把路径错误写入 `notes`。
- 任何 `unclassified` 进入语义阶段 → 立即停止。
- 隐私扫描失败 → 立即停止；profile 不写入。
- quality_check 退出非零 → 立即停止；marker 不写入。
- 公众人物流程出现回归 → 立即停止并把回归命令与输出写入 `notes`。
- 需要新增根级依赖 / pytest / 非标准库模块 → 立即停止并把所需依赖写入 `notes`。
- 默认不执行 `install.sh`、`sync.sh`、`sau`、外部 trigger evaluator 或外部模型 quota 动作。

---

## 12. 与现有文档的关系

- 命令模板与 CLI 入口：见 `skills/nuwa-skill/SKILL.md` 的 `self-local-corpus` 分支。
- 运行时 profile 章节定义：见 `references/self-profile-template.md`。
- 库存清单 CLI 用法：见 `scripts/inventory_local_corpus.py` 的 docstring 或后续自动生成参考。
- 质量门实现：见 `scripts/quality_check.py`。
- 研究合并实现：见 `scripts/merge_research.py` 的 `--mode self`。

本文档不复制上述文件的命令或代码；只规定它们之间的契约。