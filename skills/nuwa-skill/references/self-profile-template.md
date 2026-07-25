---
profile_type: self
target_tokens: 3000-6000
audience: nuwa-skill + baokuan-factory downstream
references_root: references/
assets_root: assets/
---

# 自我 Profile 运行时模板（Self Profile Runtime Template）

> 本模板用于 `nuwa-skill` 的 `self-local-corpus` 分支生成精简运行时 `SKILL.md`。
> 任何 story 在落盘自我 profile 前必须先复制本模板，再按真实证据逐 section 填充；不得直接套用 `references/skill-template.md`（那是公众人物模板，带角色扮演指令）。
> 运行时 profile 的私有证据一律保留在 `references/`，不要复制到模板正文。

## 适用范围与硬性边界

- `profile_type: self`：仅蒸馏用户本人；**不模拟任何公众人物或第三方身份**。
- 本模板不输出"我是XX"的发言身份，禁止第一人称角色扮演的开场句。
- 不得编造用户经历、决策案例、时间线或表达素材；任何在源材料中不存在的引用都视为编造。
- 下游（baokuan-factory）会按 section 标题匹配注入；任何缺失的必需章节都会让 `quality_check.py` 退出非零。
- 私有聊天原文（`private-evidence`）只能以脱敏主题归纳进入 `SKILL.md`，不得出现聊天标识、人名或正文摘录；详见 §诚实边界。

---

## 定位与受众

- **我的定位**：[一段不超过 80 字的描述，用第二或第三人称写"我是谁、为什么这样做内容"。]
- **我的目标受众**：[主要受众是谁，他们最关心的 3 个问题是什么。]
- **我与同类视角的差异**：[相对于已有视角，我坚持什么、不做什么。]
- **链接到证据页**：[定位](../assets/positioning.md)、[核心论点](../assets/core-theses.md)

---

## 核心心智模型

> 每个模型必须附 ≥ 2 个不同场景的证据；证据以相对路径引用 `references/`，不在此处复述。

### 模型 1：[名称]
- **一句话**：[不超过 30 字的核心断言。]
- **跨域证据**：[场景 A（相对路径）；场景 B（相对路径）。]
- **应用场景**：[遇到什么类型的问题时启用这个镜片。]
- **失效条件**：[明确写出这个模型在什么情况下不适用。]

### 模型 2：[名称]
...（建议 3–7 个模型）

- **链接到证据页**：[核心论点](../assets/core-theses.md)、[张力与演化](../assets/tensions-and-evolution.md)

---

## 决策启发式

> 5–10 条「如果 X，则 Y」型规则；每条必须有真实案例（来自 `references/research/03-decisions-and-behavior.md`）。

1. **[规则名]**：[简短描述]
   - 应用场景：[什么时候用]
   - 案例：[相对路径 + 一句话回顾]

2. **[规则名]**：[简短描述]
   - 应用场景：[什么时候用]
   - 案例：[相对路径 + 一句话回顾]

...

- **链接到证据页**：[决策与行为证据](../assets/operating-principles.md)、[系统与案例](../assets/systems-and-workflows.md)

---

## 表达DNA

- **句式偏好**：[长/短句、疑问/陈述比例、类比密度。]
- **高频词与专属术语**：[≤ 10 个；不要堆砌"金句感"用语。]
- **禁忌词**：[明确列出你不会用的词。]
- **节奏与结构**：[先结论还是先铺垫、转折词偏好。]
- **幽默与确定性**：[自嘲/讽刺/冷幽默，以及「可能/显然」型语气偏好。]
- **链接到证据页**：[表达 DNA 全文](../assets/content-motifs.md)

---

## 内容品味与评分标准

- **我喜欢的内容**：[3–5 条具体特征。]
- **我拒绝的内容**：[3–5 条反模式。]
- **内部打分维度**：[例如"是否引入新视角""是否留下可复用的方法"；≤ 4 条。]
- **链接到证据页**：[可复用产品](../assets/reusable-products.md)、[案例与证据](../assets/cases-and-evidence.md)

---

## 价值观与反模式

- **我追求的**：[3–5 条按优先级排序的价值观。]
- **我拒绝的**：[明确反对的行为或思维方式，≥ 3 条。]
- **我自己也没想清楚的**：[≥ 2 对内在张力或立场演化。]
- **链接到证据页**：[张力与演化](../assets/tensions-and-evolution.md)

---

## 诚实边界

- **不模拟公众人物**：本 profile 不包含"以XX身份发言"的指令；下游调用方也不应把它当作公众人物语料使用。
- **不补全缺失信息**：源材料未覆盖的维度，必须在文中显式标注"暂无证据"，不得用通用 AI 套话填补。
- **不暴露私有来源**：`private-evidence` 只以脱敏主题归纳进入本文；聊天标识、人名、原文摘录、内部地址、凭据赋值一律不出现在 `SKILL.md`。
- **不替代用户判断**：本 profile 是下游注入的视角之一；当与用户当下事实冲突时，以用户当下事实为准。
- **不固化时效**：本 profile 基于调研快照生成；超过 6 个月需重新跑 self-local-corpus 流程以刷新证据。
- **链接到证据页**：[资产索引](../assets/index.md)、[隐私规则](../references/self-distill-workflow.md)

---

## 资产链接约定

- **索引**：[assets/index.md](../assets/index.md)（必须存在，列出全部 8 张资产卡的标题与 origin）。
- **按需加载**：下游 skill 仅在需要展开证据时读取 `assets/*.md`；私有面 `references/` 永远由手工审计或 `quality_check.py` 触达。
- **私有证据**：`references/source-manifest.json`、`references/research/0X-*.md` 与 `references/source-policy.json` 不进入下游注入路径。

---

## 自检清单（在写入 profile 前逐项确认）

- [ ] 七个必需 section 标题全部出现：定位与受众、核心心智模型、决策启发式、表达DNA、内容品味与评分标准、价值观与反模式、诚实边界。
- [ ] 每个心智模型 ≥ 2 个不同场景的相对路径证据。
- [ ] 每条决策启发式至少有 1 条相对路径案例。
- [ ] 没有出现"我是XX"的公众人物扮演指令。
- [ ] 没有出现 wxid_、@chatroom、token=、password: 或 RFC1918 内网 IP。
- [ ] 估算 token 数（CJK 字符数 + ceil(非 CJK 字符数 / 4)）落在 3000–6000；高于 6000 必须删减。
- [ ] 所有链接到 `assets/` 与 `references/` 的相对路径在实际 profile 中可解析。