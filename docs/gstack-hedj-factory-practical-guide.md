# 别把 gstack 当命令大全：我拿 hedj-factory 拆出一套 AI 开发闭环

> AI 写得越来越快，但“写完代码”和“完成交付”之间，仍然隔着需求、边界、测试、审查和发布。

写这篇文章时，我在 hedj-factory 的功能分支上重新跑了一次测试。

进度日志里写着：`20 tests OK`。

但当前复跑的结果是：19 个通过，1 个失败。

失败原因不复杂。实现正在加入 `sha256`、`duplicate_group`、`semantic_read` 三个字段，测试还在坚持上一阶段的精确字段集合。代码和测试单独看都“有道理”，放在同一个时间点，却已经发生了契约漂移。

这类问题很像今天的 AI 开发：代码生成速度上去了，交付系统却没有自动跟上。

所以我重新看 gstack 时，最关注的已经不是它有多少个 slash commands，而是它能不能把一次 AI 编程会话，变成一个有输入、有边界、有验证、有出口的工程闭环。

结论先说：能，但不能照着命令表从上到下机械执行。

真正落地时，gstack 必须服从项目自己的结构、风险和发布方式。否则，它只是给“vibe coding”套了一层更复杂的外壳。

## 先说项目：hedj-factory 不是一个普通 App

[hedj-factory](https://github.com/FromTX2SJ/hedj-factory) 是一套运行在 Claude Code 里的 AI 内容生产 skills。

它的主链路是：

```text
蒸馏个人 profile
→ 下载、转写、拆解对标视频
→ 生成翻拍稿
→ 搜集素材并制作成片
→ 生成多平台文案
→ 用户确认后发布
```

这个项目同时包含 Markdown、YAML frontmatter、Bash、Python、Node.js ESM、`ffmpeg`、`whisper-cli`、`yt-dlp` 和 HyperFrames，但根目录没有统一的 `package.json`、`pyproject.toml` 或 lockfile。

这意味着，它没有一条万能的 `npm test`，也没有一套能覆盖全部模块的根级 CI 命令。

更麻烦的是，它同时存在三类完全不同的风险：

1. 代码风险：脚本可能改坏路径、覆盖产物或引入回归。
2. 隐私风险：个人 profile、聊天记录、cookies、账号会话不能进入仓库。
3. 发布风险：`sau` 会把内容真正发到抖音、小红书或视频号，这是对外不可逆操作。

在这种项目里，任何“自动修复、自动提交、自动发布”的能力，都不能只看效率，还要先看授权边界。

## 这次真实改造，为什么适合检验 gstack

当前分支正在做一件复杂但很典型的事：给 Nuwa 增加“本地个人知识资产蒸馏”。

用户可以提供一个包含 13,000 多个文件的混合知识目录。系统先做只读盘点，再区分：

- 用户原创内容；
- 私有实践证据；
- 改编资料；
- 外部参考；
- 明确排除项。

最后产出两层结果：一份精简的运行时 profile，以及一套按需加载、可追溯的个人资产库。

这不是“写一个 Python 脚本”那么简单。它至少包含 17 个 User Stories，并且有几条不能退让的约束：

- 不能复制、移动或修改原始知识库；
- 没有用户确认的 `source-policy.json`，不能开始语义蒸馏；
- 第三方收藏不能自动变成用户原创观点；
- 私聊只能做脱敏归纳，不能引用原文；
- 不能为了方便新增根级依赖系统；
- 必须保留现有公众人物蒸馏流程的兼容性；
- 真实语料只能做只读验收，自动化测试必须使用合成数据。

这正是 AI 编程最容易失控的地方：模型可以很快写出局部实现，但它未必一直记得哪些约束来自产品、哪些来自隐私、哪些来自仓库架构。

gstack 的价值，就应该在这里接受检验。

## 第一层：先把模糊需求变成可验证契约

gstack 官方把自己定义为一套从 Think、Plan、Build、Review、Test 到 Ship、Reflect 的流程，而不是彼此孤立的工具。[官方 README](https://github.com/garrytan/gstack) 当前仍把 `/office-hours`、`/spec`、`/plan-eng-review`、`/review`、`/qa`、`/ship` 放在同一条 sprint 链路里。

但在 hedj-factory 里，我不会从 `/office-hours` 开始固定走全套。

如果需求还只是“让 AI 读我的本地知识库”，先用 `/office-hours` 追问真正问题是有价值的：用户要的是模仿口吻、整理资产，还是构建一个可追溯的个人判断系统？这三个目标会导向完全不同的产品。

一旦方向已经明确，最重要的命令是 `/spec`。

因为这类功能不能只写“支持本地目录”，而要把安全边界变成验收条件：

```text
Given 一个混合知识目录
When 未提供已确认的 source policy
Then 只能生成 inventory 和 review
And 不得读取正文进入语义蒸馏
And 不得在源目录内创建任何文件
```

这一步的价值不是多写一份文档，而是让后续 Agent 无法用“功能大致完成”糊弄过去。

## 第二层：工程审查不是讨论架构，而是锁住不变量

复杂功能进入实施前，我会优先用 `/plan-eng-review`，而不是默认跑所有 review。

对当前项目，它至少应该追问五件事：

1. 文件遍历是否确定性排序，是否跟随 symlink？
2. `source-policy.json` 的 glob 是 `first match wins`，还是后规则覆盖前规则？
3. 输出目录如果位于源目录内部，是否在遍历前就拒绝？
4. 隐私扫描检查公开面，还是连私有 manifest 也一起误伤？
5. `quality_check.py` 增加 self 模式后，公众人物模式如何做回归？

这些不是代码风格问题，而是系统不变量。

此外，这次改造同时提供 CLI、Markdown contract 和 skill 路由，面向的是“其他 Agent 和开发者”。所以 `/plan-devex-review` 比 `/plan-design-review` 更相关。gstack 当前也明确区分了面向用户的设计审查、面向开发者的 DX 审查和面向架构的工程审查。[完整 skill 对照表](https://github.com/garrytan/gstack/blob/main/docs/skills.md)

这是一条很实用的选择规则：

| 变更类型 | 优先审查 |
|---|---|
| 用户界面、交互流程 | `/plan-design-review` |
| CLI、API、SDK、skill contract | `/plan-devex-review` |
| 数据流、边界、测试、兼容性 | `/plan-eng-review` |
| 多类变更同时存在 | `/autoplan`，但仍要人工裁剪 |

不是 review 越多越安全。选错 review，只会增加上下文和时间，却没有覆盖真正的风险。

## 第三层：安全模式不能替代仓库规则

gstack 提供了三层安全能力：

- `/careful`：危险命令执行前警告；
- `/freeze`：把修改限制在指定目录；
- `/guard`：两者同时开启。

这套分层设计很实用，但放进 hedj-factory，仍然需要调整。

例如，当前功能会同时修改：

```text
skills/nuwa-skill/
skills/baokuan-factory/
tests/
docs/
.optimize/
```

如果一开始就把 `/freeze` 锁在 `skills/nuwa-skill/`，测试、文档和路由样本会被挡在外面。此时更合理的做法是：先由 spec 列出允许修改的精确文件集合，日常执行开 `/careful`；只有在调查某个局部 bug 时，再用 `/freeze` 把范围收紧。

更重要的是，gstack 的安全提示不能覆盖仓库自己的 `AGENTS.md`。

这个项目明确禁止脚本批量删除文件，禁止未经授权自动 commit、push、pull、merge、rebase、reset，也禁止默认执行会消耗 API quota 的 trigger evaluator。gstack 是工作流层，`AGENTS.md` 才是项目层的执行宪法。

## 第四层：跨模型审查有用，但证据必须重新生成

gstack 的 `/review` 站在 Staff Engineer 视角检查 diff；`/codex review` 则引入 OpenAI Codex 做独立的 pass/fail 审查。官方当前还提供 `/codex challenge`，用于对抗式寻找生产失败路径。[`/codex` 官方说明](https://github.com/garrytan/gstack/blob/main/codex/SKILL.md)

这类交叉校验的真实价值，不是“两个模型都说没问题，所以肯定没问题”。

它更像两张不同焦距的镜头：Claude 可能更熟悉当前对话和实现意图，Codex 可能更容易质疑契约、边界和遗漏。两者重合的发现置信度更高，不重合的发现则提醒你继续调查。

但最终门禁仍然是可重复的项目证据。

这次复跑出现的 1 个失败就是例子：旧进度日志记录过全绿，不代表新增字段后的当前代码仍然全绿。模型审查也无法替代下面这些命令：

```bash
git diff --check
python3 -c 'import ast,pathlib; [ast.parse(p.read_text(encoding="utf-8")) for p in pathlib.Path("skills/nuwa-skill/scripts").glob("*.py")]'
python3 -m unittest discover -s tests -p 'test_nuwa_*.py' -v
python3 -m json.tool .optimize/trigger-evals.json >/dev/null
```

真正可信的状态不是“某个 Agent 说已经通过”，而是你在当前 commit、当前工作区、当前依赖环境里重新跑出的结果。

## 第五层：不是所有项目都该跑 `/qa`

gstack 的 `/qa` 很强，但它的强项是打开真实浏览器，测试应用页面，发现问题、修复并生成回归测试。官方当前描述也明确把它定位为 QA Lead 和真实浏览器测试。[官方 skills 文档](https://github.com/garrytan/gstack/blob/main/docs/skills.md)

hedj-factory 的核心却不是一个可点击的 Web App，而是 skills、CLI、媒体脚本和文件契约。

所以这里不能把 `/qa` 当成通用测试入口：

- 测 Python inventory，用 `unittest`、`tempfile` 和合成语料；
- 测 Bash，用 `bash -n` 和缺参、缺文件失败路径；
- 测 Node，用 `node --check`；
- 测 HyperFrames，在代表性 composition 里跑 `npx hyperframes lint`；
- 测视觉结果，先生成 `review.html` 或 draft，不直接渲染 high/60fps 终版；
- 测真实发布链路，先检查账号登录状态，最后一步必须人工确认。

只有当变更涉及 hedj.io、浏览器下载、网页截图或真实页面交互时，`/qa` 或 `/qa-only` 才进入主流程。

项目类型决定测试方法，不是工具菜单决定测试方法。

## 最容易踩坑的地方：代码发布和内容发布是两条线

gstack 的 `/ship` 会同步主分支、运行测试、审查覆盖率、push 并创建 PR；`/land-and-deploy` 会合并 PR、等待 CI 和部署，再验证生产环境。[`/ship` 当前实现说明](https://github.com/garrytan/gstack/blob/main/ship/SKILL.md)

对于标准 SaaS 项目，这条链路很顺。

但在 hedj-factory 里，必须把“代码发布”和“内容发布”拆开：

```text
代码发布：review → test → 人工确认 → commit/push/PR → merge

内容发布：检查账号 → 确认平台/账号/素材/文案/时间 → sau 发布
```

`/ship` 获得授权，不等于 `sau` 也获得授权。

PR 可以回滚，已经公开发布的视频和文案却可能被用户看到、转载和缓存。两个动作都叫“发布”，风险模型完全不同。

因此，我不会在这个项目里把 `/ship`、`/land-and-deploy` 和 `sau` 串成一条无人值守流水线。最后一道门必须由人来关。

## Context 能保存，但别默认让它替你提交

长功能跨多天开发时，`/context-save` 和 `/context-restore` 很有价值。它们把决策、剩余工作和失败路径变成可读的上下文，而不是只留在聊天窗口里。

不过 gstack 当前还支持 opt-in 的 continuous checkpoint mode：自动生成带 `WIP:` 前缀的本地 commit，`/ship` 前再处理这些 WIP commits。这个能力在官方 README 里有明确说明。[continuous checkpoint 说明](https://github.com/garrytan/gstack#continuous-checkpoint-mode-opt-in-local-by-default)

对于明确禁止自动 commit 的仓库，不要开启它。

更稳妥的做法是使用显式 `/context-save`，把 checkpoint 当作可阅读的项目状态，而不是默认把每次 Agent 工作都写进 Git 历史。

## 一套更适合 hedj-factory 的 gstack 顺序

如果是当前这种复杂功能，我会采用下面的流程：

```text
/office-hours（需求仍模糊时才用）
→ /spec
→ /plan-eng-review
→ /plan-devex-review（涉及 CLI / skill contract 时）
→ 分 story 实现
→ 按模块运行仓库原生验证
→ /review
→ /codex review（关键边界、隐私、安全相关）
→ /document-release
→ 人工检查 diff 与未验证项
→ 明确授权后再 /ship
```

如果只是修一个明确 bug，则缩短为：

```text
/investigate
→ 最小修复
→ 定向回归测试
→ /review
```

如果只是改 Markdown 规则，则再缩短：

```text
核对 SKILL.md 和 references
→ git diff --check
→ 检查 frontmatter、路径、触发边界和产物契约
```

流程不是越长越专业。流程的目标，是用最小成本覆盖当前变更的最高风险。

## 谁适合用，谁不适合用

gstack 适合这几类人：

- 一个人同时承担产品、开发、测试和发布职责；
- 经常让 Agent 完成跨文件、跨模块功能；
- 已经发现“代码写得快，但 review 和收尾跟不上”；
- 愿意把需求、架构和验证写成显式工件；
- 需要 Claude 与 Codex 做交叉审查。

它不太适合这些场景：

- 只改一行文案，却坚持跑完整 sprint；
- 仓库连最基本的测试命令和风险边界都没定义；
- 希望 slash command 自动替代工程判断；
- 无法接受浏览器、跨模型审查和长链路带来的时间与计算成本；
- 把自动 commit、push、merge 当成默认安全动作。

## 最终判断

gstack 最值得借鉴的，不是“一个人拥有一支虚拟团队”的角色包装，而是它把 AI 开发拆成了几个可检查的阶段：想清楚、定边界、做实现、找反例、跑证据、再发布。

但项目一旦进入真实环境，命令顺序只能是起点。

hedj-factory 给我的提醒很直接：一个没有根级测试命令、同时连接本地隐私数据、浏览器、媒体工具和外部发布平台的项目，不可能靠一条标准流水线解决所有问题。

AI 可以压低执行成本，但不能替你定义责任边界。

真正可靠的 AI 开发，不是让 Agent 做更多，而是让每一步都能回答三个问题：

```text
它为什么可以做？
它做完后如何验证？
如果做错了，在哪里停下？
```

当这三个问题有明确答案时，gstack 才不只是命令集合，而是一套能落地的交付系统。

---

> 注：gstack 更新速度较快。本文命令与能力于 2026-07-25 根据本机安装版本及 [官方仓库](https://github.com/garrytan/gstack) 核查；正式使用前请重新查看 README、`VERSION` 和对应 `SKILL.md`。本文基于 hedj-factory 当前功能分支的仓库结构与验证结果，不代表该功能已经全部完成或发布。
