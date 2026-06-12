# 爆款工厂 · baokuan-factory

把**别人的爆款短视频**变成**你自己口吻的成片 + 全平台文案**的一条龙。一个 Claude Code skill 集合 + 一键安装。

## 它干什么

```
线A（一次性）  女娲蒸馏「你自己」 ──► 你的表达DNA + 品味（skills/<你>/SKILL.md）
                                              │ 反复复用
线B（每条视频）video-distill 蒸馏「别人的爆款」
   取片 → 转写 → 拆解 → 翻拍角度◄注入①品味 → hyperframes 成片 → 四平台文案◄注入②口吻
```

四件事，一个入口（`baokuan-factory` orchestrator）串起来：
1. **蒸馏你自己**（nuwa-skill / 女娲）——把你的思维方式和说话风格蒸馏成一个可复用 profile。一次性。
2. **蒸馏对标爆款**（video-distill）——取片、whisper 转写、拆出"它为什么火"的骨架和手法。
3. **成片**（hyperframes 全家桶）——把翻拍稿做成 HTML 视频合成并渲染。
4. **四平台文案**（video-distill）——抖音/视频号/小红书（中）+ X（英），用你自己的人设口吻。

## 安装（团队同事看这里）

```bash
git clone <这个仓库的地址> baokuan-factory
cd baokuan-factory
./install.sh            # 装 skills 到 ~/.claude/skills/ + 检查依赖
# 要覆盖已存在的同名 skill：./install.sh --force
```

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
| `baokuan-factory` | 本仓库 | 总入口/路由，串起整条流水线，管两个 profile 注入点 |
| `nuwa-skill` | [CLAWVARDLABS/nuwa-skill](https://github.com/CLAWVARDLABS/nuwa-skill)（lean 版） | 女娲造人：蒸馏一个人→Skill |
| `video-distill` | 本仓库 | 取片/转写/拆解/翻拍角度/四平台文案 |
| `hyperframes` 等 5 个 | hyperframes 项目 | HTML 视频合成 + 渲染成片 |

> nuwa-skill 这里是裁过的精简版（去掉了 README 的演示大图）。要完整版/更新：见上面 GitHub。
> 你自己的 profile（`skills/<你>/SKILL.md`）是你蒸馏出来的个人资产，**不要提交进这个公共仓库**，也不要覆盖别人的。

## 注意

- **视频号下载**走在线解析器（`sph.litao.workers.dev`）拿明文真链，不用 mitmproxy 抓包。细节在 video-distill 里。
- 每个同事蒸馏的是**他自己**；对标博主如果也要蒸馏，存成另一个 handle，别和"你自己"混。
