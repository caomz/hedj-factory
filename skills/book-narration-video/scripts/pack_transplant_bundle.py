#!/usr/bin/env python3
"""Pack book-extract transplant bundle for selective copy into a state-machine repo.

Copies only the hardened extractor files into --out. Never deletes directories
(no rm -rf / no TemporaryDirectory.cleanup). If --out exists and is non-empty,
refuses unless --force (then overwrites individual files via copy2 only).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPTS.parent

# Paths relative to skill root
BUNDLE_FILES = [
    "scripts/extract_book.py",
    "scripts/extract_book.sh",
    "scripts/make_fixtures.py",
    "scripts/test_extract_book.py",
    "scripts/smoke_test.sh",
    "references/transplant-to-state-machine.md",
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(
        description="打包可选择性移植的 extract_book 文件（不删目录）")
    ap.add_argument("--out", type=Path, required=True,
                    help="输出目录（建议新建空目录）")
    ap.add_argument("--force", action="store_true",
                    help="允许覆盖 --out 内已存在的同名文件")
    ap.add_argument("--dry-run", action="store_true",
                    help="只列出将复制的文件，不落盘")
    args = ap.parse_args()

    missing = [rel for rel in BUNDLE_FILES if not (SKILL_ROOT / rel).is_file()]
    if missing:
        print("❌ 缺少文件：", ", ".join(missing), file=sys.stderr)
        return 1

    out: Path = args.out.expanduser().resolve()
    if out.exists():
        if not out.is_dir():
            print(f"❌ --out 已存在且不是目录：{out}", file=sys.stderr)
            return 1
        existing = [p for p in out.rglob("*") if p.is_file()]
        if existing and not args.force and not args.dry_run:
            print(f"❌ --out 非空（{len(existing)} 个文件）。换空目录或加 --force。",
                  file=sys.stderr)
            return 1
    elif not args.dry_run:
        out.mkdir(parents=True, exist_ok=True)

    manifest = {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_skill_root": str(SKILL_ROOT),
        "note": "Selective transplant bundle. Do not overwrite local state-machine SKILL.md.",
        "files": [],
    }

    for rel in BUNDLE_FILES:
        src = SKILL_ROOT / rel
        dst = out / rel
        digest = sha256_file(src)
        entry = {"path": rel, "sha256": digest, "bytes": src.stat().st_size}
        manifest["files"].append(entry)
        print(f"{'[dry-run] ' if args.dry_run else ''}{rel}  sha256={digest[:16]}…")
        if args.dry_run:
            continue
        if dst.exists() and not args.force:
            print(f"❌ 已存在：{dst}（加 --force 覆盖单文件）", file=sys.stderr)
            return 1
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

    man_path = out / "TRANSPLANT_MANIFEST.json"
    text = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    if args.dry_run:
        print(f"[dry-run] 将写入 {man_path.name}（{len(manifest['files'])} files）")
        return 0
    man_path.write_text(text, encoding="utf-8")
    print(f"✅ bundle → {out}")
    print(f"   manifest → {man_path}")
    print("   下一步：把 scripts/ 拷进本地状态机 skill；读 references/transplant-to-state-machine.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
