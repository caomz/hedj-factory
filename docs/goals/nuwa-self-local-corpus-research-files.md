---
goal_topic: nuwa-self-local-corpus-research-files
created: 2026-07-25
status: prompt-only
---

# Goal Contract — Nuwa Self-Local-Corpus（mingtian-profile）六维研究文件质量门

> 本文件是**可复制的 goal 提示词**，不是任务执行结果。除非后续用户明确授权执行 / 写入 / 提交，否则 Claude Code 应将其作为提示词读取后再开工，不直接覆盖 `skills/mingtian-profile/references/research/01–06.md`。

```markdown
Goal:
在不重跑 inventory、不动 source-policy.json、不动 source-manifest.json 的前提下，让 `skills/mingtian-profile/references/research/01–06.md` 六份研究文件同时通过五项质量门：来源合规、隐私脱敏、表达 DNA、版本序列、可追溯证据。

Intent:
仓库已具备真实语料的盘点成果（`source-manifest.json` 13,430 文件，`source-policy.json` 用户确认，`00-source-inventory.md` 已生成）；用户的真实意图不是再做一次盘点，而是把这套盘点成果固化到"六份 self 研究文件"中，使得：
- 后续 nuwa-skill 的 self-local-corpus 分支可以读到清晰的研究输入。
- 后续 baokuan-factory 可以引用这些研究文件做运行时 profile 的章节喂养。
- 隐私门 / 证据门 / class 门同时守住，不会让自述数字 / 聊天原文 / 外部作者 / 隐私标识外溢到公开面。

Strategic outcome:
- 06 篇研究文件成为"自包含、可被 quality_check.py 验证、不污染下游 baokuan-factory / 资产卡"的输入面。
- profile 公开面（`SKILL.md` + `assets/*.md`）尚未生成，但研究文件已经为它们准备好原料；后续 US-013、US-019 等里程碑可以无缝接管。
- 一旦基线确立，后续全量重跑只动 inventory 与研究文件，不影响下游 skill。

Decision standard:
- "合格" = 同时满足：相对路径、不外显 self-数字、不引用 external-only 路径、私有证据仅锚点 0 命中、自述诱人词 0 命中（除"反人设"语句外）。
- "不合格" = 出现以下任意一条 → 立即 stop：聊天原文摘录、wxid/@chatroom/RFC1918/凭据赋值、绝对路径、未在 manifest 出现的相对路径、数字结论（除非显式标"待验证"）。

Evidence standard:
- 来源证据：仅允许 `references/source-manifest.json` 列出的 relative_path。
- 私有证据：仅允许"标题 + 时间锚点 + 主题归纳"三段；禁止任何形式的原文摘录、用户名、行内凭据。
- 数字结论：仅允许 v0.1→v0.2 类的版本序列 ID；其他数字必须降级为"案例线索 / 待验证"并列入 04-§3 的"待验证案例线索"表。
- Confidence：本次基线设 high（同时被 authored + inventory 双源确认）。如有未在 manifest 出现的相对路径引入，confidence 自动降为 low，必须立即 stop。

Scope:
- 改 / 重写 `skills/mingtian-profile/references/research/01-positioning.md`、`02-core-theses.md`、`03-decisions-and-behavior.md`、`04-systems-and-cases.md`、`05-expression-dna.md`、`06-tensions-and-evolution.md` 六份。
- 允许调整 frontmatter `sources:` 列表与正文，但 sources 列表必须仍然只含 manifest 中存在的 relative_path。

Non-goals:
- 不重跑 inventory。
- 不改 `source-policy.json` / `source-manifest.json` / `00-source-inventory.md`（除非要新增 archive/）。
- 不生成 `skills/mingtian-profile/SKILL.md` 或 `assets/*.md`（那是后续里程碑）。
- 不引用 external-only 类文件（`bloggers/`、`claude/`、`openai/`、`feeds/`、`harness/`、`优秀ai文章/`、`通识内容/`、`雷哥ai知识星球内容/`、`aihot/*.{md,json}` / 但 `aihot/` 下划归 adapted，看 policy）。
- 不执行 install / sync / publish / 任何外部模型 quota。

Context to read first:
- `skills/nuwa-skill/SKILL.md`（self-local-corpus 分支）。
- `skills/nuwa-skill/references/self-distill-workflow.md`（五类来源 / 三个 Checkpoint / 阅读预算 / 输出目录）。
- `skills/nuwa-skill/references/self-profile-template.md`（self profile 章节定义与 estimated_tokens 估算）。
- `skills/mingtian-profile/references/source-policy.json`（已用户确认，五类规则）。
- `skills/mingtian-profile/references/source-manifest.json`（仅 summary / by_class 计数）。
- `skills/mingtian-profile/references/research/00-source-inventory.md`（已有盘点总结）。

Constraints:
- 隐私扫描只检查 SKILL.md 与 assets/*.md；研究文件属于 references/research/，故不强制隐私字面零命中，但禁止任何"原文摘录 / 用户名 / 群名 / 行内凭据"。
- 每份研究文件 frontmatter 必须有 `sources:` 列表；YAML 格式合规；同一相对路径只计一次。
- sources 中允许出现：authored 类（23 文件）+ private-evidence 类仅以"标题 + 时间锚点"列出 + adapted 类（33+ 文件）。
- sources 中不允许出现：external 类的相对路径。
- 自述诱人词（必读 / 神器 / 全网头部 / 颠覆 / yyds / 封神 / 必看）零命中（除"反人设"语句）。
- 绝对路径（/Volumes / /Users / ~/) 零命中（除已存在的 00-source-inventory.md）。
- 文件大小上限：单份 12KB；超过即视为"未压缩"。
- 文件必须保留 Markdown 章节 `## 与其他研究文件的关系`，且能反查到至少 2 份其它文件。

GStack route:
- Detect the matching /gstack skill from the task intent.
- Invoke the matching skill automatically when it improves execution quality.
- Prefer no-user-intervention progress for reversible, local, verifiable work.
- Pause only for destructive actions, commit/push, deploy/publish, secrets, paid quota, or unclear product decisions.
- If multiple skills match, run the earliest quality gate first, then continue toward the goal.

Execution policy:
- 先 read-only review 现存 01–06.md，记录 self-数字 / 外部路径 / 类违规项。
- 用 `grep -nE` / `wc -l` / `ls -la` 做物理抽检，**不要把任何文件字节级复制回**。
- 抽到违规项先 freeze 那一文件，再一份一份修；不要批量改。
- 每次修完再扫一次，确认无回归。
- 全部六份文件改完后，写一份"终检报告"——5 列（path / 自述数字残留 / 绝对路径 / external 来源混入 / 自述诱人词），全 0 通过即停。

Checkpoints:
- CP-A：read-only review 完成（含 5 列违规抽检结果）。
- CP-B：frontmatter sources 列表全集与 manifest 的 authored/adapted/private-evidence 三集合交、并、补齐率。
- CP-C：每文件 ≤ 12 KB；每个标题层级不超过 3 层；至少出现"## 与其他研究文件的关系"段。
- CP-D：终检报告全 0 通过。

Verification:
- 在 `scripts/ralph/progress.txt` 末尾追加一条修订日志段（格式参照已存在的 US 段落）。
- 在 `docs/goals/nuwa-self-local-corpus-research-files.md` 中追加"verified_at"与"verification_commands"。
- 验证命令：
  - `python3 -c 'import json, pathlib; m=json.loads(pathlib.Path("skills/mingtian-profile/references/source-manifest.json").read_text(encoding="utf-8")); paths={f["relative_path"] for f in m["files"]}; print(len(paths))'` 应 > 11000，且 6 份研究文件中所有 sources 条目应全部 ∈ paths。
  - `grep -nE "(wxid_|@chatroom|token=|password=|192\.168\.|10\.0\.\d|172\.16\.\d)" skills/mingtian-profile/references/research/0[1-6]-*.md` 应 0 命中（除反人设语句）。
  - `grep -nE "(/Volumes/|/Users/mingtian/|~/)" skills/mingtian-profile/references/research/0[1-6]-*.md` 应 0 命中。
  - `grep -nE "(必读|必看|神器|全网头部|全网第一|yyds|封神|绝绝子|家人们|老铁们)" skills/mingtian-profile/references/research/0[1-6]-*.md` 应 0 命中（除 §3 反人设段落）。
  - `wc -l skills/mingtian-profile/references/research/0[1-6]-*.md` 每份 ≤ 280 行。

Stop conditions:
- 任何一份文件含原文摘录 → 立即 stop。
- 任何来源被替换为 manifest 中不存在的路径 → 立即 stop。
- 任何数字结论未标"待验证/案例线索"→ 立即 stop。
- 出现 publish / commit / push / git reset / install / sync / 任何外部模型 quota → 立即 stop。
- 私有证据正文未被脱敏（出现用户名 / 群名 / wxid）→ 立即 stop。

Final report:
- 列出 6 份文件最终状态（passes / fail-reasons / size）。
- 列出 CP-A / CP-B / CP-C / CP-D 四个 checkpoint 的产出（grep 输出 / 集合计算结果）。
- 给出"research 文件 vs 后续里程碑（US-013 assets / US-014 baokuan / US-019 闭环）"的接入说明。
- 不解释过程，只列差异 / 证据 / 未关闭风险。
```

---

## 5. 收尾（按 GoalPro 规则停止）

- 当前回合按 GoalPro 规则不再继续执行。
- 文件已写到 `docs/goals/nuwa-self-local-corpus-research-files.md`，聊天窗口同步输出同一份可复制的 code block。
- 修订与执行需要你授权后才进入独立任务。
