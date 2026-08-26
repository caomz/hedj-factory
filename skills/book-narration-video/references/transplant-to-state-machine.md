# 选择性移植：Cloud book-extract → 本地状态机仓库

> **目的**：把 GitHub `caomz/hedj-factory`（Cloud `main`）里已 harden 的书源提取能力，接到本地 baokuan / content-package v2 / 状态机版讲书 skill。
> **禁止**：把 Cloud `main` 整支 `git merge` 进本地状态机 `main`（会覆盖本地 SKILL、撞品牌路径、缠上未提交改动）。

Cloud 合入点：`b3f9002`（PR #2）。本文件随仓库演进；移植前再核对一次文件列表。

---

## 1. 只带走这些文件

| 路径 | 必带 | 说明 |
|------|:----:|------|
| `skills/book-narration-video/scripts/extract_book.py` | ● | 主提取器（fail-closed manifest） |
| `skills/book-narration-video/scripts/make_fixtures.py` | ● | 合成 fixture（测用） |
| `skills/book-narration-video/scripts/test_extract_book.py` | ● | 16 项 unittest |
| `skills/book-narration-video/scripts/smoke_test.sh` | ○ | 转调测试文件 |
| `skills/book-narration-video/scripts/extract_book.sh` | ○ | 薄封装 |
| `skills/book-narration-video/references/transplant-to-state-machine.md` | ○ | 本说明 |
| `skills/book-narration-video/SKILL.md` | ✕ | **不要整文件覆盖**；只摘 Phase 0–3 方法 |

### 推荐 checkout 命令（在本地状态机仓库）

```bash
git fetch https://github.com/caomz/hedj-factory.git main
# 或：git fetch <cloud-remote> main

git checkout FETCH_HEAD -- \
  skills/book-narration-video/scripts/extract_book.py \
  skills/book-narration-video/scripts/make_fixtures.py \
  skills/book-narration-video/scripts/test_extract_book.py \
  skills/book-narration-video/scripts/smoke_test.sh \
  skills/book-narration-video/scripts/extract_book.sh
```

若本地 skill 目录名不同，先 checkout 到临时路径再挪文件。

### 或用打包脚本（在 Cloud clone 里）

```bash
python3 skills/book-narration-video/scripts/pack_transplant_bundle.py \
  --out /tmp/book-extract-transplant-bundle
# 再把该目录拷到本地状态机仓库对应 scripts/ 下
```

---

## 2. 产物 → 状态机字段映射

| Cloud / 本 skill 产物 | 本地状态机接法 |
|----------------------|----------------|
| `extraction-manifest.json` → `input_sha256` / `output_sha256` | 上游 provenance（接 `source_lock`） |
| `案例库/<slug>/原文.txt` | `source_lock.py create … --source … --source-type adapted` |
| `source.txt` | **人读**；不作状态真源 |
| `extraction-manifest.json` | 机器可读真源之一；损坏时 extract_book **fail-closed** |
| `拆解.md` | → `制作准备.md` / `artifacts.brief` |
| `讲书稿.md` | → **`口播/<项目>/口播稿.md`**（统一正式稿名，勿并存） |
| `cover.jpg` | 独立参考素材（inventory 是否登记以本地为准） |
| `平台文案.md` | `artifacts.platform_copy` |
| 成片 MP4 | `artifacts.final_video` |

健康内容示例（以本地 CLI 为准）：

```bash
python3 "$SKILL_ROOT/scripts/source_lock.py" create "$PROJECT" \
  --source "$STUDIO_ROOT/案例库/<book-slug>/原文.txt" \
  --script "$PROJECT/口播稿.md" \
  --source-type adapted \
  --risk-domain health
```

---

## 3. SKILL 怎么合（方法粘贴，不覆盖）

从 Cloud `SKILL.md` **只摘**这些段落进本地状态机 SKILL（改写路径/稿名）：

1. Phase 0 版权纪律 + `extract_book` 调用（改用本地 `SKILL_ROOT`）
2. Phase 1 拆解模板
3. Phase 2 讲书角度 / profile 注入
4. Phase 3 个人元素审计 + hook；**产物文件名写成 `口播稿.md`**

保留本地：状态机、source 哈希锁定、健康门禁、真实 ASR、素材 inventory/review、发布确认。

---

## 4. 移植后验收

```bash
python3 "$SKILL_ROOT/scripts/test_extract_book.py" -v
# 期望：16/16 OK

# 烟雾（可选）
bash "$SKILL_ROOT/scripts/smoke_test.sh"
```

手工确认：

- [ ] 多来源提取后 `extraction-manifest.json` 含完整双 SHA
- [ ] 损坏 manifest 时第二次提取失败且不写新文件
- [ ] `source_lock` 能锁上 `原文.txt`
- [ ] 工作流只认 `口播稿.md`

---

## 5. 明确不要做的事

- 不要 `git merge` Cloud `main` 进本地状态机 `main`
- 不要用 Cloud `SKILL.md` 覆盖本地讲书 skill
- 不要引入第二个正式稿名 `讲书稿.md`
- 不要把 `source.txt` 当 source_lock 真源
- 不要在脚本里对用户目录 `rm -rf`；测试用 `mkdtemp` 且不主动递归清理

---

## 6. 回滚 Cloud 合入（仅 Cloud 仓库）

若需撤销 Cloud `main` 上的 PR #2 merge：

```bash
git revert -m 1 b3f90028199e166881d031274ec20643b26b71a3
# 走新 PR，勿 reset main
```
