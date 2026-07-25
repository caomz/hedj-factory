"""Nuwa 本地知识目录 inventory 的标准库测试。"""

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "skills" / "nuwa-skill" / "scripts" / "inventory_local_corpus.py"
sys.path.insert(0, str(SCRIPT.parent))
from inventory_local_corpus import (
    inventory_local_corpus,
    summarize_inventory,
    write_manifest_and_review,
)


class LocalCorpusInputValidationTests(unittest.TestCase):
    """覆盖 US-003 的参数与路径防护。"""

    def run_cli(self, *args: object) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *(str(arg) for arg in args)],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_missing_source_root_reports_exact_path(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            missing = Path(temp_dir) / "missing-corpus"
            result = self.run_cli(missing, "--check")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(str(missing), result.stderr)
        self.assertIn("source_root 不存在", result.stderr)

    def test_file_source_root_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            source_file = Path(temp_dir) / "notes.md"
            source_file.write_text("synthetic", encoding="utf-8")
            result = self.run_cli(source_file, "--check")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(str(source_file), result.stderr)
        self.assertIn("source_root 不是目录", result.stderr)

    def test_inventory_requires_profile_dir(self):
        with tempfile.TemporaryDirectory() as source_dir:
            result = self.run_cli(source_dir)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("必须提供 --profile-dir", result.stderr)

    def test_profile_dir_inside_source_root_is_rejected_without_writes(self):
        with tempfile.TemporaryDirectory() as source_dir:
            source_root = Path(source_dir)
            profile_dir = source_root / "generated-profile"
            result = self.run_cli(source_root, "--profile-dir", profile_dir)

            self.assertFalse(profile_dir.exists())

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(str(profile_dir), result.stderr)
        self.assertIn("不得位于 source_root 内部", result.stderr)

    def test_check_allows_missing_profile_dir_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as source_dir:
            source_root = Path(source_dir)
            note = source_root / "note.md"
            note.write_text("synthetic note", encoding="utf-8")
            before = sorted(path.relative_to(source_root) for path in source_root.rglob("*"))

            result = self.run_cli(source_root, "--check")

            after = sorted(path.relative_to(source_root) for path in source_root.rglob("*"))

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(before, after)
        self.assertIn("mode=check", result.stdout)
        self.assertIn("max_file_bytes=2000000", result.stdout)

    def test_cli_accepts_policy_and_custom_max_file_bytes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source_root = root / "corpus"
            source_root.mkdir()
            policy = root / "source-policy.json"
            result = self.run_cli(
                source_root,
                "--check",
                "--policy",
                policy,
                "--max-file-bytes",
                "1234",
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("max_file_bytes=1234", result.stdout)


class LocalCorpusTraversalTests(unittest.TestCase):
    """覆盖 US-004 的确定性遍历与文件资格判定。"""

    def test_records_are_sorted_and_include_required_metadata(self):
        with tempfile.TemporaryDirectory() as source_dir:
            source_root = Path(source_dir)
            (source_root / "z-family").mkdir()
            (source_root / "a-family").mkdir()
            (source_root / "z-family" / "later.TXT").write_text(
                "later", encoding="utf-8"
            )
            (source_root / "root.md").write_text("root", encoding="utf-8")
            (source_root / "a-family" / "first.json").write_text(
                '{"synthetic": true}', encoding="utf-8"
            )

            records = inventory_local_corpus(source_root)

        self.assertEqual(
            [record["relative_path"] for record in records],
            ["a-family/first.json", "root.md", "z-family/later.TXT"],
        )
        self.assertEqual(records[0]["top_level_family"], "a-family")
        self.assertEqual(records[1]["top_level_family"], ".")
        self.assertEqual(records[2]["extension"], ".txt")
        self.assertTrue(records[0]["eligible"])
        self.assertEqual(records[0]["policy_class"], "unclassified")
        self.assertIsNone(records[0]["exclusion_reason"])
        self.assertIsInstance(records[0]["size_bytes"], int)
        self.assertIsInstance(records[0]["mtime"], float)
        self.assertEqual(
            set(records[0]),
            {
                "relative_path",
                "extension",
                "size_bytes",
                "mtime",
                "top_level_family",
                "eligible",
                "policy_class",
                "exclusion_reason",
            },
        )

    def test_hidden_entries_and_symlinks_are_skipped(self):
        with tempfile.TemporaryDirectory() as source_dir:
            source_root = Path(source_dir)
            (source_root / "visible.md").write_text("visible", encoding="utf-8")
            (source_root / ".hidden.md").write_text("hidden", encoding="utf-8")
            hidden_dir = source_root / ".hidden"
            hidden_dir.mkdir()
            (hidden_dir / "nested.md").write_text("hidden", encoding="utf-8")
            target_dir = source_root / "target"
            target_dir.mkdir()
            (target_dir / "real.md").write_text("real", encoding="utf-8")
            (source_root / "linked-file.md").symlink_to(target_dir / "real.md")
            (source_root / "linked-dir").symlink_to(target_dir, target_is_directory=True)

            records = inventory_local_corpus(source_root)

        self.assertEqual(
            [record["relative_path"] for record in records],
            ["target/real.md", "visible.md"],
        )

    def test_supported_extensions_are_eligible_without_semantic_fields(self):
        extensions = (
            ".md",
            ".markdown",
            ".txt",
            ".json",
            ".jsonl",
            ".html",
            ".htm",
            ".yaml",
            ".yml",
            ".csv",
        )
        with tempfile.TemporaryDirectory() as source_dir:
            source_root = Path(source_dir)
            for index, extension in enumerate(extensions):
                (source_root / f"note-{index}{extension}").write_text(
                    "synthetic text", encoding="utf-8"
                )

            records = inventory_local_corpus(source_root)

        self.assertEqual(len(records), len(extensions))
        self.assertTrue(all(record["eligible"] for record in records))
        self.assertFalse(
            any(
                semantic_field in record
                for record in records
                for semantic_field in ("title", "summary", "content", "chat_content")
            )
        )

    def test_unsupported_and_binary_files_are_counted_but_ineligible(self):
        with tempfile.TemporaryDirectory() as source_dir:
            source_root = Path(source_dir)
            (source_root / "photo.png").write_bytes(b"\x89PNG\x00synthetic")
            (source_root / "database.sqlite").write_bytes(b"SQLite format 3\x00")
            (source_root / "binary.txt").write_bytes(b"before\x00after")

            records = inventory_local_corpus(source_root)
            summary = summarize_inventory(records)

        by_path = {record["relative_path"]: record for record in records}
        self.assertEqual(summary["total_files"], 3)
        self.assertEqual(summary["eligible_files"], 0)
        self.assertEqual(summary["skipped_by_extension"], 2)
        self.assertEqual(summary["binary_files"], 1)
        self.assertEqual(
            by_path["photo.png"]["exclusion_reason"], "unsupported_extension"
        )
        self.assertEqual(by_path["binary.txt"]["exclusion_reason"], "binary")

    def test_oversized_file_has_stable_exclusion_reason(self):
        with tempfile.TemporaryDirectory() as source_dir:
            source_root = Path(source_dir)
            (source_root / "large.md").write_text("x" * 11, encoding="utf-8")

            records = inventory_local_corpus(source_root, max_file_bytes=10)

        self.assertEqual(len(records), 1)
        self.assertFalse(records[0]["eligible"])
        self.assertEqual(records[0]["exclusion_reason"], "oversized")


class LocalCorpusOutputTests(unittest.TestCase):
    """覆盖 US-005 的 manifest / review 写入。"""

    @staticmethod
    def _hash_tree(root: Path) -> dict:
        payload: dict = {}
        for path in sorted(root.rglob("*")):
            if path.is_file():
                payload[path.relative_to(root).as_posix()] = (
                    hashlib.sha256(path.read_bytes()).hexdigest()
                )
        return payload

    def test_no_policy_writes_manifest_and_review(self):
        work_dir = Path(tempfile.mkdtemp(prefix="nuwa_us005_"))
        try:
            source_root = work_dir / "corpus"
            source_root.mkdir()
            (source_root / "notes").mkdir()
            (source_root / "notes" / "first.md").write_text(
                "first synthetic note", encoding="utf-8"
            )
            (source_root / "notes" / "second.txt").write_text(
                "second synthetic note", encoding="utf-8"
            )
            (source_root / "photo.png").write_bytes(b"\x89PNG\x00synthetic")
            (source_root / "root.md").write_text("root", encoding="utf-8")

            profile_dir = work_dir / "profile"
            before_hash = self._hash_tree(source_root)

            records = inventory_local_corpus(source_root)
            summary = summarize_inventory(records)
            write_manifest_and_review(
                profile_dir, records, source_root, summary, 2_000_000
            )

            after_hash = self._hash_tree(source_root)

            manifest_path = profile_dir / "references" / "source-manifest.json"
            review_path = (
                profile_dir / "references" / "research" / "00-source-inventory.md"
            )
            self.assertTrue(manifest_path.is_file())
            self.assertTrue(review_path.is_file())

            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["schema_version"], 1)
            self.assertFalse(manifest["can_distill"])
            self.assertEqual(manifest["max_file_bytes"], 2_000_000)
            self.assertEqual(manifest["source_root"], str(source_root.resolve()))
            self.assertTrue(manifest["generated_at"].endswith("Z"))
            self.assertGreaterEqual(manifest["unmatched_count"], 1)
            self.assertEqual(manifest["summary"]["total_files"], 4)
            self.assertEqual(manifest["summary"]["eligible_files"], 3)
            self.assertEqual(manifest["summary"]["skipped_by_extension"], 1)

            entries = manifest["files"]
            self.assertEqual(len(entries), 4)
            self.assertTrue(
                all(entry["policy_class"] == "unclassified" for entry in entries)
            )
            eligible_entries = [
                entry
                for entry in entries
                if entry["eligible"] and entry["policy_class"] == "unclassified"
            ]
            self.assertEqual(
                len(eligible_entries), manifest["unmatched_count"]
            )
            for entry in entries:
                self.assertEqual(
                    set(entry),
                    {
                        "relative_path",
                        "extension",
                        "size_bytes",
                        "mtime",
                        "top_level_family",
                        "eligible",
                        "policy_class",
                        "exclusion_reason",
                    },
                )

            review_text = review_path.read_text(encoding="utf-8")
            self.assertIn("# Source Inventory Review", review_text)
            self.assertIn("can_distill: False", review_text)
            self.assertIn("`notes`", review_text)
            for needle in (
                "first synthetic note",
                "second synthetic note",
                "synthetic text",
            ):
                self.assertNotIn(needle, review_text)
            self.assertFalse((profile_dir / "source-policy.json").exists())
            self.assertEqual(before_hash, after_hash)
        finally:
            shutil.rmtree(work_dir, ignore_errors=True)

    def test_no_policy_with_existing_profile_is_rejected_without_overwrite(self):
        work_dir = Path(tempfile.mkdtemp(prefix="nuwa_us005_"))
        try:
            source_root = work_dir / "corpus"
            source_root.mkdir()
            (source_root / "a.md").write_text("a", encoding="utf-8")

            profile_dir = work_dir / "profile"
            existing_manifest = profile_dir / "references" / "source-manifest.json"
            existing_manifest.parent.mkdir(parents=True)
            existing_manifest.write_text('{"legacy": true}', encoding="utf-8")
            legacy_content = existing_manifest.read_text(encoding="utf-8")

            records = inventory_local_corpus(source_root)
            summary = summarize_inventory(records)
            with self.assertRaises(Exception) as raised:
                write_manifest_and_review(
                    profile_dir, records, source_root, summary, 2_000_000
                )

            preserved_content = existing_manifest.read_text(encoding="utf-8")
        finally:
            shutil.rmtree(work_dir, ignore_errors=True)

        self.assertIn("已存在 inventory 产物", str(raised.exception))
        self.assertEqual(preserved_content, legacy_content)

if __name__ == "__main__":
    unittest.main()
