#!/usr/bin/env python3
"""Validate the shared image-prompt contract and its production wiring."""
from __future__ import annotations

import re
import sys
from pathlib import Path


DEFAULT_REPO_ROOT = Path(__file__).resolve().parents[3]
SCHEMA_REL = Path("skills/hyperframes/references/image-prompt-schema.md")

REQUIRED_HEADINGS = (
    "什么时候用 /browse、什么时候用 AI 生图",
    "六块提示词协议（6-block protocol）",
    "1. 主体与任务（subject/task）",
    "2. 构图与版式（composition/layout）",
    "3. 视觉风格与材质（visual style/materials）",
    "4. 文字与标签（text & labels）",
    "5. 画幅比例与输出格式（aspect ratio / output format）",
    "6. 约束与负面清单（constraints & negatives）",
    "填空模板（按用途取用）",
    "模板 A · 书籍卡片装饰图兜底（book-narration-video `cover.jpg`）",
    "模板 B · 示意信息图 / 图表风卡片（talking-head chart/recap 类装饰素材）",
    "模板 C · 叙事多格 / 九宫格 storyboard",
    "成本闸门（批量九宫格 / 多格生成必过）",
    "来源登记与生成后验收",
    "禁止事项（What NOT to Do）",
    "署名与来源",
)

REQUIRED_SCHEMA_CONTRACTS = (
    "证据必须真，装饰可以生",
    "AI 生成的栅格图默认不承载生产文字",
    "`book-narration-video` 正式九宫格整页为约 16:9",
    "不能伪造或复刻书封",
    "成本写“未知”",
    "ai_disclosure_required: true",
    "source_url",
    "awesome-gpt-image-2",
    "Copyright © 2026 freestylefly",
    "MIT License",
)

FORBIDDEN_SCHEMA_CONTRACTS = (
    "单张 1:1 画布等分 3×3 九格",
    "生成《<书名>》（<作者>）的示意书封",
)

WIRING = {
    Path("skills/hyperframes/SKILL.md"): (
        "references/image-prompt-schema.md",
        "Visual Identity Gate",
    ),
    Path("skills/book-narration-video/SKILL.md"): (
        "../hyperframes/references/image-prompt-schema.md",
        "成本闸门",
        "不能伪造或复刻书封",
    ),
    Path("skills/talking-head-edit/SKILL.md"): (
        "../hyperframes/references/image-prompt-schema.md",
        "/browse` = 证据",
        "绝不用 AI 伪造真实新闻截图",
    ),
    Path("docs/SOP.md"): (
        "skills/hyperframes/references/image-prompt-schema.md",
        "绝不 AI 伪造",
        "成本闸门",
    ),
}


def markdown_headings(text: str) -> set[str]:
    return {
        match.group(1).strip()
        for match in re.finditer(r"^#{2,3}\s+(.+?)\s*$", text, flags=re.MULTILINE)
    }


def check_repo(repo_root: Path = DEFAULT_REPO_ROOT) -> list[str]:
    repo_root = repo_root.resolve()
    schema = repo_root / SCHEMA_REL
    failures: list[str] = []
    if not schema.is_file():
        return [f"缺文件 {SCHEMA_REL}"]
    text = schema.read_text(encoding="utf-8")
    headings = markdown_headings(text)
    for heading in REQUIRED_HEADINGS:
        if heading not in headings:
            failures.append(f"schema 缺精确章节: {heading!r}")
    for contract in REQUIRED_SCHEMA_CONTRACTS:
        if contract not in text:
            failures.append(f"schema 缺生产合同: {contract!r}")
    for contract in FORBIDDEN_SCHEMA_CONTRACTS:
        if contract in text:
            failures.append(f"schema 含冲突合同: {contract!r}")

    for relative, needles in WIRING.items():
        path = repo_root / relative
        if not path.is_file():
            failures.append(f"缺接线文件: {relative}")
            continue
        wired = path.read_text(encoding="utf-8")
        for needle in needles:
            if needle not in wired:
                failures.append(f"{relative} 缺接线语义: {needle!r}")
    return failures


def main() -> int:
    failures = check_repo()
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        print(f"\n{len(failures)} 项未通过")
        return 1
    print(
        f"OK: {SCHEMA_REL} 含全部 {len(REQUIRED_HEADINGS)} 个精确章节、"
        f"{len(REQUIRED_SCHEMA_CONTRACTS)} 条生产合同；{len(WIRING)} 处接线通过"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
