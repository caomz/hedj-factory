#!/usr/bin/env python3
"""只读盘点本地知识目录，生成确定性的文件资格记录。

当前阶段只在内存中生成基础记录并输出统计；manifest 与 review 文件由后续
story 实现。

用法：
    python3 inventory_local_corpus.py SOURCE_ROOT --check
    python3 inventory_local_corpus.py SOURCE_ROOT --profile-dir PROFILE_DIR
"""

import argparse
import datetime as _datetime
import hashlib
import json
import os
import re
import stat
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

MANIFEST_SCHEMA_VERSION = 1
MANIFEST_FILE_NAME = "source-manifest.json"
INVENTORY_REVIEW_FILE = "00-source-inventory.md"
INVENTORY_REVIEW_DIR = "research"


DEFAULT_MAX_FILE_BYTES = 2_000_000
BINARY_SAMPLE_BYTES = 8_192
SUPPORTED_TEXT_EXTENSIONS = frozenset(
    {
        ".csv",
        ".htm",
        ".html",
        ".json",
        ".jsonl",
        ".markdown",
        ".md",
        ".txt",
        ".yaml",
        ".yml",
    }
)
SEMANTIC_FIELDS = frozenset({"title", "summary", "content", "chat_content"})

POLICY_SCHEMA_VERSION = 1
VALID_POLICY_CLASSES = frozenset(
    {"authored", "private-evidence", "adapted", "external", "excluded"}
)
DISTILLABLE_POLICY_CLASSES = frozenset(
    {"authored", "private-evidence", "adapted", "external"}
)


class InputValidationError(ValueError):
    """命令行输入不满足只读与输出路径约束。"""


class InventoryError(RuntimeError):
    """源目录无法被完整、确定地盘点。"""


class SourcePolicyError(ValueError):
    """source-policy.json 不满足 schema 或语义约束。"""


def positive_int(value: str) -> int:
    """解析大于零的整数参数。"""
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"必须是整数: {value}") from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError("必须大于 0")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    """创建 inventory CLI 参数解析器。"""
    parser = argparse.ArgumentParser(
        description="只读盘点本地知识目录；默认不会复制或修改源文件。",
    )
    parser.add_argument("source_root", type=Path, help="待盘点的本地目录")
    parser.add_argument(
        "--profile-dir",
        type=Path,
        help="inventory 产物所属的 profile 目录；--check 模式可省略",
    )
    parser.add_argument(
        "--policy",
        type=Path,
        help="可选的 source-policy.json 路径（后续 story 应用规则）",
    )
    parser.add_argument(
        "--max-file-bytes",
        type=positive_int,
        default=DEFAULT_MAX_FILE_BYTES,
        help=f"单文件资格上限，默认 {DEFAULT_MAX_FILE_BYTES}",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="只检查输入并输出摘要，不创建或修改任何文件",
    )
    return parser


def is_within(path: Path, directory: Path) -> bool:
    """判断 path 是否等于 directory 或位于其内部。"""
    try:
        path.relative_to(directory)
    except ValueError:
        return False
    return True


def validate_inputs(args: argparse.Namespace) -> None:
    """在任何盘点或写入发生前验证输入与输出边界。"""
    source_root = args.source_root.expanduser()
    if not source_root.exists():
        raise InputValidationError(f"source_root 不存在: {source_root}")
    if not source_root.is_dir():
        raise InputValidationError(f"source_root 不是目录: {source_root}")

    if not args.check and args.profile_dir is None:
        raise InputValidationError("非 --check 模式必须提供 --profile-dir")

    if args.profile_dir is not None:
        resolved_source = source_root.resolve()
        resolved_profile = args.profile_dir.expanduser().resolve(strict=False)
        if is_within(resolved_profile, resolved_source):
            raise InputValidationError(
                "profile-dir 不得位于 source_root 内部: "
                f"{args.profile_dir} (source_root: {source_root})"
            )


def is_binary_file(path: Path) -> bool:
    """通过有限字节样本识别明显二进制内容，不做语义解析。"""
    try:
        with path.open("rb") as source_file:
            sample = source_file.read(BINARY_SAMPLE_BYTES)
    except OSError as exc:
        raise InventoryError(f"无法读取文件: {path}: {exc}") from exc

    if b"\x00" in sample:
        return True
    try:
        sample.decode("utf-8")
    except UnicodeDecodeError:
        return True
    return False


def determine_eligibility(
    path: Path,
    size_bytes: int,
    max_file_bytes: int,
) -> Tuple[bool, Optional[str], str]:
    """按大小、扩展名和二进制样本返回稳定的资格结果与小写扩展名。"""
    if size_bytes > max_file_bytes:
        return False, "oversized", path.suffix.lower()
    extension = path.suffix.lower()
    if extension not in SUPPORTED_TEXT_EXTENSIONS:
        return False, "unsupported_extension", extension
    if is_binary_file(path):
        return False, "binary", extension
    return True, None, extension


def top_level_family(relative_path: Path) -> str:
    """返回首层目录名；根目录直属文件统一归入点号 family。"""
    if len(relative_path.parts) == 1:
        return "."
    return relative_path.parts[0]


def load_source_policy(path: Path) -> Dict[str, object]:
    """加载并校验 source-policy.json。

    校验项：
    - JSON 合法（``json.loads`` 不抛）
    - 顶层为对象，且 ``schema_version == 1``
    - ``rules`` 为非空数组
    - 每条 rule 为对象，包含 ``class``（必须是 ``VALID_POLICY_CLASSES`` 之一）
      与非空 ``globs`` 字符串数组
    """
    try:
        raw_text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise SourcePolicyError(f"无法读取 source-policy.json: {path}: {exc}") from exc
    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise SourcePolicyError(
            f"source-policy.json 不是合法 JSON: {path}: {exc}"
        ) from exc

    if not isinstance(payload, dict):
        raise SourcePolicyError(
            f"source-policy.json 顶层必须是对象: {path}"
        )

    schema_version = payload.get("schema_version")
    if schema_version != POLICY_SCHEMA_VERSION:
        raise SourcePolicyError(
            f"source-policy.json schema_version 必须为 "
            f"{POLICY_SCHEMA_VERSION}: 实际 {schema_version!r}"
        )

    rules = payload.get("rules")
    if not isinstance(rules, list) or not rules:
        raise SourcePolicyError("source-policy.json rules 必须为非空数组")

    normalized_rules: List[Dict[str, object]] = []
    for index, rule in enumerate(rules):
        if not isinstance(rule, dict):
            raise SourcePolicyError(f"rules[{index}] 必须是对象")
        class_name = rule.get("class")
        if not isinstance(class_name, str) or class_name not in VALID_POLICY_CLASSES:
            raise SourcePolicyError(
                f"rules[{index}].class 必须是 {sorted(VALID_POLICY_CLASSES)}"
                f" 之一: {class_name!r}"
            )
        globs = rule.get("globs")
        if not isinstance(globs, list) or not globs:
            raise SourcePolicyError(f"rules[{index}].globs 必须为非空数组")
        for glob_index, glob_pattern in enumerate(globs):
            if not isinstance(glob_pattern, str) or not glob_pattern:
                raise SourcePolicyError(
                    f"rules[{index}].globs[{glob_index}] 必须为非空字符串"
                )
        normalized_rules.append({"class": class_name, "globs": list(globs)})

    return {
        "schema_version": POLICY_SCHEMA_VERSION,
        "rules": normalized_rules,
    }


def _glob_matches(relative_path: str, pattern: str) -> bool:
    """glob 风格匹配，支持 ``**`` 表示跨目录通配。

    规则：
    - ``**/`` 表示零或多层目录（含末尾的 ``/``）；与 ``gitignore`` 的 ``**/``
      语义一致，因此 ``**/*.md`` 能命中 ``notes/first.md``。
    - 单独的 ``**`` 表示任意字符序列（含 ``/``）。
    - 单个 ``*`` 与 ``?`` 不跨 ``/``，与 ``fnmatch`` 一致。
    - 所有其它字符按字面匹配。
    """
    regex_parts: List[str] = []
    index = 0
    length = len(pattern)
    while index < length:
        if pattern.startswith("**/", index):
            regex_parts.append("(?:.*/)?")
            index += 3
        elif pattern.startswith("**", index):
            regex_parts.append(".*")
            index += 2
        elif pattern[index] == "*":
            regex_parts.append("[^/]*")
            index += 1
        elif pattern[index] == "?":
            regex_parts.append("[^/]")
            index += 1
        else:
            regex_parts.append(re.escape(pattern[index]))
            index += 1
    regex = "^" + "".join(regex_parts) + "$"
    return re.match(regex, relative_path) is not None


def apply_source_policy(
    records: Sequence[Dict[str, object]],
    policy: Dict[str, object],
) -> List[Dict[str, object]]:
    """按 ``policy['rules']`` 的 JSON 文件顺序对每条 record 求值，first match wins。

    - 命中规则后，``policy_class`` 被替换为规则 class。
    - 未命中的 eligible 文件保持 ``policy_class='unclassified'``；
      未命中的 ineligible 文件同样保持 ``policy_class='unclassified'``。
    - 返回新列表；不修改传入的 ``records``。
    """
    rules = policy.get("rules", [])  # type: ignore[assignment]
    applied: List[Dict[str, object]] = []
    for record in records:
        new_record = dict(record)
        relative_path = record["relative_path"]  # type: ignore[index]
        matched_class = None
        for rule in rules:
            globs = rule["globs"]  # type: ignore[index]
            if any(_glob_matches(relative_path, pattern) for pattern in globs):  # type: ignore[arg-type]
                matched_class = rule["class"]  # type: ignore[index]
                break
        if matched_class is None:
            new_record["policy_class"] = "unclassified"
        else:
            new_record["policy_class"] = matched_class
        applied.append(new_record)
    return applied


def _raise_walk_error(error: OSError) -> None:
    """把 os.walk 的异步错误转成不会被静默忽略的 inventory 错误。"""
    path = error.filename or "<unknown>"
    raise InventoryError(f"无法遍历目录: {path}: {error}")


SHA256_READ_CHUNK = 65_536


def _compute_sha256(path: Path) -> str:
    """读取文件全文并计算 SHA-256；读取失败时抛 InventoryError。

    读取失败以非零退出码结束，不静默跳过。
    """
    digest = hashlib.sha256()
    try:
        with path.open("rb") as source_file:
            while True:
                chunk = source_file.read(SHA256_READ_CHUNK)
                if not chunk:
                    break
                digest.update(chunk)
    except OSError as exc:
        raise InventoryError(f"无法读取文件: {path}: {exc}") from exc
    return digest.hexdigest()


def assign_duplicate_groups(records: Sequence[Dict[str, object]]) -> None:
    """按 SHA-256 给每条 record 分配 deterministic duplicate_group 与语义读取标记。

    契约：
    - 同一 ``sha256`` 的所有文件共享 ``duplicate_group``（群组标识 == sha256 本身）。
    - 每个非空 ``duplicate_group`` 以相对路径字典序最小的 eligible 文件作为
      ``representative``，其它成员标记 ``semantic_read=false``。
    - 没有重复的 eligible 文件 ``duplicate_group`` 仍为 sha256 字符串，
      ``semantic_read=true``（因为它就是自己的 representative）。
    - ineligible 文件共享 SHA 时同样被分组，但 ``semantic_read`` 保持原始
      ``eligible`` 值（ineligible 文件不应被语义读取，不计入 dup 统计）。
    - 直接修改传入 ``records`` 列表中每个 dict 的 ``duplicate_group`` 与
      ``semantic_read`` 字段。
    """
    for record in records:
        sha = record.get("sha256")
        if not isinstance(sha, str) or not sha:
            continue
        same_sha = [other for other in records if other.get("sha256") == sha]
        if len(same_sha) > 1:
            record["duplicate_group"] = sha
            eligible_members = sorted(
                other["relative_path"]
                for other in same_sha
                if other.get("eligible")
            )
            if eligible_members and record.get("eligible"):
                if record["relative_path"] == eligible_members[0]:
                    record["semantic_read"] = True
                else:
                    record["semantic_read"] = False
        else:
            record["duplicate_group"] = None


def count_duplicate_summary(
    records: Sequence[Dict[str, object]],
) -> Dict[str, int]:
    """从 records 汇总重复文件总数与重复组数。"""
    duplicates_total = 0
    seen_groups: set = set()
    duplicate_group_count = 0
    for record in records:
        sha = record.get("sha256")
        if not isinstance(sha, str) or not sha:
            continue
        group = record.get("duplicate_group")
        if not group:
            continue
        if sha not in seen_groups:
            seen_groups.add(sha)
            duplicate_group_count += 1
            same_sha = [other for other in records if other.get("sha256") == sha]
            duplicates_total += max(0, len(same_sha) - 1)
    return {
        "duplicate_files": duplicates_total,
        "duplicate_groups": duplicate_group_count,
    }


def inventory_local_corpus(
    source_root: Path,
    max_file_bytes: int = DEFAULT_MAX_FILE_BYTES,
) -> List[Dict[str, object]]:
    """遍历非隐藏常规文件并按 POSIX 相对路径返回基础记录。"""
    resolved_root = source_root.expanduser().resolve()
    records: List[Dict[str, object]] = []

    for current_root, directory_names, file_names in os.walk(
        resolved_root,
        topdown=True,
        onerror=_raise_walk_error,
        followlinks=False,
    ):
        current_path = Path(current_root)
        directory_names[:] = sorted(
            name
            for name in directory_names
            if not name.startswith(".")
            and not (current_path / name).is_symlink()
        )

        for file_name in sorted(file_names):
            if file_name.startswith("."):
                continue

            path = current_path / file_name
            try:
                file_stat = path.lstat()
            except OSError as exc:
                raise InventoryError(f"无法读取文件元数据: {path}: {exc}") from exc

            if stat.S_ISLNK(file_stat.st_mode) or not stat.S_ISREG(file_stat.st_mode):
                continue

            relative_path = path.relative_to(resolved_root)
            eligible, exclusion_reason, extension = determine_eligibility(
                path,
                file_stat.st_size,
                max_file_bytes,
            )
            sha256 = _compute_sha256(path)
            records.append(
                {
                    "relative_path": relative_path.as_posix(),
                    "extension": extension,
                    "size_bytes": file_stat.st_size,
                    "mtime": file_stat.st_mtime,
                    "top_level_family": top_level_family(relative_path),
                    "eligible": eligible,
                    "policy_class": "unclassified",
                    "exclusion_reason": exclusion_reason,
                    "sha256": sha256,
                    "duplicate_group": None,
                    "semantic_read": bool(eligible),
                }
            )

    records.sort(key=lambda record: record["relative_path"])
    assign_duplicate_groups(records)
    return records


def summarize_inventory(records: Sequence[Dict[str, object]]) -> Dict[str, int]:
    """汇总 check 模式需要的非语义计数。"""
    eligible_files = 0
    skipped_by_extension = 0
    oversized_files = 0
    binary_files = 0
    for record in records:
        if record.get("eligible") is True:
            eligible_files += 1
            continue
        reason = record.get("exclusion_reason")
        if reason == "unsupported_extension":
            skipped_by_extension += 1
        elif reason == "oversized":
            oversized_files += 1
        elif reason == "binary":
            binary_files += 1
    total_files = len(records)
    return {
        "total_files": total_files,
        "eligible_files": eligible_files,
        "ineligible_files": total_files - eligible_files,
        "skipped_by_extension": skipped_by_extension,
        "oversized_files": oversized_files,
        "binary_files": binary_files,
    }


def run(argv: Optional[Sequence[str]] = None) -> int:
    """执行 CLI；通过输入校验后只读盘点并输出元数据统计。"""
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        validate_inputs(args)
        source_root = args.source_root.expanduser().resolve()
        records = inventory_local_corpus(source_root, args.max_file_bytes)
    except (InputValidationError, InventoryError) as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 2

    policy: Optional[Dict[str, object]] = None
    if args.policy is not None:
        try:
            policy = load_source_policy(args.policy.expanduser().resolve(strict=False))
        except SourcePolicyError as exc:
            print(f"错误: {exc}", file=sys.stderr)
            return 2
        records = apply_source_policy(records, policy)

    summary = summarize_inventory(records)
    mode = "check" if args.check else "inventory"
    fields = " ".join(f"{key}={value}" for key, value in summary.items())
    print(
        f"mode={mode} source_root={source_root} "
        f"max_file_bytes={args.max_file_bytes} {fields}"
    )

    if not args.check and args.profile_dir is not None:
        try:
            write_manifest_and_review(
                profile_dir=args.profile_dir.expanduser().resolve(strict=False),
                records=records,
                source_root=source_root,
                summary=summary,
                max_file_bytes=args.max_file_bytes,
                policy=policy,
            )
        except (InputValidationError, InventoryError, OSError) as exc:
            print(f"错误: {exc}", file=sys.stderr)
            return 2

    return 0


def write_manifest_and_review(
    profile_dir: Path,
    records: Sequence[Dict[str, object]],
    source_root: Path,
    summary: Dict[str, int],
    max_file_bytes: int,
    policy: Optional[Dict[str, object]] = None,
) -> Dict[str, object]:
    """把 manifest 与 inventory review 写入 profile。

    行为契约：
    - ``policy`` 为 ``None`` 时：所有 eligible 文件保持
      ``policy_class="unclassified"``，并在 manifest 顶层用
      ``can_distill=False`` 阻塞后续语义阶段。
    - ``policy`` 非空时：传入的 ``records`` 必须已经按 first-match wins 求值，
      manifest 的 ``can_distill`` 仅在所有 eligible + 非 ``excluded`` 文件都进
      入 ``DISTILLABLE_POLICY_CLASSES`` 时才为 ``True``；否则保持 ``False``。
    - 只写入 ``references/source-manifest.json`` 与
      ``references/research/00-source-inventory.md``；绝不写入
      ``source-policy.json`` 或其他 profile 产物。
    - 绝不读取源文件正文；review 中只输出统计与 family 摘要。
    """
    if profile_dir.resolve(strict=False) == source_root:
        raise InputValidationError(
            "profile-dir 不得等于 source_root"
        )
    if is_within(profile_dir.resolve(strict=False), source_root):
        raise InputValidationError(
            "profile-dir 不得位于 source_root 内部"
        )

    references_dir = profile_dir / "references"
    research_dir = references_dir / INVENTORY_REVIEW_DIR
    research_dir.mkdir(parents=True, exist_ok=False)

    manifest_path = references_dir / MANIFEST_FILE_NAME
    review_path = research_dir / INVENTORY_REVIEW_FILE
    if manifest_path.exists() or review_path.exists():
        raise InventoryError(
            f"profile 目录已存在 inventory 产物: {profile_dir}"
        )

    manifest = _build_manifest(records, source_root, summary, max_file_bytes)
    _write_json(manifest_path, manifest)
    _write_inventory_review(review_path, manifest, summary)
    return manifest


def _build_manifest(
    records: Sequence[Dict[str, object]],
    source_root: Path,
    summary: Dict[str, int],
    max_file_bytes: int,
) -> Dict[str, object]:
    """构造 source manifest，保留稳定字段顺序。

    ``records`` 可以来自无 policy 场景（全部 ``policy_class="unclassified"``），
    也可以来自 ``apply_source_policy`` 之后的产物。manifest 的 ``can_distill``
    在且仅在**所有** eligible 文件都已经进入 ``DISTILLABLE_POLICY_CLASSES``
    （即不是 ``unclassified`` 且不是 ``excluded``）时为 ``True``。
    """
    file_entries: List[Dict[str, object]] = []
    for record in records:
        file_entries.append(
            {
                "relative_path": record["relative_path"],
                "extension": record["extension"],
                "size_bytes": record["size_bytes"],
                "mtime": record["mtime"],
                "top_level_family": record["top_level_family"],
                "eligible": record["eligible"],
                "policy_class": record["policy_class"],
                "exclusion_reason": record.get("exclusion_reason"),
                "sha256": record.get("sha256"),
                "duplicate_group": record.get("duplicate_group"),
                "semantic_read": record.get("semantic_read", record["eligible"]),
            }
        )

    unmatched_count = sum(
        1
        for entry in file_entries
        if entry["eligible"] and entry["policy_class"] == "unclassified"
    )
    distillable_count = sum(
        1
        for entry in file_entries
        if entry["eligible"] and entry["policy_class"] in DISTILLABLE_POLICY_CLASSES
    )
    can_distill = unmatched_count == 0 and distillable_count > 0

    return {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "generated_at": _datetime.datetime.now(tz=_datetime.timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z"),
        "source_root": str(source_root),
        "max_file_bytes": max_file_bytes,
        "can_distill": can_distill,
        "unmatched_count": unmatched_count,
        "summary": dict(summary),
        "files": file_entries,
    }


def _write_json(path: Path, payload: Dict[str, object]) -> None:
    """原子写入 JSON manifest，避免半截文件污染后续读入。"""
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False),
        encoding="utf-8",
    )
    os.replace(tmp_path, path)


def _write_inventory_review(
    path: Path,
    manifest: Dict[str, object],
    summary: Dict[str, int],
) -> None:
    """生成不含源文件正文、只含统计与 family 摘要的 inventory review。"""
    family_counts: Dict[str, int] = {}
    class_counts: Dict[str, int] = {}
    unmatched_paths: List[str] = []
    for entry in manifest["files"]:  # type: ignore[index]
        family = entry["top_level_family"]  # type: ignore[index]
        family_counts[family] = family_counts.get(family, 0) + 1
        class_name = entry["policy_class"]  # type: ignore[index]
        class_counts[class_name] = class_counts.get(class_name, 0) + 1
        if entry["eligible"] and class_name == "unclassified":  # type: ignore[index]
            unmatched_paths.append(entry["relative_path"])  # type: ignore[index]

    family_lines = "\n".join(
        f"- `{name}`: {count}" for name, count in sorted(family_counts.items())
    ) or "- (none)"
    class_lines = "\n".join(
        f"- `{name}`: {count}" for name, count in sorted(class_counts.items())
    ) or "- (none)"

    duplicate_summary = count_duplicate_summary(manifest["files"])  # type: ignore[arg-type]
    duplicate_section = [
        "## 重复文件",
        "",
        f"- duplicate_files: {duplicate_summary['duplicate_files']}",
        f"- duplicate_groups: {duplicate_summary['duplicate_groups']}",
        "- 注：相同 SHA-256 的文件归入同一 duplicate_group；"
        "相对路径字典序最小的 eligible 文件作为 representative，其它成员标记 "
        "`semantic_read=false`，不消耗阅读预算。",
        "",
    ]

    can_distill = manifest["can_distill"]  # type: ignore[index]
    status_note = (
        "- can_distill: True — 所有 eligible 文件均已分类，Nuwa 可进入六维研究。"
        if can_distill
        else "- can_distill: False — 仍存在 `unclassified` eligible 文件；"
        "Nuwa 必须补规则或请用户显式排除后重跑。"
    )

    unmatched_section = ["## 未匹配文件", ""]
    if unmatched_paths:
        unmatched_section.append(
            f"- 共 {len(unmatched_paths)} 个 eligible 文件保持 `unclassified`："
        )
        unmatched_section.extend(
            f"  - `{relative}`" for relative in unmatched_paths
        )
    else:
        unmatched_section.append("- (无)")
    unmatched_section.append("")

    lines = [
        "# Source Inventory Review",
        "",
        "> 由 `inventory_local_corpus.py` 自动生成；分类按 `source-policy.json` "
        "中的规则顺序求值（first-match wins），未匹配文件保持 `unclassified`。",
        "",
        "## 摘要",
        "",
        f"- source_root: `{manifest['source_root']}`",
        f"- generated_at: {manifest['generated_at']}",
        f"- can_distill: {can_distill}",
        f"- unmatched_count: {manifest['unmatched_count']}",
        f"- total_files: {summary['total_files']}",
        f"- eligible_files: {summary['eligible_files']}",
        f"- ineligible_files: {summary['ineligible_files']}",
        f"- skipped_by_extension: {summary['skipped_by_extension']}",
        f"- oversized_files: {summary['oversized_files']}",
        f"- binary_files: {summary['binary_files']}",
        status_note,
        "",
        "## top_level_family 计数",
        "",
        family_lines,
        "",
        "## policy_class 计数",
        "",
        class_lines,
        "",
        *duplicate_section,
        *unmatched_section,
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    sys.exit(run())


if __name__ == "__main__":
    main()
