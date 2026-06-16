#!/usr/bin/env bash
# baokuan-factory · 开工前自动同步
# 每次触发 baokuan-factory 时先跑这个:把团队公共仓库拉到最新,有更新就重装 skills。
# 设计原则:**永不阻塞**。离线 / 没仓库 / 有本地改动 / 冲突 → 打一行提示就退,用当前版本继续干活。
#
# 怎么找到仓库:install.sh 安装时把仓库根路径写进了 ~/.baokuan-factory/repo。
# 怎么避免每次都重装:只有 git pull 真的移动了 HEAD 才重装,"已是最新"是个 1 秒空操作,不会刷一堆 .bak 备份。
set -uo pipefail

MARK="$HOME/.baokuan-factory/repo"
say() { printf "[sync] %s\n" "$1"; }

if [ ! -f "$MARK" ]; then
  say "没找到仓库标记($MARK),跳过自动同步。"
  say "首次请在仓库根跑一次 ./install.sh —— 它会记下仓库位置,之后才能自动拉最新。"
  exit 0
fi

REPO="$(cat "$MARK" 2>/dev/null || true)"
if [ -z "$REPO" ] || [ ! -d "$REPO/.git" ]; then
  say "$REPO 不是 git 仓库或已删除,跳过同步,用当前版本继续。"
  exit 0
fi

BEFORE="$(git -C "$REPO" rev-parse HEAD 2>/dev/null || echo none)"
if ! git -C "$REPO" pull --ff-only --quiet 2>/dev/null; then
  say "git pull 没成功(离线 / 有本地改动 / 需要 merge),用当前版本继续。"
  say "想手动解决:cd $REPO && git status"
  exit 0
fi
AFTER="$(git -C "$REPO" rev-parse HEAD 2>/dev/null || echo none)"

if [ "$BEFORE" = "$AFTER" ]; then
  say "已是最新(${AFTER:0:8})。"
  exit 0
fi

say "拉到更新:${BEFORE:0:8} → ${AFTER:0:8},重装 skills…"
git -C "$REPO" --no-pager log --oneline "$BEFORE..$AFTER" 2>/dev/null | sed 's/^/[sync]   /'
if bash "$REPO/install.sh" --force >/dev/null 2>&1; then
  say "已更新到最新。注意:本次更新下次触发才完全生效(当前对话已加载旧版 SKILL.md)。"
else
  say "重装出错,用当前版本继续。手动重装:cd $REPO && ./install.sh --force"
fi
exit 0
