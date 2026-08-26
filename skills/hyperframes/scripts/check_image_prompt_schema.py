#!/usr/bin/env python3
"""校验 image-prompt-schema.md 存在且包含必需章节；同时校验三处 SKILL 接线。

用法: python3 skills/hyperframes/scripts/check_image_prompt_schema.py
退出码: 0 = 全部通过, 1 = 有缺失。
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCHEMA = REPO_ROOT / "skills" / "hyperframes" / "references" / "image-prompt-schema.md"

REQUIRED_SECTIONS = [
    # browse vs 生图分流
    "什么时候用 /browse、什么时候用 AI 生图",
    # 六块协议总标题 + 六块各自的名字
    "六块提示词协议",
    "主体与任务（subject/task）",
    "构图与版式（composition/layout",
    "视觉风格与材质（visual style/materials）",
    "文字与标签（text & labels）",
    "画幅比例与输出格式（aspect ratio / output format）",
    "约束与负面清单（constraints & negatives）",
    # 模板、成本闸门、禁区、署名
    "填空模板",
    "模板 A · 书封兜底",
    "模板 B · 示意信息图",
    "模板 C · 叙事多格 / 九宫格",
    "成本闸门",
    "禁止事项",
    "署名与来源",
    "awesome-gpt-image-2",
]

WIRING = {
    REPO_ROOT / "skills" / "hyperframes" / "SKILL.md": "references/image-prompt-schema.md",
    REPO_ROOT / "skills" / "book-narration-video" / "SKILL.md": "image-prompt-schema.md",
    REPO_ROOT / "skills" / "talking-head-edit" / "SKILL.md": "image-prompt-schema.md",
    REPO_ROOT / "docs" / "SOP.md": "image-prompt-schema.md",
}


def main() -> int:
    failures = []

    if not SCHEMA.is_file():
        print(f"FAIL: 缺文件 {SCHEMA.relative_to(REPO_ROOT)}")
        return 1
    text = SCHEMA.read_text(encoding="utf-8")

    for section in REQUIRED_SECTIONS:
        if section not in text:
            failures.append(f"schema 缺章节/关键词: {section!r}")

    for path, needle in WIRING.items():
        rel = path.relative_to(REPO_ROOT)
        if not path.is_file():
            failures.append(f"缺接线文件: {rel}")
        elif needle not in path.read_text(encoding="utf-8"):
            failures.append(f"{rel} 未引用 {needle}")

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        print(f"\n{len(failures)} 项未通过")
        return 1

    print(
        f"OK: {SCHEMA.relative_to(REPO_ROOT)} 含全部 {len(REQUIRED_SECTIONS)} 个必需章节；"
        f"{len(WIRING)} 处接线就位"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
