# Project Overview

- 本仓库是面向 Claude Code 的 AI 内容生产 skill 集合，不是传统单体应用。
- 主链路：蒸馏个人 profile → 下载/转写/拆解对标视频 → 生成翻拍稿 → 制作成片 → 生成平台文案 → 可选发布。
- `skills/baokuan-factory/` 只负责端到端编排；单步需求应交给对应的专用 skill，避免总入口吞掉所有请求。
- 修改前先阅读目标目录的 `SKILL.md`；其中引用的 reference 或 engine 文档是该模块的权威规范。

# Stack And Runtime

- 内容与规范：Markdown、YAML frontmatter。
- 脚本：Bash、Python 3、Node.js ESM (`.mjs`)。
- 媒体工具：`ffmpeg`、`ffprobe`、`whisper-cli`、`yt-dlp`。
- 视频合成：Node.js >= 22、`npx hyperframes`、GSAP。
- 可选集成：gstack `/browse`、`sau`、`uv`、Patchright/Chromium。
- 仓库没有根级 `package.json`、`pyproject.toml` 或 lockfile；不要未经论证引入新的根级依赖系统。

# Common Commands

```bash
# 仓库检查
git status --short --branch
rg --files

# 安装到 ~/.claude/skills/；会修改仓库外文件，运行前先说明副作用
./install.sh
./install.sh --force

# Shell / Python / Node 静态语法检查
bash -n install.sh skills/baokuan-factory/scripts/sync.sh skills/video-distill/scripts/transcribe.sh
python3 -c 'import ast,pathlib; [ast.parse(p.read_text()) for p in pathlib.Path("skills").rglob("*.py")]'
node --check skills/hyperframes/scripts/animation-map.mjs
node --check skills/hyperframes/scripts/contrast-report.mjs

# 在具体 HyperFrames composition 目录内运行
npx hyperframes lint
npx hyperframes preview
npx hyperframes render --quality draft --output draft.mp4
```

`npx hyperframes` 可能联网拉包，渲染会消耗较长时间和计算资源。不要把 preview/render 当作仓库根级通用测试。

# Repository Structure

- `skills/*/SKILL.md`：skill 入口、触发条件、工作流与边界。
- `skills/*/references/`：按需加载的详细规范和示例。
- `skills/*/scripts/`：下载、转写、质量检查和辅助脚本。
- `skills/talking-head-edit/engine/`：口播合成引擎；`DESIGN.md` 是视觉系统单一真源。
- `docs/SOP.md`：端到端产物、衔接和排错说明。
- `docs/patches/`：第三方项目补丁，不代表补丁一定适配最新 upstream。
- `.optimize/`：`baokuan-factory` 触发评测和测试集。
- `install.sh`：依赖检测、备份、symlink 安装及仓库位置记录。

# Coding Conventions

- 保持现有文件语言和风格；技术命令、路径、配置名保持英文原样。
- 修改 `SKILL.md` 时保留合法 frontmatter，并同步检查 description、触发词、边界、产物和实际脚本是否一致。
- 总入口只编排完整链路或 onboarding。只下载、只转写、只拆解、只剪辑、只写文案等请求必须保持专用 skill 的路由精度。
- Skill 正文只放执行所需规则；长背景、样式目录和示例放入 `references/`，通过明确链接按需加载。
- Bash 脚本必须引用变量、检查输入和依赖，并返回有意义的非零退出码。普通执行脚本优先使用 `set -euo pipefail`；`sync.sh` 的“不阻塞主流程”是刻意设计，不要随意改成 fail-fast。
- Python 优先使用 `pathlib`、UTF-8、`subprocess` 参数数组和显式错误处理；不要用拼接 shell 字符串执行用户输入。
- Node 脚本保持 ESM/async 风格，清理浏览器或文件服务器资源，并通过 exit code 表达校验失败。
- `talking-head-edit/engine` 脚本通常以 composition 的 `build/` 为 CWD。不要改成依赖仓库根目录，也不要把单片数据写进 engine。
- 产物目录约定：拆解放 `案例库/<slug>/`；翻拍稿、`build/`、成片和平台文案放 `口播/<片名>/`。

# Testing And Verification

- 仓库没有统一的 `test`、`build` 或 `lint` 命令；按修改范围验证。
- Markdown/规则修改：运行 `git diff --check`，核对 frontmatter、内部路径、命令和职责边界。
- Bash 修改：对受影响脚本运行 `bash -n`，并用安全的缺参/缺文件路径验证错误信息与退出码。
- Python 修改：至少解析全部受影响文件的 AST；行为测试使用临时输入目录，确认输出路径、编码和失败处理。
- Node/HyperFrames 修改：先运行 `node --check`；在代表性 composition 中运行 `npx hyperframes lint`。视觉变更先生成 review 或 draft，不直接出 high/60fps 终版。
- 口播链路必须遵循“先裁静音，再转写”，并对裁剪前后转写做 diff，防止句尾被吃。
- 字幕必须贴实际录音；渲染前必须生成并检查 `review.html`。
- 修改 `baokuan-factory` 的触发 description 时，可使用 `.optimize/trigger-evals.json`，但评测器会改写已安装 skill、调用外部 Claude 模型并消耗 quota，只有用户明确同意后才运行。
- 最终报告必须说明修改内容、影响面、实际执行的验证、未验证项和回滚方式。

# Safety Notes

- 不提交个人 profile、cookies、账号会话、`secrets.env`、视频、音频、模型或生成日志；遵守 `.gitignore`。
- 禁止脚本批量删除文件或目录。删除前确认精确路径；需要批量删除时停止并让用户确认。
- 不自动执行 `git commit`、`push`、`pull`、merge、rebase、reset 或批量覆盖。
- `./install.sh` 会改动 `~/.claude/skills/`、移动同名真实目录到备份并创建 symlink；`--force` 还会改写指向其他位置的 symlink。运行前展示目标和回滚路径。
- `skills/baokuan-factory/scripts/sync.sh` 会执行 `git pull --ff-only`，有更新时强制重装 skills；不要把它当只读检查。
- `transcribe.sh` 在找不到本地 Whisper 模型时会下载约 1.5 GB 文件。先检查模型路径和磁盘空间，再决定是否允许下载。
- `take.py` 会联网、读取浏览器 cookie、写入 `~/.baokuan-factory/state/` 并下载媒体；先确认来源、输出目录和授权范围。
- HyperFrames 渲染、字体抓取、网页截图和触发评测可能联网或消耗大量时间/API quota，先说明成本，优先使用 lint、review 和 draft。
- `sau` 发布是对外不可逆操作。执行前逐项确认平台、账号、素材、文案、立即或定时发布；先运行相应平台的登录状态检查。
- 应用 `docs/patches/` 前核对 upstream commit，并先运行 `git apply --check`；补丁失败时不要强行套用。

# Key Files

- `README.md`：项目定位、安装和依赖概览。
- `docs/SOP.md`：完整生产流程与产物约定。
- `skills/baokuan-factory/SKILL.md`：端到端调度规则。
- `skills/video-distill/SKILL.md`：取片、转写、拆解、翻拍稿和平台文案。
- `skills/talking-head-edit/SKILL.md`：口播剪辑 SOP。
- `skills/talking-head-edit/engine/DESIGN.md`：字幕、卡片、章节和主题规范。
- `skills/hyperframes/SKILL.md`：HTML 视频 composition 规范。
- `install.sh`：安装行为和外部副作用。
