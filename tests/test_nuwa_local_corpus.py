"""Nuwa 本地知识目录 inventory 的标准库测试。"""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "skills" / "nuwa-skill" / "scripts" / "inventory_local_corpus.py"
sys.path.insert(0, str(SCRIPT.parent))
from inventory_local_corpus import inventory_local_corpus, summarize_inventory


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


if __name__ == "__main__":
    unittest.main()
