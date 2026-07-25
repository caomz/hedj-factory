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
import json
import os
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


class InputValidationError(ValueError):
    """命令行输入不满足只读与输出路径约束。"""


class InventoryError(RuntimeError):
    """源目录无法被完整、确定地盘点。"""


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


def _raise_walk_error(error: OSError) -> None:
    """把 os.walk 的异步错误转成不会被静默忽略的 inventory 错误。"""
    path = error.filename or "<unknown>"
    raise InventoryError(f"无法遍历目录: {path}: {error}")


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
                }
            )

    records.sort(key=lambda record: record["relative_path"])
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

    summary = summarize_inventory(records)
    mode = "check" if args.check else "inventory"
    fields = " ".join(f"{key}={value}" for key, value in summary.items())
    print(
        f"mode={mode} source_root={source_root} "
        f"max_file_bytes={args.max_file_bytes} {fields}"
    )

    if not args.check and args.policy is None and args.profile_dir is not None:
        try:
            write_manifest_and_review(
                profile_dir=args.profile_dir.expanduser().resolve(strict=False),
                records=records,
                source_root=source_root,
                summary=summary,
                max_file_bytes=args.max_file_bytes,
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
) -> None:
    """在无 policy 场景下把 manifest 与 inventory review 写入 profile。

    行为契约：
    - 所有 eligible 文件保持 ``policy_class="unclassified"``，并在 manifest
      顶层用 ``can_distill=False`` 阻塞后续语义阶段。
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


def _build_manifest(
    records: Sequence[Dict[str, object]],
    source_root: Path,
    summary: Dict[str, int],
    max_file_bytes: int,
) -> Dict[str, object]:
    """构造无 policy 场景的 source manifest，保留稳定字段顺序。"""
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
                "policy_class": "unclassified",
                "exclusion_reason": record.get("exclusion_reason"),
            }
        )

    unmatched_count = sum(
        1
        for entry in file_entries
        if entry["eligible"] and entry["policy_class"] == "unclassified"
    )
    return {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "generated_at": _datetime.datetime.now(tz=_datetime.timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z"),
        "source_root": str(source_root),
        "max_file_bytes": max_file_bytes,
        "can_distill": False,
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
    for entry in manifest["files"]:  # type: ignore[index]
        family = entry["top_level_family"]  # type: ignore[index]
        family_counts[family] = family_counts.get(family, 0) + 1

    family_lines = "\n".join(
        f"- `{name}`: {count}" for name, count in sorted(family_counts.items())
    ) or "- (none)"

    lines = [
        "# Source Inventory Review",
        "",
        "> 由 `inventory_local_corpus.py` 自动生成；所有文件 policy_class",
        "> 均为 `unclassified`，Nuwa 必须在用户确认 policy 后才能进入语义阶段。",
        "",
        "## 摘要",
        "",
        f"- source_root: `{manifest['source_root']}`",
        f"- generated_at: {manifest['generated_at']}",
        f"- can_distill: {manifest['can_distill']}",
        f"- unmatched_count: {manifest['unmatched_count']}",
        f"- total_files: {summary['total_files']}",
        f"- eligible_files: {summary['eligible_files']}",
        f"- ineligible_files: {summary['ineligible_files']}",
        f"- skipped_by_extension: {summary['skipped_by_extension']}",
        f"- oversized_files: {summary['oversized_files']}",
        f"- binary_files: {summary['binary_files']}",
        "",
        "## top_level_family 计数",
        "",
        family_lines,
        "",
        "## 未匹配文件",
        "",
        f"- 共 {manifest['unmatched_count']} 个 eligible 文件保持 `unclassified`；",
        "  Nuwa 必须在 Checkpoint A 提出 `source-policy.json` 草稿并经用户逐条确认。",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    sys.exit(run())


if __name__ == "__main__":
    main()
