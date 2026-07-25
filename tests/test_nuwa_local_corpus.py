"""Nuwa 本地知识目录 inventory 的标准库测试。"""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "skills" / "nuwa-skill" / "scripts" / "inventory_local_corpus.py"


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


if __name__ == "__main__":
    unittest.main()
