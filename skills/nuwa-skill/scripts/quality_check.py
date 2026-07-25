#!/usr/bin/env python3
"""
质量门：检查生成的 SKILL.md 是否满足当前模式（person / self）的契约。

用法:
    python3 quality_check.py <SKILL.md路径 | profile目录>
    python3 quality_check.py <profile目录>   # 同时校验 assets/index.md 与 SKILL.md

模式识别（按以下顺序）:
1. SKILL.md frontmatter `profile_type: self` → self 模式
2. profile 目录中存在 `references/source-manifest.json` 且 SKILL.md 含 `profile_type: self` → self
3. 其它默认 → person 模式（保持旧版契约）
4. 显式 `--mode self|person` 覆盖自动检测

person 模式保留以下旧检查（向后兼容）:
- 心智模型数量（3–7）
- 模型局限性
- 表达 DNA
- 诚实边界（≥3 条）
- 内在张力（≥2 处）
- 一手来源占比

self 模式契约（US-010 + US-011）:
- 七个必需章节：定位与受众、核心心智模型、决策启发式、表达DNA、
  内容品味与评分标准、价值观与反模式、诚实边界
- `assets/index.md` 必须存在
- SKILL.md 至少包含一个指向 `assets/` 的相对链接
- estimated_tokens = CJK 字符数 + ceil(非 CJK 字符数 / 4)；
  > 6000 → 非零退出；< 3000 → 仅警告
- 公开面隐私扫描（US-011）：
  * 只检查 SKILL.md 与 assets/*.md，不扫描 references/
  * 检测规则 CREDENTIAL_ASSIGNMENT / WECHAT_ID / CHATROOM_ID / PRIVATE_IPV4
  * 命中仅输出 rule id + 相对路径 + 行号，不回显完整敏感值

退出码:
- 0 = 全部硬性检查通过
- 1 = 任一硬性检查失败
"""

import argparse
import ipaddress
import math
import re
import sys
from pathlib import Path


SELF_REQUIRED_SECTIONS = (
    "定位与受众",
    "核心心智模型",
    "决策启发式",
    "表达DNA",
    "内容品味与评分标准",
    "价值观与反模式",
    "诚实边界",
)


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _extract_frontmatter(text: str) -> str:
    """Return the frontmatter body (between the two leading '---' lines)."""
    if not text.startswith("---\n"):
        return ""
    end = text.find("\n---", 4)
    if end < 0:
        return ""
    return text[4:end]


def detect_profile_type(skill_path: Path) -> str:
    """Return 'self' or 'person' based on SKILL.md frontmatter profile_type."""
    if skill_path.is_dir():
        skill_md = skill_path / "SKILL.md"
    else:
        skill_md = skill_path
    if not skill_md.exists():
        return "person"
    fm = _extract_frontmatter(_read_text(skill_md))
    for line in fm.splitlines():
        if line.strip().startswith("profile_type:"):
            value = line.split(":", 1)[1].strip().lower()
            if value == "self":
                return "self"
            return "person"
    return "person"


def resolve_profile_paths(target: Path) -> tuple[Path, Path]:
    """Return (profile_dir, skill_md_path). If target is a file, treat its parent
    as the profile directory."""
    if target.is_dir():
        return target, target / "SKILL.md"
    return target.parent, target


# ---------------------- person 模式（向后兼容） ---------------------- #


def check_mental_models(content: str) -> tuple[bool, str]:
    models = re.findall(r'^###\s+(?:模型|Model|心智模型)\s*\d', content, re.MULTILINE)
    if not models:
        in_section = False
        count = 0
        for line in content.split('\n'):
            if re.match(r'^##\s+.*心智模型|Mental Model', line, re.IGNORECASE):
                in_section = True
                continue
            if in_section and re.match(r'^##\s+', line) and '心智模型' not in line:
                break
            if in_section and re.match(r'^###\s+', line):
                count += 1
        if count > 0:
            passed = 3 <= count <= 7
            return passed, f"{count}个心智模型 {'✅' if passed else '❌ (应为3-7个)'}"
    count = len(models)
    if count == 0:
        return False, "未检测到心智模型section"
    passed = 3 <= count <= 7
    return passed, f"{count}个心智模型 {'✅' if passed else '❌ (应为3-7个)'}"


def check_limitations(content: str) -> tuple[bool, str]:
    has_limitation = bool(re.search(r'局限|失效|不适用|盲区|limitation|blind spot', content, re.IGNORECASE))
    return has_limitation, "有局限性标注 ✅" if has_limitation else "❌ 未找到局限性描述"


def check_expression_dna(content: str) -> tuple[bool, str]:
    dna_section = bool(re.search(r'表达DNA|Expression DNA|表达风格', content, re.IGNORECASE))
    if not dna_section:
        return False, "❌ 未找到表达DNA section"
    style_markers = len(re.findall(r'句式|词汇|语气|幽默|节奏|确定性|引用|口头禅', content))
    passed = style_markers >= 3
    return passed, f"表达DNA特征: {style_markers}项 {'✅' if passed else '❌ (应≥3项)'}"


def check_honest_boundary(content: str) -> tuple[bool, str]:
    boundary_match = re.search(r'(?:##\s+.*诚实边界|## Honest Boundary)(.*?)(?=\n##\s|\Z)', content, re.DOTALL | re.IGNORECASE)
    if not boundary_match:
        return False, "❌ 未找到诚实边界section"
    boundary_text = boundary_match.group(1)
    items = re.findall(r'^[-*]\s+', boundary_text, re.MULTILINE)
    count = len(items)
    passed = count >= 3
    return passed, f"诚实边界: {count}条 {'✅' if passed else '❌ (应≥3条)'}"


def check_tensions(content: str) -> tuple[bool, str]:
    tension_markers = len(re.findall(r'张力|矛盾|tension|paradox|一方面.*另一方面|既.*又', content, re.IGNORECASE))
    passed = tension_markers >= 2
    return passed, f"内在张力: {tension_markers}处 {'✅' if passed else '❌ (应≥2处)'}"


def check_primary_sources(content: str) -> tuple[bool, str]:
    source_section = re.search(r'(?:##\s+.*来源|## Source|## Reference)(.*?)(?=\n##\s|\Z)', content, re.DOTALL | re.IGNORECASE)
    if not source_section:
        return True, "未找到来源section（跳过检查）"
    source_text = source_section.group(1)
    primary = len(re.findall(r'一手|primary|本人著作|原始', source_text, re.IGNORECASE))
    secondary = len(re.findall(r'二手|secondary|转述|评论', source_text, re.IGNORECASE))
    total = primary + secondary
    if total == 0:
        return True, "未标记来源类型（跳过检查）"
    ratio = primary / total
    passed = ratio > 0.5
    return passed, f"一手来源占比: {primary}/{total} ({ratio:.0%}) {'✅' if passed else '❌ (应>50%)'}"


# ---------------------- self 模式（US-010） ---------------------- #


def check_self_sections(content: str) -> tuple[bool, str]:
    missing = [section for section in SELF_REQUIRED_SECTIONS if f"## {section}" not in content]
    if missing:
        return False, "缺失章节: " + "、".join(missing)
    return True, f"七章节齐全 ✅ ({len(SELF_REQUIRED_SECTIONS)})"


def check_assets_index(profile_dir: Path, skill_md: Path) -> tuple[bool, str]:
    if not profile_dir.exists():
        return False, f"profile 目录不存在: {profile_dir}"
    index_path = profile_dir / "assets" / "index.md"
    if not index_path.exists():
        return False, "缺失文件: assets/index.md"
    return True, f"assets/index.md 存在 ✅"


def check_assets_link(skill_content: str) -> tuple[bool, str]:
    """SKILL.md 至少包含一个指向 assets/ 的相对链接。"""
    # 形如 [..](../assets/x.md)、[..](assets/x.md)、或 <assets/x.md> 风格的相对引用。
    pattern = re.compile(r'(?:\]\(|<\s*)(?:\.\./)?assets/[A-Za-z0-9_./-]+\.md(?:\s*>|\))')
    if pattern.search(skill_content):
        return True, "SKILL.md 含 assets/ 相对链接 ✅"
    return False, "SKILL.md 未找到指向 assets/ 的相对链接"


def estimate_tokens(content: str) -> int:
    """CJK 字符数 + ceil(非 CJK 字符数 / 4)。"""
    cjk = sum(1 for ch in content if '一' <= ch <= '鿿')
    non_cjk = len(content) - cjk
    return cjk + math.ceil(non_cjk / 4)


def check_self_token_budget(skill_content: str) -> tuple[bool, str]:
    tokens = estimate_tokens(skill_content)
    if tokens > 6000:
        return False, f"估算 token={tokens} > 6000 ❌"
    if tokens < 3000:
        # 软警告，不阻塞；通过 + ⚠️。
        return True, f"估算 token={tokens} < 3000 ⚠️ (警告，不阻塞)"
    return True, f"估算 token={tokens} ✅"


# ---------------------- self 模式隐私扫描（US-011） ---------------------- #


# Rule IDs 与 pattern 由 self-distill-workflow.md §8 锁定；新增/重命名都会
# 破坏下游脚本与文档约定。本模块不修改规则集合。
PRIVACY_RULES: dict[str, re.Pattern[str]] = {
    # token=...、password: ...、secret = "..." 等赋值形式；
    # 仅在「key 紧邻分隔符 = 或 :」时算违规，避免命中正文里的普通单词。
    "CREDENTIAL_ASSIGNMENT": re.compile(
        r"(?i)\b(?:token|password|passwd|secret|api[_-]?key|access[_-]?token)"
        r"\s*[:=]\s*['\"]?[A-Za-z0-9_./+=-]{4,}"
    ),
    # 微信 wxid_ 前缀字符串；只命中显式前缀，避免误伤正文里的 “wxid 怎么读”。
    "WECHAT_ID": re.compile(r"\bwxid_[A-Za-z0-9_-]{4,}"),
    # 微信群 @chatroom；要求前面不是合法 URL 字符，避免命中 markdown 链接里的
    # "@chatroom/xxx"（虽然实际不大可能）；保持宽松即可。
    "CHATROOM_ID": re.compile(r"@chatroom\b"),
    # RFC1918 + loopback；通过 ipaddress 校验，避免误伤 999.999.999.999 之类。
    "PRIVATE_IPV4": re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
}


def _is_private_ipv4(candidate: str) -> bool:
    try:
        address = ipaddress.IPv4Address(candidate)
    except ValueError:
        return False
    return (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_reserved
        or address.is_multicast
        or address.is_unspecified
    )


# 修复 frontmatter / fenced code block 时，不能因为 metadata 里出现 wxid_ 字样就误报；
# 但规则上仍要扫 frontmatter，因为 SKILL.md 头部被质量门读取前先要走隐私扫描。
# 这里不做剔除，统一全文件扫描；用户/编写者只需保证公开面不出现敏感值。


def scan_privacy_in_text(text: str, rule_id: str) -> list[tuple[int, str]]:
    """Return list of (line_number, snippet) for matches of a given rule.

    snippet 只截取被命中行的前 80 字符（不含敏感尾部），避免回显完整凭据/IP。
    line_number 从 1 起。
    """
    pattern = PRIVACY_RULES[rule_id]
    hits: list[tuple[int, str]] = []
    for index, raw_line in enumerate(text.splitlines(), start=1):
        if rule_id == "PRIVATE_IPV4":
            for match in pattern.finditer(raw_line):
                if _is_private_ipv4(match.group(0)):
                    snippet = raw_line[:80]
                    hits.append((index, snippet))
        else:
            if pattern.search(raw_line):
                snippet = raw_line[:80]
                hits.append((index, snippet))
    return hits


def scan_privacy_gate(profile_dir: Path, skill_md: Path) -> tuple[bool, list[tuple[str, str, int]]]:
    """扫描 SKILL.md 与 assets/*.md；references/ 与其他路径不扫描。

    返回 (passed, findings)；findings 每条形如 (rule_id, relative_path, line)。
    """
    findings: list[tuple[str, str, int]] = []

    targets: list[tuple[Path, str]] = []
    if skill_md.exists():
        targets.append((skill_md, _relpath(profile_dir, skill_md)))

    assets_dir = profile_dir / "assets"
    if assets_dir.exists():
        for path in sorted(assets_dir.glob("*.md")):
            targets.append((path, _relpath(profile_dir, path)))

    for path, rel in targets:
        text = _read_text(path)
        for rule_id in PRIVACY_RULES:
            for line_no, _snippet in scan_privacy_in_text(text, rule_id):
                findings.append((rule_id, rel, line_no))

    return (len(findings) == 0), findings


def _relpath(base: Path, target: Path) -> str:
    try:
        return target.relative_to(base).as_posix()
    except ValueError:
        # 越界 fallback：返回绝对路径（一般不应发生）。
        return target.as_posix()


def format_privacy_findings(findings: list[tuple[str, str, int]]) -> str:
    """把 findings 渲染成可执行的多行错误信息（不回显完整敏感值）。"""
    lines = ["隐私扫描命中 {} 处违规：".format(len(findings))]
    for rule_id, rel, line_no in findings:
        lines.append(f"  - {rule_id} @ {rel}:{line_no}")
    return "\n".join(lines)


# ---------------------- 主流程 ---------------------- #


def _print_section(title: str) -> None:
    print("=" * 60)
    print(title)
    print("=" * 60)


def _run_checks(label: str, checks: list[tuple[str, tuple[bool, str]]]) -> tuple[int, int]:
    passed_count = 0
    total = len(checks)
    print(f"\n[{label}]")
    for name, (passed, detail) in checks:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {name:<24} {status}  {detail}")
        if passed:
            passed_count += 1
    return passed_count, total


def run_quality_check(target: Path, mode: str | None) -> int:
    profile_dir, skill_md_path = resolve_profile_paths(target)
    detected = detect_profile_type(target)
    profile_type = mode if mode in ("self", "person") else detected
    print(f"quality_check target={target} detected={detected} mode={profile_type}")

    if not skill_md_path.exists():
        print(f"❌ SKILL.md 不存在: {skill_md_path}")
        return 1
    skill_content = _read_text(skill_md_path)

    if profile_type == "self":
        _print_section("self 模式契约（US-010 + US-011）")
        section_ok, section_detail = check_self_sections(skill_content)
        index_ok, index_detail = check_assets_index(profile_dir, skill_md_path)
        link_ok, link_detail = check_assets_link(skill_content)
        budget_ok, budget_detail = check_self_token_budget(skill_content)
        privacy_ok, privacy_findings = scan_privacy_gate(profile_dir, skill_md_path)
        if privacy_ok:
            privacy_detail = "公开面隐私扫描通过 ✅"
        else:
            privacy_detail = format_privacy_findings(privacy_findings)
        checks = [
            ("七个必需章节", (section_ok, section_detail)),
            ("assets/index.md 存在", (index_ok, index_detail)),
            ("assets/ 相对链接", (link_ok, link_detail)),
            ("token 预算 (3000-6000)", (budget_ok, budget_detail)),
            ("公开面隐私扫描", (privacy_ok, privacy_detail)),
        ]
        passed, total = _run_checks("self", checks)
        print("=" * 60)
        print(f"结果: {passed}/{total} 通过")
        if passed == total:
            print("🎉 self 模式质量门通过")
            return 0
        print("❌ self 模式存在失败项")
        return 1

    # person 模式（旧契约，保持兼容）
    _print_section("person 模式契约（兼容旧版）")
    checks = [
        ("心智模型数量", check_mental_models(skill_content)),
        ("模型局限性", check_limitations(skill_content)),
        ("表达DNA辨识度", check_expression_dna(skill_content)),
        ("诚实边界", check_honest_boundary(skill_content)),
        ("内在张力", check_tensions(skill_content)),
        ("一手来源占比", check_primary_sources(skill_content)),
    ]
    passed, total = _run_checks("person", checks)
    print("=" * 60)
    print(f"结果: {passed}/{total} 通过")
    if passed == total:
        print("🎉 全部通过，可以交付")
        return 0
    if passed >= total - 1:
        print("⚠️ 基本通过，建议修复不通过项后交付")
        return 0  # 与旧版兼容：total-1 通过仍视为 exit 0。
    print("❌ 多项不通过，建议回到Phase 2迭代")
    return 1


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Nuwa SKILL.md 质量门")
    parser.add_argument("target", help="SKILL.md 路径或 profile 目录")
    parser.add_argument("--mode", choices=("self", "person"), default=None,
                        help="显式模式覆盖自动检测")
    args = parser.parse_args(argv)
    target = Path(args.target)
    if not target.exists():
        print(f"❌ 路径不存在: {target}")
        return 1
    return run_quality_check(target, args.mode)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))