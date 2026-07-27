<div align="center">

<img src="docs/assets/hedj-logo.png" width="140" alt="hedj logo">

# hedj-factory

**Your personal AI content machine.**

人负责创意,机器负责执行。把对标爆款,变成你自己口吻的成片,然后自动发布。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/FromTX2SJ/hedj-factory?style=social)](https://github.com/FromTX2SJ/hedj-factory/stargazers)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://github.com/FromTX2SJ/hedj-factory/pulls)
[![Cloud](https://img.shields.io/badge/%E2%98%81%EF%B8%8F%20Cloud-hedj.io-EC7211)](https://hedj.io)

[**☁️ 云端版 hedj.io**](https://hedj.io) · [快速开始](#-快速开始) · [五层流水线](#-五层流水线) · [完整 SOP](docs/SOP.md)

</div>

---

## ✨ 它是什么

一套跑在 Claude Code 里的 **内容机器**:你只出现两次(定方向、出观点),其余全部由 agent 执行。

```
01 蒸馏自己(一次性)  女娲读你全部过往表达 ──► 你的观点 + 语气 + 口头禅 → profile
02 寻找爆款          全网找被验证的对标 → 下载 → whisper 转写 → 拆解它为什么火
03 共写内容稿        它出结构,你出观点 → 个人元素审计 → 换成你的观点与口吻 → 黄金5秒 hook
04 素材 / 成片       自动搜素材、截图、剪辑 → hyperframes 渲染(口播走 talking-head-edit)
05 Headless 发布     一键发抖音 / 小红书 / 视频号(发前显式确认)
```

一句话就能开工(skill 自动触发):

- **第一次用** → 「帮我 onboarding」→ 查依赖 + 女娲蒸馏**你自己**,产出你的 profile
- **做一条** → 「我要翻拍这条视频 `<对标链接>`,做成我自己口吻的成片和文案」
- **发出去** → 「把这条成片发到抖音/小红书/视频号」

完整流程和「为什么这么设计」见 [`docs/SOP.md`](docs/SOP.md)。

## ☁️ 云端版:hedj.io

不想折腾代码?[**hedj.io**](https://hedj.io) 是这台机器的云端版:

- **今日定位** — 每天告诉你,今天该说什么、以什么被记住
- **Hedgie 影响力伙伴** — 记得你的工作、定位和口吻,先判断,再生成
- **内容起草** — 选个热点,草稿自己写出来,一次发好几个平台
- **Video Factory** — 翻拍爆款:benchmark → script → record → cut
- **24/7 云端运行** — 渲染、排期、自动发布都在云上,你关了电脑它还在干活

目前 invite-only,在 [hedj.io](https://hedj.io) 加入 waitlist。

## 🚀 快速开始

```bash
git clone git@github.com:FromTX2SJ/hedj-factory.git
cd hedj-factory
./install.sh            # 装 skills 到 ~/.claude/skills/ + 检查依赖 + 记下仓库位置
# 要覆盖已存在的同名 skill:./install.sh --force
```

> `install.sh` 会把仓库路径写进 `~/.hedj-factory/repo`。装在哪个目录都行,但**别装完就把这个 clone 删了**,之后「自动拉最新」靠它。

**依赖**(install.sh 会检查,缺了给你 brew 命令):`ffmpeg`、`whisper-cpp`、`yt-dlp`、`python3`、`bun`。

**软依赖 1:gstack `/browse`**(视频号取片 + 成片抓素材截图靠它,是成片质感的命根子)。公开仓库([garrytan/gstack](https://github.com/garrytan/gstack),MIT),一行装(需 Bun v1.0+ 和 Git):

```bash
git clone --single-branch --depth 1 https://github.com/garrytan/gstack.git ~/.claude/skills/gstack && cd ~/.claude/skills/gstack && ./setup
```

装完重开一轮 Claude Code 生效,升级用 `/gstack-upgrade`。没有它也能跑:视频号改备选下载、截图手动塞进 `build/news/`。

**软依赖 2:social-auto-upload(`sau` CLI)** — 只有最后一步「一键发布」才用,不装不影响成片+文案。公开仓库([dreammis/social-auto-upload](https://github.com/dreammis/social-auto-upload),MIT,需 `uv` + `python3.10~3.12`):

```bash
git clone https://github.com/dreammis/social-auto-upload.git && cd social-auto-upload && uv venv --python 3.12 && uv pip install -e . && PLAYWRIGHT_DOWNLOAD_HOST="https://npmmirror.com/mirrors/playwright" .venv/bin/patchright install chromium && cp conf.example.py conf.py
```

装完各平台 `sau <平台> login --account <你> --headed` 扫码登录。首次登录若报错是 upstream 已知 bug,打本仓库带的补丁:`git apply <你的 clone>/docs/patches/social-auto-upload-login-fixes.patch`(细节见 [`docs/SOP.md`](docs/SOP.md) 排错「发布」)。

## 🧩 五层流水线

| # | 层 | skill | 你出现吗 |
|---|-----|-------|:---:|
| 01 | 蒸馏自己 → profile | [nuwa-skill](https://github.com/CLAWVARDLABS/nuwa-skill)(女娲) | ● 一次性 |
| 02 | 寻找爆款(取片/转写/拆解) | `video-distill` | |
| 03 | 共写内容稿(它出结构,你出观点) | `video-distill` + 你的 profile | ● 每条 |
| 04 | 素材 / B-roll / 成片 | `talking-head-edit` / `hyperframes` | |
| 05 | Headless 发布(抖音/小红书/视频号) | [social-auto-upload](https://github.com/dreammis/social-auto-upload) | 发前确认 |

> 你自己的 profile(`skills/<你>/SKILL.md`)是你蒸馏出来的个人资产,**不要提交进公共仓库**。
> 视频号下载走在线解析器(`sph.litao.workers.dev`)拿明文真链,不用 mitmproxy 抓包,细节在 video-distill 里。

## 🔄 保持最新

装完**不用手动更新**:每次触发,第一步自动跑 `scripts/sync.sh`,`git pull` 有新 commit 就 `install.sh --force` 重装。多人共用一个 `main`,谁改了引擎/拆解套路/卡片样式,推上去,所有人下一次用就自动拿到。

- 这一步**永不阻塞**:离线 / 有本地改动 / 没装过 → 打一行提示就退,用当前版本继续
- 手动同步:`cd <你的 clone> && git pull && ./install.sh --force`

## ⭐ Star History

[![Star History Chart](https://api.star-history.com/svg?repos=FromTX2SJ/hedj-factory&type=Date&v=2)](https://www.star-history.com/?repos=FromTX2SJ%2Fhedj-factory&type=date&legend=top-left)

## 🐾 Find me(全网同名)

[![X](https://img.shields.io/badge/X-%400xKaiwen-000000?logo=x&logoColor=white)](https://x.com/0xKaiwen)
[![小红书](https://img.shields.io/badge/%E5%B0%8F%E7%BA%A2%E4%B9%A6-0xKaiwen-FF2442?logo=xiaohongshu&logoColor=white)](https://www.xiaohongshu.com/user/profile/652d3908000000002a01908e)
[![抖音](https://img.shields.io/badge/%E6%8A%96%E9%9F%B3-0xKaiwen-000000?logo=tiktok&logoColor=white)](https://www.douyin.com/search/1926695496)
[![视频号](https://img.shields.io/badge/%E5%BE%AE%E4%BF%A1%E8%A7%86%E9%A2%91%E5%8F%B7-0xKaiwen-07C160?logo=wechat&logoColor=white)](#)

## 📄 License

[MIT](LICENSE) © 2026 Kaiwen Li (0xKaiwen)
