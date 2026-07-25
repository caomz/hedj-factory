#!/usr/bin/env python3
"""
合并6个Agent的调研结果，生成Phase 1.5调研Review检查点的摘要表格。

支持两种模式:
- person（默认）: 公众人物蒸馏，六个标签为 著作/对话/表达/他者/决策/时间线。
- self:           自我蒸馏，六个标签为 positioning/core-theses/decisions-and-behavior/
                  systems-and-cases/expression-dna/tensions-and-evolution；按相对源路径
                  去重计数证据，并结合 references/source-manifest.json 统计来源 class。

用法:
    python3 merge_research.py <skill目录路径> [--mode person|self]

示例:
    python3 merge_research.py .claude/skills/elon-musk-perspective
    python3 merge_research.py skills/<handle>-profile --mode self

输出: 打印markdown格式的摘要表格到stdout
"""

import argparse
import json
import re
import sys
from pathlib import Path


PERSON_AGENTS = {
    "01-writings": "著作",
    "02-conversations": "对话",
    "03-expression-dna": "表达",
    "04-external-views": "他者",
    "05-decisions": "决策",
    "06-timeline": "时间线",
}


# self 模式六个研究维度，与 references/self-distill-workflow.md §5 锁定一致。
SELF_AGENTS = {
    "01-positioning": "positioning",
    "02-core-theses": "core-theses",
    "03-decisions-and-behavior": "decisions-and-behavior",
    "04-systems-and-cases": "systems-and-cases",
    "05-expression-dna": "expression-dna",
    "06-tensions-and-evolution": "tensions-and-evolution",
}


# self 模式相对路径 frontmatter 字段候选名（任一出现即可）。
SELF_SOURCE_FIELDS = ("sources", "source_paths", "relative_sources")


def count_sources(content: str) -> dict:
    """统计来源数量和一手/二手占比（person 模式）。"""
    urls = re.findall(r"https?://[^\s\)]+", content)
    primary_markers = len(
        re.findall(r"一手|primary|本人|原文|原始|直接引用", content, re.IGNORECASE)
    )
    secondary_markers = len(
        re.findall(r"二手|secondary|转述|总结|评论|分析", content, re.IGNORECASE)
    )
    return {
        "url_count": len(urls),
        "unique_urls": len(set(urls)),
        "primary_markers": primary_markers,
        "secondary_markers": secondary_markers,
    }


def extract_key_findings(content: str, max_items: int = 3) -> list[str]:
    """提取关键发现（取前几个二级标题或加粗项）。"""
    headings = re.findall(r"^##\s+(.+)$", content, re.MULTILINE)
    if headings:
        return headings[:max_items]

    bolds = re.findall(r"\*\*(.+?)\*\*", content)
    if bolds:
        return bolds[:max_items]

    lines = [
        line.strip()
        for line in content.split("\n")
        if line.strip() and not line.startswith("#")
    ]
    return [
        (line[:50] + "..." if len(line) > 50 else line) for line in lines[:max_items]
    ]


def find_contradictions(files: dict[str, str], label_map: dict[str, str]) -> list[str]:
    """简单检测跨文件矛盾（同一关键词出现不同判断）。"""
    contradictions = []
    for name, content in files.items():
        matches = re.findall(r"(?:矛盾|相反|但实际上|然而.*?不同|争议).{0,100}", content)
        for match in matches:
            contradictions.append(f"{label_map.get(name, name)}: {match[:80]}")
    return contradictions[:5]


# ---------------------------------------------------------------------------
# self 模式 helpers
# ---------------------------------------------------------------------------


def _strip_frontmatter(content: str) -> str:
    """移除 YAML frontmatter，返回正文。"""
    if content.startswith("---"):
        end = content.find("\n---", 3)
        if end != -1:
            return content[end + 4 :].lstrip("\n")
    return content


def _parse_frontmatter_fields(content: str) -> dict[str, object]:
    """极简 frontmatter 解析：只读扁平 YAML key/value；列表字段按 `-` 行收集。

    不引入 PyYAML 依赖；只支持 self 模式所需的少量字段。
    """
    if not content.startswith("---"):
        return {}
    end = content.find("\n---", 3)
    if end == -1:
        return {}
    block = content[3:end].strip("\n")
    fields: dict[str, object] = {}
    current_list_key: str | None = None
    for raw_line in block.splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        if raw_line.startswith("  - ") or raw_line.startswith("- "):
            value = raw_line.split("- ", 1)[1].strip()
            if current_list_key is not None:
                existing = fields.get(current_list_key)
                if isinstance(existing, list):
                    existing.append(value)
                else:
                    fields[current_list_key] = [value]
            continue
        if ":" in raw_line:
            key, _, value = raw_line.partition(":")
            key = key.strip()
            value = value.strip()
            if value == "":
                fields[key] = []
                current_list_key = key
            elif value.startswith("[") and value.endswith("]"):
                inner = value[1:-1].strip()
                items: list[str] = []
                if inner:
                    items = [
                        token.strip().strip('"').strip("'")
                        for token in inner.split(",")
                        if token.strip()
                    ]
                fields[key] = items
                current_list_key = None
            else:
                fields[key] = value.strip('"').strip("'")
                current_list_key = None
    return fields


def _extract_self_sources(content: str) -> list[str]:
    """从 self 研究文件中提取相对源路径列表。

    优先级:
    1. frontmatter 中 sources / source_paths / relative_sources 列表。
    2. 正文中形如 `notes/foo.md` `summaries/bar.md` 的相对路径（裸词，
       不含 scheme、绝对路径或 markdown 链接括号）。
    """
    fields = _parse_frontmatter_fields(content)
    for key in SELF_SOURCE_FIELDS:
        value = fields.get(key)
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str) and value:
            return [value]

    body = _strip_frontmatter(content)
    pattern = re.compile(
        r"(?<![\w/])((?:[A-Za-z0-9_\-]+/)*[A-Za-z0-9_\-]+\.[A-Za-z0-9]{1,8})(?![\w/])"
    )
    candidates: list[str] = []
    seen: set[str] = set()
    for match in pattern.finditer(body):
        path = match.group(1)
        if path in seen:
            continue
        seen.add(path)
        candidates.append(path)
    return candidates


def _load_source_manifest(skill_dir: Path) -> dict[str, str] | None:
    """加载 profile 内的 source-manifest.json，返回 {relative_path: policy_class}。

    缺失或非法 JSON 时返回 None；调用方应容忍 manifest 缺失并跳过 class 统计。
    """
    manifest_path = skill_dir / "references" / "source-manifest.json"
    if not manifest_path.is_file():
        return None
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    files = payload.get("files")
    if not isinstance(files, list):
        return None
    mapping: dict[str, str] = {}
    for entry in files:
        if not isinstance(entry, dict):
            continue
        rel = entry.get("relative_path")
        policy_class = entry.get("policy_class")
        if isinstance(rel, str) and isinstance(policy_class, str):
            mapping[rel] = policy_class
    return mapping


def _dedupe_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


def _render_self_table(
    rows: list[str],
    total_unique_sources: int,
    class_counts: dict[str, int],
    class_breakdown_text: str,
    missing: list[str],
    contradictions: list[str],
) -> str:
    """self 模式表格输出。"""
    lines = [
        "┌──────────────┬──────────┬──────────────────────────┐",
        "│ Dimension    │ 来源数    │ 关键发现                  │",
        "├──────────────┼──────────┼──────────────────────────┤",
    ]
    lines.extend(rows)
    lines.extend(
        [
            "├──────────────┼──────────┼──────────────────────────┤",
            f"│ 总来源(去重) │ {total_unique_sources:<8} │ {class_breakdown_text[:24]:<24} │",
        ]
    )
    if contradictions:
        lines.append(
            f"│ 矛盾点       │ {len(contradictions)}处      │ {contradictions[0][:24]:<24} │"
        )
    else:
        lines.append("│ 矛盾点       │ 0处      │ —                        │")
    if missing:
        lines.append(
            f"│ 信息不足维度  │ {len(missing)}个      │ {', '.join(missing)[:24]:<24} │"
        )
    else:
        lines.append("│ 信息不足维度  │ 无       │ —                        │")
    lines.append("└──────────────┴──────────┴──────────────────────────┘")

    # class 计数详情放在表格外，避免被 24 字符槽位截断。
    if class_counts:
        breakdown = ", ".join(
            f"{name}={count}"
            for name, count in sorted(
                class_counts.items(), key=lambda item: (-item[1], item[0])
            )
        )
        lines.append("")
        lines.append(f"class counts: {breakdown}")

    warnings: list[str] = []
    if class_counts:
        unlabeled = class_counts.get("unclassified", 0)
        if unlabeled:
            warnings.append(
                f"⚠️ 有 {unlabeled} 个 unclassified 来源路径尚未被 manifest 分类。"
            )
    if missing:
        warnings.append(
            f"⚠️ 缺失维度: {', '.join(missing)}，建议补充或在诚实边界中标注"
        )
    if warnings:
        lines.append("")
        lines.extend(warnings)
    return "\n".join(lines)


def _render_person_table(
    rows: list[str],
    total_sources: int,
    total_primary: int,
    total_secondary: int,
    contradictions: list[str],
    missing: list[str],
) -> str:
    primary_ratio = (
        f"{total_primary}/{total_primary + total_secondary}"
        if (total_primary + total_secondary) > 0
        else "未标记"
    )
    lines = [
        "┌──────────────┬──────────┬──────────────────────────┐",
        "│ Agent        │ 来源数量  │ 关键发现                  │",
        "├──────────────┼──────────┼──────────────────────────┤",
    ]
    lines.extend(rows)
    lines.extend(
        [
            "├──────────────┼──────────┼──────────────────────────┤",
            f"│ 总来源数      │ {total_sources:<8} │ 一手占比: {primary_ratio:<15} │",
        ]
    )
    if contradictions:
        lines.append(
            f"│ 矛盾点        │ {len(contradictions)}处      │ {contradictions[0][:24]:<24} │"
        )
    else:
        lines.append("│ 矛盾点        │ 0处      │ —                        │")
    if missing:
        lines.append(
            f"│ 信息不足维度   │ {len(missing)}个      │ {', '.join(missing):<24} │"
        )
    else:
        lines.append("│ 信息不足维度   │ 无       │ —                        │")
    lines.append("└──────────────┴──────────┴──────────────────────────┘")

    if total_sources < 10:
        lines.append("")
        lines.append("⚠️ 总来源数 <10，建议降低期望或补充调研")
    if missing:
        lines.append("")
        lines.append(
            f"⚠️ 缺失维度: {', '.join(missing)}，建议补充或在诚实边界中标注"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="合并 nuwa-skill 调研结果。person / self 两种模式。"
    )
    parser.add_argument(
        "skill_dir",
        help="skill 目录路径；person 模式下含 references/research/，self 模式下还含 references/source-manifest.json",
    )
    parser.add_argument(
        "--mode",
        choices=("person", "self"),
        default=None,
        help="person 模式使用公众人物六标签；self 模式使用自我六标签。",
    )
    return parser


def _detect_mode(skill_dir: Path, explicit: str | None) -> str:
    """自动检测：profile_type: self → self；否则 person。

    显式传入 --mode 时优先使用显式值。
    """
    if explicit in ("person", "self"):
        return explicit
    skill_md = skill_dir / "SKILL.md"
    if skill_md.is_file():
        try:
            text = skill_md.read_text(encoding="utf-8")
        except OSError:
            text = ""
        if re.search(r"^profile_type:\s*self\s*$", text, re.MULTILINE):
            return "self"
    return "person"


def _run_person(skill_dir: Path) -> int:
    research_dir = skill_dir / "references" / "research"
    if not research_dir.exists():
        print(f"❌ 目录不存在: {research_dir}")
        return 1

    files: dict[str, str] = {}
    rows: list[str] = []
    total_sources = 0
    total_primary = 0
    total_secondary = 0
    missing: list[str] = []

    for key, label in PERSON_AGENTS.items():
        md_file = research_dir / f"{key}.md"
        if not md_file.exists():
            missing.append(label)
            rows.append(f"│ {label:<12} │ {'❌ 缺失':<8} │ {'—':<24} │")
            continue

        content = md_file.read_text(encoding="utf-8")
        files[key] = content
        stats = count_sources(content)
        findings = extract_key_findings(content)

        total_sources += stats["unique_urls"]
        total_primary += stats["primary_markers"]
        total_secondary += stats["secondary_markers"]

        findings_str = ", ".join(findings) if findings else "—"
        if len(findings_str) > 40:
            findings_str = findings_str[:37] + "..."

        rows.append(f"│ {label:<12} │ {stats['unique_urls']:<8} │ {findings_str:<24} │")

    contradictions = find_contradictions(files, PERSON_AGENTS)
    print(_render_person_table(
        rows=rows,
        total_sources=total_sources,
        total_primary=total_primary,
        total_secondary=total_secondary,
        contradictions=contradictions,
        missing=missing,
    ))
    return 0


def _run_self(skill_dir: Path) -> int:
    research_dir = skill_dir / "references" / "research"
    if not research_dir.exists():
        print(f"❌ 目录不存在: {research_dir}")
        return 1

    class_lookup = _load_source_manifest(skill_dir)
    if class_lookup is None:
        # 无 manifest 不阻塞 self 模式，仅跳过 class 统计。
        print(
            "ℹ️ 未读取到 references/source-manifest.json，"
            "将仅按相对路径去重统计，不输出 class 计数。",
            file=sys.stderr,
        )

    files: dict[str, str] = {}
    rows: list[str] = []
    dimension_source_counts: list[int] = []
    all_sources: list[str] = []
    class_counts: dict[str, int] = {}
    missing: list[str] = []

    for key, label in SELF_AGENTS.items():
        md_file = research_dir / f"{key}.md"
        if not md_file.exists():
            missing.append(label)
            rows.append(f"│ {label:<12} │ {'❌ 缺失':<8} │ {'—':<24} │")
            continue

        content = md_file.read_text(encoding="utf-8")
        files[key] = content
        sources = _extract_self_sources(content)
        findings = extract_key_findings(content)

        # 维度内先按出现顺序去重；不同维度之间在最后统一去重。
        unique_in_dim = _dedupe_preserve_order(sources)
        dimension_source_counts.append(len(unique_in_dim))
        all_sources.extend(unique_in_dim)

        if class_lookup is not None:
            for rel in unique_in_dim:
                cls = class_lookup.get(rel, "unclassified")
                class_counts[cls] = class_counts.get(cls, 0) + 1

        findings_str = ", ".join(findings) if findings else "—"
        if len(findings_str) > 40:
            findings_str = findings_str[:37] + "..."

        rows.append(
            f"│ {label:<12} │ {len(unique_in_dim):<8} │ {findings_str:<24} │"
        )

    total_unique = len(_dedupe_preserve_order(all_sources))
    if class_counts:
        # 按 class 名字典序输出，写到「总来源」右侧的 24 字符槽中。
        top = sorted(class_counts.items(), key=lambda item: (-item[1], item[0]))
        breakdown = ", ".join(f"{name}:{count}" for name, count in top[:3])
        class_breakdown_text = f"class: {breakdown}"
    else:
        class_breakdown_text = "—"

    contradictions = find_contradictions(files, SELF_AGENTS)
    print(_render_self_table(
        rows=rows,
        total_unique_sources=total_unique,
        class_counts=class_counts,
        class_breakdown_text=class_breakdown_text,
        missing=missing,
        contradictions=contradictions,
    ))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    skill_dir = Path(args.skill_dir)
    if not skill_dir.exists():
        print(f"❌ 目录不存在: {skill_dir}")
        return 1
    if not skill_dir.is_dir():
        print(f"❌ 不是目录: {skill_dir}")
        return 1

    mode = _detect_mode(skill_dir, args.mode)
    if mode == "self":
        return _run_self(skill_dir)
    return _run_person(skill_dir)


if __name__ == "__main__":
    sys.exit(main())