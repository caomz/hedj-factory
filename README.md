# 爆款工厂 · baokuan-factory

把**别人的爆款短视频**变成**你自己口吻的成片 + 全平台文案**的一条龙。一个 Claude Code skill 集合 + 一键安装。

## 它干什么

```
线A（一次性）  女娲蒸馏「你自己」 ──► 你的表达DNA + 品味（skills/<你>/SKILL.md）
                                              │ 反复复用
线B（每条视频）video-distill 蒸馏「别人的爆款」
   取片 → 转写 → 拆解 → 翻拍角度◄注入①品味 → 成片(口播=talking-head-edit / 图文=hyperframes) → 四平台文案◄注入②口吻
```

四件事，一个入口（`baokuan-factory` orchestrator）串起来：
1. **蒸馏你自己**（nuwa-skill / 女娲）——把你的思维方式和说话风格蒸馏成一个可复用 profile。一次性。
2. **蒸馏对标爆款**（video-distill）——取片、whisper 转写、拆出"它为什么火"的骨架和手法。
3. **成片**——口播号(真人出镜)走 **talking-head-edit**(双语字幕 + 卡片素材 + 章节条 + 可换主题，内置引擎和踩过的坑)；图文/动画/混剪走 **hyperframes** 全家桶。两条底层都是 hyperframes 渲染。
4. **四平台文案**（video-distill）——抖音/视频号/小红书（中）+ X（英），用你自己的人设口吻。

## 安装（团队同事看这里）

```bash
git clone git@github.com:CLAWVARDLABS/baokuan-factory.git
cd baokuan-factory
./install.sh            # 装 skills 到 ~/.claude/skills/ + 检查依赖 + 记下仓库位置
# 要覆盖已存在的同名 skill：./install.sh --force
```

> `install.sh` 会把仓库路径写进 `~/.baokuan-factory/repo`。装在哪个目录都行，但**别装完就把这个 clone 删了**——之后"自动拉最新"靠它。

依赖（install.sh 会检查，缺了给你 brew 命令）：
`ffmpeg`、`whisper-cpp`、`yt-dlp`、`python3`、`bun`。

## 怎么用

装完，打开 Claude Code，说一句话就行（skill 会自动触发）：

- **第一次用** → "用爆款工厂帮我 onboarding"
  → 它先查依赖，再用女娲蒸馏**你自己**（你给 X/小红书/播客等链接），产出你的 profile，记到 `~/.baokuan-factory/profile`。
- **翻拍一条** → "我要翻拍这条视频 `<对标链接>`，做成我自己口吻的成片和文案"
  → 拆解 → 用你的品味定翻拍角度 → hyperframes 成片 → 四平台文案。

完整流程和"为什么这么设计"见 [`docs/SOP.md`](docs/SOP.md)。

## 包含的 skills

| skill | 来源 | 作用 |
|-------|------|------|
| `baokuan-factory` | 本仓库 | 总入口/路由，串起整条流水线，管两个 profile 注入点；每次开工先自动拉最新 |
| `nuwa-skill` | [CLAWVARDLABS/nuwa-skill](https://github.com/CLAWVARDLABS/nuwa-skill)（lean 版） | 女娲造人：蒸馏一个人→Skill |
| `video-distill` | 本仓库 | 取片/转写/拆解/翻拍角度/四平台文案 |
| `talking-head-edit` | 本仓库 | 口播成片引擎：双语字幕 + 卡片素材 + 章节条 + 可换主题（`engine/` 内置合成脚本 + 风格规范 `DESIGN.md`） |
| `hyperframes` 等 5 个 | hyperframes 项目 | HTML 视频合成 + 渲染成片（talking-head-edit 底层也用它） |

> nuwa-skill 这里是裁过的精简版（去掉了 README 的演示大图）。要完整版/更新：见上面 GitHub。
> 你自己的 profile（`skills/<你>/SKILL.md`）是你蒸馏出来的个人资产，**不要提交进这个公共仓库**，也不要覆盖别人的。

## 保持最新（团队共用一个版本）

装完之后**不用手动更新**：每次在 Claude Code 里触发爆款工厂，它第一步会自动跑 `skills/baokuan-factory/scripts/sync.sh` —— `git pull` 公共仓库，有新 commit 就 `install.sh --force` 重装。所以谁改了引擎/拆解套路/卡片样式，推到 `main`，全队下一次用就自动拿到。

- 这一步**永不阻塞**：离线 / 有本地改动 / 没装过 → 打一行提示就退，用当前版本继续。
- "已是最新"是个 1 秒空操作，不会刷一堆备份；只有真拉到更新才重装。
- 想手动同步：`cd <你的 clone> && git pull && ./install.sh --force`。
- 改了东西要给全队 → 在这个 clone 里提交并 `git push` 到 `main`（**别提交你自己的 profile `skills/<你>/`**）。

## 注意

- **视频号下载**走在线解析器（`sph.litao.workers.dev`）拿明文真链，不用 mitmproxy 抓包。细节在 video-distill 里。
- 每个同事蒸馏的是**他自己**；对标博主如果也要蒸馏，存成另一个 handle，别和"你自己"混。
