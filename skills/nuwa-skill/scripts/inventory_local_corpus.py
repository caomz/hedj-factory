#!/usr/bin/env python3
"""盘点本地知识目录的 CLI 入口与输入路径防护。

本 story 只负责参数解析和写入边界校验；确定性遍历与 manifest 输出由后续
story 实现。

用法：
    python3 inventory_local_corpus.py SOURCE_ROOT --check
    python3 inventory_local_corpus.py SOURCE_ROOT --profile-dir PROFILE_DIR
"""

import argparse
import sys
from pathlib import Path
from typing import Optional, Sequence


DEFAULT_MAX_FILE_BYTES = 2_000_000


class InputValidationError(ValueError):
    """命令行输入不满足只读与输出路径约束。"""


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


def run(argv: Optional[Sequence[str]] = None) -> int:
    """执行 CLI；所有输入通过后才允许后续 story 接入盘点逻辑。"""
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        validate_inputs(args)
    except InputValidationError as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 2

    mode = "check" if args.check else "inventory"
    print(
        f"mode={mode} source_root={args.source_root.expanduser().resolve()} "
        f"max_file_bytes={args.max_file_bytes}"
    )
    return 0


def main() -> None:
    sys.exit(run())


if __name__ == "__main__":
    main()
