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
    apply_source_policy,
    assign_duplicate_groups,
    count_duplicate_summary,
    inventory_local_corpus,
    load_source_policy,
    summarize_inventory,
    write_manifest_and_review,
    _compute_sha256,
    assign_version_groups,
    count_version_summary,
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
            policy.write_text(
                '{"schema_version": 1, "rules": [{"class": "authored", "globs": ["**/*.md"]}]}',
                encoding="utf-8",
            )
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
                "sha256",
                "duplicate_group",
                "semantic_read",
                "version_group",
                "current_version",
                "evolution_only",
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
                        "sha256",
                        "duplicate_group",
                        "semantic_read",
                        "version_group",
                        "current_version",
                        "evolution_only",
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


class SourcePolicyTests(unittest.TestCase):
    """覆盖 US-006：source policy schema、first-match、can_distill 与失败保护。"""

    @staticmethod
    def _seed_corpus(root: Path) -> None:
        (root / "notes").mkdir()
        (root / "notes" / "first.md").write_text("first note", encoding="utf-8")
        (root / "notes" / "second.txt").write_text("second note", encoding="utf-8")
        (root / "external").mkdir()
        (root / "external" / "blog.md").write_text("external blog", encoding="utf-8")
        (root / "credentials.txt").write_text("wxid_fake_secret", encoding="utf-8")

    @staticmethod
    def _hash_tree(root: Path) -> dict:
        payload: dict = {}
        for path in sorted(root.rglob("*")):
            if path.is_file():
                payload[path.relative_to(root).as_posix()] = (
                    hashlib.sha256(path.read_bytes()).hexdigest()
                )
        return payload

    def test_first_match_wins_and_unmatched_stays_unclassified(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            work_dir = Path(temp_dir)
            source_root = work_dir / "corpus"
            source_root.mkdir()
            self._seed_corpus(source_root)

            policy_path = work_dir / "source-policy.json"
            policy_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "rules": [
                            {
                                "class": "authored",
                                "globs": ["notes/**/*.md", "notes/**/*.txt"],
                            },
                            {"class": "external", "globs": ["external/**/*"]},
                        ],
                    }
                ),
                encoding="utf-8",
            )

            loaded = load_source_policy(policy_path)
            self.assertEqual(loaded["schema_version"], 1)
            records = inventory_local_corpus(source_root)
            applied = apply_source_policy(records, loaded)
            by_path = {entry["relative_path"]: entry for entry in applied}

            self.assertEqual(
                by_path["notes/first.md"]["policy_class"], "authored"
            )
            self.assertEqual(
                by_path["notes/second.txt"]["policy_class"], "authored"
            )
            self.assertEqual(
                by_path["external/blog.md"]["policy_class"], "external"
            )
            self.assertEqual(
                by_path["credentials.txt"]["policy_class"], "unclassified"
            )

            summary = summarize_inventory(applied)
            manifest_payload = write_manifest_and_review(
                profile_dir=work_dir / "profile",
                records=applied,
                source_root=source_root,
                summary=summary,
                max_file_bytes=2_000_000,
                policy=loaded,
            )

        self.assertFalse(manifest_payload["can_distill"])
        self.assertEqual(manifest_payload["unmatched_count"], 1)

    def test_full_policy_sets_can_distill_true_and_excluded_does_not_block(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            work_dir = Path(temp_dir)
            source_root = work_dir / "corpus"
            source_root.mkdir()
            self._seed_corpus(source_root)
            (source_root / "tokens").mkdir()
            (source_root / "tokens" / "secret.bin").write_bytes(b"\x00bad")

            policy_path = work_dir / "source-policy.json"
            policy_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "rules": [
                            {
                                "class": "authored",
                                "globs": ["notes/**/*.md", "notes/**/*.txt"],
                            },
                            {"class": "external", "globs": ["external/**/*"]},
                            {
                                "class": "excluded",
                                "globs": ["credentials.txt", "tokens/**/*"],
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )

            loaded = load_source_policy(policy_path)
            records = inventory_local_corpus(source_root)
            applied = apply_source_policy(records, loaded)
            summary = summarize_inventory(applied)
            manifest_payload = write_manifest_and_review(
                profile_dir=work_dir / "profile",
                records=applied,
                source_root=source_root,
                summary=summary,
                max_file_bytes=2_000_000,
                policy=loaded,
            )

        self.assertTrue(manifest_payload["can_distill"])
        self.assertEqual(manifest_payload["unmatched_count"], 0)
        by_path = {entry["relative_path"]: entry for entry in manifest_payload["files"]}
        self.assertEqual(by_path["credentials.txt"]["policy_class"], "excluded")
        self.assertEqual(by_path["tokens/secret.bin"]["policy_class"], "excluded")

    def test_invalid_json_rejected_and_does_not_overwrite_manifest(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            work_dir = Path(temp_dir)
            source_root = work_dir / "corpus"
            source_root.mkdir()
            self._seed_corpus(source_root)
            profile_dir = work_dir / "profile"

            existing_manifest = profile_dir / "references" / "source-manifest.json"
            existing_manifest.parent.mkdir(parents=True)
            existing_manifest.write_text(
                '{"legacy": true, "can_distill": false}', encoding="utf-8"
            )
            legacy_content = existing_manifest.read_text(encoding="utf-8")

            policy_path = work_dir / "source-policy.json"
            policy_path.write_text("{ this is not json", encoding="utf-8")

            with self.assertRaises(Exception) as raised:
                load_source_policy(policy_path)

            preserved = existing_manifest.read_text(encoding="utf-8")
            self.assertFalse((profile_dir / "references" / "research").exists())

        self.assertIn("合法 JSON", str(raised.exception))
        self.assertEqual(preserved, legacy_content)

    def test_invalid_class_rejected_with_clear_message(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            work_dir = Path(temp_dir)
            policy_path = work_dir / "source-policy.json"
            policy_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "rules": [
                            {"class": "bogus", "globs": ["**/*.md"]},
                        ],
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaises(Exception) as raised:
                load_source_policy(policy_path)

        self.assertIn("rules[0].class", str(raised.exception))

    def test_empty_globs_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            work_dir = Path(temp_dir)
            policy_path = work_dir / "source-policy.json"
            policy_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "rules": [{"class": "authored", "globs": []}],
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaises(Exception) as raised:
                load_source_policy(policy_path)

        self.assertIn("globs 必须为非空", str(raised.exception))

    def test_invalid_policy_rejected_by_cli_without_overwrite(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            work_dir = Path(temp_dir)
            source_root = work_dir / "corpus"
            source_root.mkdir()
            self._seed_corpus(source_root)
            profile_dir = work_dir / "profile"
            existing_manifest = profile_dir / "references" / "source-manifest.json"
            existing_manifest.parent.mkdir(parents=True)
            existing_manifest.write_text(
                '{"legacy": true}', encoding="utf-8"
            )
            legacy_content = existing_manifest.read_text(encoding="utf-8")

            policy_path = work_dir / "source-policy.json"
            policy_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "rules": [{"class": "nope", "globs": ["**/*"]}],
                    }
                ),
                encoding="utf-8",
            )

            before_hash = self._hash_tree(source_root)
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    str(source_root),
                    "--profile-dir",
                    str(profile_dir),
                    "--policy",
                    str(policy_path),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            after_hash = self._hash_tree(source_root)
            preserved = existing_manifest.read_text(encoding="utf-8")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("rules[0].class", result.stderr)
        self.assertEqual(before_hash, after_hash)
        self.assertEqual(preserved, legacy_content)

    def test_review_includes_class_counts_and_unmatched_paths(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            work_dir = Path(temp_dir)
            source_root = work_dir / "corpus"
            source_root.mkdir()
            self._seed_corpus(source_root)

            policy_path = work_dir / "source-policy.json"
            policy_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "rules": [
                            {
                                "class": "authored",
                                "globs": ["notes/**/*.md"],
                            },
                            {"class": "external", "globs": ["external/**/*"]},
                        ],
                    }
                ),
                encoding="utf-8",
            )

            loaded = load_source_policy(policy_path)
            records = inventory_local_corpus(source_root)
            applied = apply_source_policy(records, loaded)
            summary = summarize_inventory(applied)
            profile_dir = work_dir / "profile"
            write_manifest_and_review(
                profile_dir=profile_dir,
                records=applied,
                source_root=source_root,
                summary=summary,
                max_file_bytes=2_000_000,
                policy=loaded,
            )

            review_text = (
                profile_dir / "references" / "research" / "00-source-inventory.md"
            ).read_text(encoding="utf-8")

        self.assertIn("## policy_class 计数", review_text)
        self.assertIn("`authored`", review_text)
        self.assertIn("`external`", review_text)
        self.assertIn("`unclassified`", review_text)
        self.assertIn("`credentials.txt`", review_text)
        self.assertIn("can_distill: False", review_text)

class DuplicateDetectionTests(unittest.TestCase):
    """覆盖 US-007：SHA-256 重复分组、representative 选取与失败保护。"""

    @staticmethod
    def _hash_tree(root: Path) -> dict:
        payload: dict = {}
        for path in sorted(root.rglob("*")):
            if path.is_file() and not path.is_symlink():
                payload[path.relative_to(root).as_posix()] = (
                    hashlib.sha256(path.read_bytes()).hexdigest()
                )
        return payload

    def test_exact_duplicates_share_group_with_lowest_representative(self):
        with tempfile.TemporaryDirectory() as source_dir:
            source_root = Path(source_dir)
            note = "exact duplicate content"
            (source_root / "zeta.md").write_text(note, encoding="utf-8")
            (source_root / "alpha.md").write_text(note, encoding="utf-8")
            (source_root / "mid.md").write_text(note, encoding="utf-8")
            (source_root / "unique.md").write_text("unique text", encoding="utf-8")

            records = inventory_local_corpus(source_root)

        by_path = {record["relative_path"]: record for record in records}
        expected_sha = hashlib.sha256(note.encode("utf-8")).hexdigest()

        self.assertEqual(by_path["alpha.md"]["sha256"], expected_sha)
        self.assertEqual(by_path["zeta.md"]["sha256"], expected_sha)
        self.assertEqual(by_path["mid.md"]["sha256"], expected_sha)
        self.assertNotEqual(by_path["unique.md"]["sha256"], expected_sha)

        self.assertEqual(by_path["alpha.md"]["duplicate_group"], expected_sha)
        self.assertEqual(by_path["zeta.md"]["duplicate_group"], expected_sha)
        self.assertEqual(by_path["mid.md"]["duplicate_group"], expected_sha)
        self.assertIsNone(by_path["unique.md"]["duplicate_group"])

        self.assertTrue(by_path["alpha.md"]["semantic_read"])
        self.assertFalse(by_path["zeta.md"]["semantic_read"])
        self.assertFalse(by_path["mid.md"]["semantic_read"])
        self.assertTrue(by_path["unique.md"]["semantic_read"])

        summary = count_duplicate_summary(records)
        self.assertEqual(summary["duplicate_files"], 2)
        self.assertEqual(summary["duplicate_groups"], 1)

    def test_duplicate_group_is_deterministic_after_sorting(self):
        with tempfile.TemporaryDirectory() as source_dir:
            source_root = Path(source_dir)
            payload = "identical content"
            (source_root / "b.md").write_text(payload, encoding="utf-8")
            (source_root / "a.md").write_text(payload, encoding="utf-8")

            records = inventory_local_corpus(source_root)

        sha = records[0]["sha256"]
        self.assertEqual(records[0]["relative_path"], "a.md")
        self.assertEqual(records[0]["duplicate_group"], sha)
        self.assertTrue(records[0]["semantic_read"])
        self.assertEqual(records[1]["relative_path"], "b.md")
        self.assertEqual(records[1]["duplicate_group"], sha)
        self.assertFalse(records[1]["semantic_read"])

    def test_sha256_is_computed_for_every_regular_file(self):
        with tempfile.TemporaryDirectory() as source_dir:
            source_root = Path(source_dir)
            (source_root / "a.md").write_text("hello", encoding="utf-8")
            (source_root / "b.txt").write_text("world", encoding="utf-8")

            records = inventory_local_corpus(source_root)
            for record in records:
                self.assertEqual(len(record["sha256"]), 64)
                self.assertEqual(
                    record["sha256"],
                    hashlib.sha256(
                        (source_root / record["relative_path"]).read_bytes()
                    ).hexdigest(),
                )

    def test_sha256_read_failure_raises_inventory_error(self):
        with tempfile.TemporaryDirectory() as source_dir:
            source_root = Path(source_dir)
            target = source_root / "note.md"
            target.write_text("payload", encoding="utf-8")
            target.chmod(0)
            try:
                with self.assertRaises(Exception) as raised:
                    inventory_local_corpus(source_root)
            finally:
                target.chmod(0o644)

        self.assertIn("无法读取文件", str(raised.exception))
        self.assertIn("note.md", str(raised.exception))

    def test_review_includes_duplicate_counts_without_source_bodies(self):
        work_dir = Path(tempfile.mkdtemp(prefix="nuwa_us007_"))
        try:
            source_root = work_dir / "corpus"
            source_root.mkdir()
            payload = "duplicate body"
            (source_root / "first.md").write_text(payload, encoding="utf-8")
            (source_root / "second.md").write_text(payload, encoding="utf-8")
            (source_root / "third.md").write_text(payload, encoding="utf-8")
            (source_root / "unique.md").write_text("unique body", encoding="utf-8")

            profile_dir = work_dir / "profile"
            records = inventory_local_corpus(source_root)
            summary = summarize_inventory(records)
            write_manifest_and_review(
                profile_dir, records, source_root, summary, 2_000_000
            )

            review_text = (
                profile_dir / "references" / "research" / "00-source-inventory.md"
            ).read_text(encoding="utf-8")
        finally:
            shutil.rmtree(work_dir, ignore_errors=True)

        self.assertIn("## 重复文件", review_text)
        self.assertIn("duplicate_files: 2", review_text)
        self.assertIn("duplicate_groups: 1", review_text)
        for needle in ("duplicate body", "unique body"):
            self.assertNotIn(needle, review_text)

    def test_duplicate_group_survives_apply_source_policy(self):
        with tempfile.TemporaryDirectory() as source_dir:
            source_root = Path(source_dir)
            payload = "shared payload"
            (source_root / "z.md").write_text(payload, encoding="utf-8")
            (source_root / "a.md").write_text(payload, encoding="utf-8")
            (source_root / "other.md").write_text("different", encoding="utf-8")

            policy_payload = {
                "schema_version": 1,
                "rules": [{"class": "authored", "globs": ["**/*.md"]}],
            }
            policy_path = Path(source_dir) / "source-policy.json"
            policy_path.write_text(
                json.dumps(policy_payload), encoding="utf-8"
            )

            records = inventory_local_corpus(source_root)
            loaded = load_source_policy(policy_path)
            applied = apply_source_policy(records, loaded)

        by_path = {record["relative_path"]: record for record in applied}
        self.assertEqual(
            by_path["a.md"]["duplicate_group"], by_path["z.md"]["duplicate_group"]
        )
        self.assertEqual(by_path["a.md"]["policy_class"], "authored")
        self.assertEqual(by_path["z.md"]["policy_class"], "authored")
        self.assertTrue(by_path["a.md"]["semantic_read"])
        self.assertFalse(by_path["z.md"]["semantic_read"])
        self.assertIsNone(by_path["other.md"]["duplicate_group"])

    def test_compute_sha256_directly_for_small_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            note = Path(temp_dir) / "tiny.md"
            note.write_text("tiny", encoding="utf-8")
            expected = hashlib.sha256(b"tiny").hexdigest()
            actual = _compute_sha256(note)

        self.assertEqual(actual, expected)


class VersionSelectionTests(unittest.TestCase):
    """覆盖 US-008：版本序列 current_version 判定。"""

    def test_version_groups_pick_highest_tuple_as_current(self):
        with tempfile.TemporaryDirectory() as source_dir:
            source_root = Path(source_dir)
            (source_root / "notes").mkdir()
            (source_root / "notes" / "draft-v0.1.md").write_text(
                "early draft", encoding="utf-8"
            )
            (source_root / "notes" / "draft-v0.2.md").write_text(
                "later draft", encoding="utf-8"
            )
            (source_root / "notes" / "draft-v1.md").write_text(
                "current draft", encoding="utf-8"
            )
            (source_root / "notes" / "unversioned.md").write_text(
                "no version marker", encoding="utf-8"
            )

            records = inventory_local_corpus(source_root)

        by_path = {record["relative_path"]: record for record in records}
        # 版本序列只覆盖三个有版本标记的文件。
        self.assertEqual(by_path["notes/draft-v1.md"]["current_version"], True)
        self.assertEqual(by_path["notes/draft-v1.md"]["evolution_only"], False)
        self.assertEqual(by_path["notes/draft-v0.2.md"]["current_version"], False)
        self.assertEqual(by_path["notes/draft-v0.2.md"]["evolution_only"], True)
        self.assertEqual(by_path["notes/draft-v0.1.md"]["current_version"], False)
        self.assertEqual(by_path["notes/draft-v0.1.md"]["evolution_only"], True)
        # 无版本标记的文件不参与分组。
        self.assertIsNone(by_path["notes/unversioned.md"]["version_group"])
        self.assertFalse(by_path["notes/unversioned.md"]["current_version"])
        self.assertFalse(by_path["notes/unversioned.md"]["evolution_only"])

        # version_group 在三个版本序列文件之间相同。
        self.assertEqual(
            by_path["notes/draft-v1.md"]["version_group"],
            by_path["notes/draft-v0.1.md"]["version_group"],
        )

        summary = count_version_summary(records)
        self.assertEqual(summary["version_groups"], 1)
        self.assertEqual(summary["current_paths"], ["notes/draft-v1.md"])

    def test_version_groups_are_case_insensitive_and_compare_numeric_tuple(self):
        with tempfile.TemporaryDirectory() as source_dir:
            source_root = Path(source_dir)
            (source_root / "plans").mkdir()
            (source_root / "plans" / "plan-V2.md").write_text(
                "uppercase v2", encoding="utf-8"
            )
            (source_root / "plans" / "plan-V10.md").write_text(
                "uppercase v10", encoding="utf-8"
            )
            (source_root / "plans" / "plan-v0.2.3.md").write_text(
                "multi segment", encoding="utf-8"
            )

            records = inventory_local_corpus(source_root)

        by_path = {record["relative_path"]: record for record in records}
        # V10 应被视为最高版本。
        self.assertTrue(by_path["plans/plan-V10.md"]["current_version"])
        self.assertTrue(by_path["plans/plan-V2.md"]["evolution_only"])
        self.assertTrue(by_path["plans/plan-v0.2.3.md"]["evolution_only"])

        summary = count_version_summary(records)
        self.assertEqual(summary["version_groups"], 1)
        self.assertEqual(summary["current_paths"], ["plans/plan-V10.md"])

    def test_files_without_version_marker_are_not_grouped(self):
        with tempfile.TemporaryDirectory() as source_dir:
            source_root = Path(source_dir)
            (source_root / "journal.md").write_text("journal", encoding="utf-8")
            (source_root / "vlog.md").write_text("vlog", encoding="utf-8")
            (source_root / "save.md").write_text("save", encoding="utf-8")

            records = inventory_local_corpus(source_root)

        for record in records:
            self.assertIsNone(record["version_group"])
            self.assertFalse(record["current_version"])
            self.assertFalse(record["evolution_only"])

        summary = count_version_summary(records)
        self.assertEqual(summary["version_groups"], 0)
        self.assertEqual(summary["current_paths"], [])

    def test_assign_version_groups_is_idempotent(self):
        with tempfile.TemporaryDirectory() as source_dir:
            source_root = Path(source_dir)
            (source_root / "draft-v1.md").write_text("first", encoding="utf-8")
            (source_root / "draft-v2.md").write_text("second", encoding="utf-8")

            records = inventory_local_corpus(source_root)
            first_state = [
                (
                    record["relative_path"],
                    record["version_group"],
                    record["current_version"],
                    record["evolution_only"],
                )
                for record in records
            ]
            assign_version_groups(records)
            second_state = [
                (
                    record["relative_path"],
                    record["version_group"],
                    record["current_version"],
                    record["evolution_only"],
                )
                for record in records
            ]

        self.assertEqual(first_state, second_state)

    def test_review_lists_version_group_count_and_current_paths(self):
        work_dir = Path(tempfile.mkdtemp(prefix="nuwa_us008_"))
        try:
            source_root = work_dir / "corpus"
            source_root.mkdir()
            (source_root / "notes").mkdir()
            (source_root / "notes" / "plan-v0.1.md").write_text(
                "old", encoding="utf-8"
            )
            (source_root / "notes" / "plan-v0.2.md").write_text(
                "newer", encoding="utf-8"
            )
            (source_root / "notes" / "plan-v0.3.md").write_text(
                "newest", encoding="utf-8"
            )

            profile_dir = work_dir / "profile"
            records = inventory_local_corpus(source_root)
            summary = summarize_inventory(records)
            write_manifest_and_review(
                profile_dir, records, source_root, summary, 2_000_000
            )

            review_text = (
                profile_dir / "references" / "research" / "00-source-inventory.md"
            ).read_text(encoding="utf-8")
        finally:
            shutil.rmtree(work_dir, ignore_errors=True)

        self.assertIn("## 版本序列", review_text)
        self.assertIn("version_groups: 1", review_text)
        self.assertIn("notes/plan-v0.3.md", review_text)
        self.assertNotIn("old", review_text)
        self.assertNotIn("newer", review_text)
        self.assertNotIn("newest", review_text)


class MergeResearchCompatibilityTests(unittest.TestCase):
    """覆盖 US-009：merge_research.py self 模式 + person 模式向后兼容。"""

    MERGE_SCRIPT = REPO_ROOT / "skills" / "nuwa-skill" / "scripts" / "merge_research.py"
    FIXTURES = REPO_ROOT / "tests" / "fixtures" / "nuwa-self-distill" / "merge_research"

    def _run_cli(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(self.MERGE_SCRIPT), *args],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_person_mode_matches_saved_golden_output(self):
        """person 模式（含/不含 --mode person）输出与修改前一致。"""
        golden_path = self.FIXTURES / "person_golden_output.txt"
        golden = golden_path.read_text(encoding="utf-8")

        without_mode = self._run_cli(str(self.FIXTURES / "person"))
        with_mode = self._run_cli(str(self.FIXTURES / "person"), "--mode", "person")

        self.assertEqual(without_mode.returncode, 0, without_mode.stderr)
        self.assertEqual(with_mode.returncode, 0, with_mode.stderr)
        self.assertEqual(without_mode.stdout.rstrip("\n"), golden.rstrip("\n"))
        self.assertEqual(with_mode.stdout.rstrip("\n"), golden.rstrip("\n"))

    def test_self_mode_uses_six_self_dimensions_and_dedupes_sources(self):
        """self 模式用 6 个 self 标签，按相对源路径去重计数证据。"""
        result = self._run_cli(str(self.FIXTURES / "self"), "--mode", "self")

        self.assertEqual(result.returncode, 0, result.stderr)

        expected_dimensions = (
            "positioning",
            "core-theses",
            "decisions-and-behavior",
            "systems-and-cases",
            "expression-dna",
            "tensions-and-evolution",
        )
        for dimension in expected_dimensions:
            self.assertIn(dimension, result.stdout)

        # 不应再使用 person 模式的 6 标签。
        for person_label in ("著作", "对话", "他者", "时间线"):
            self.assertNotIn(person_label, result.stdout)

        # 核心断言：每个维度的来源数与"总来源(去重)"稳定。
        self.assertIn("│ positioning  │ 3", result.stdout)
        self.assertIn("│ core-theses  │ 2", result.stdout)
        self.assertIn("│ decisions-and-behavior │ 2", result.stdout)
        self.assertIn("│ systems-and-cases │ 2", result.stdout)
        self.assertIn("│ expression-dna │ 1", result.stdout)
        self.assertIn("│ tensions-and-evolution │ 2", result.stdout)
        # positioning-a 在 01/02/05/04 都引用过，去重后只算 1 次。
        # 总来源去重后为 5：positioning-a / positioning-b / external/blog
        # / summaries/private-a / summaries/private-b。
        self.assertIn("│ 总来源(去重) │ 5", result.stdout)

        # 输出与 golden fixture 文本等价（忽略尾换行差异）。
        golden = (self.FIXTURES / "self_golden_output.txt").read_text(encoding="utf-8")
        self.assertEqual(result.stdout.rstrip("\n"), golden.rstrip("\n"))

    def test_self_mode_does_not_require_urls(self):
        """self 模式不依赖 URL；研究文件正文可不含 https://。"""
        dimensions = (
            "core-theses",
            "decisions-and-behavior",
            "systems-and-cases",
            "expression-dna",
            "tensions-and-evolution",
        )
        with tempfile.TemporaryDirectory() as work_dir:
            work = Path(work_dir)
            research_dir = work / "references" / "research"
            research_dir.mkdir(parents=True)

            (research_dir / "01-positioning.md").write_text(
                "---\nsources:\n  - notes/a.md\n  - notes/b.md\n---\n# 定位\n",
                encoding="utf-8",
            )
            for index, dimension in enumerate(dimensions, start=2):
                (research_dir / f"0{index}-{dimension}.md").write_text(
                    f"---\nsources:\n  - notes/a.md\n---\n# {dimension}\n",
                    encoding="utf-8",
                )

            result = self._run_cli(str(work), "--mode", "self")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("│ 总来源(去重) │ 2", result.stdout)
        self.assertNotIn("⚠️ 总来源数", result.stdout)

    def test_self_mode_combines_source_manifest_class_counts(self):
        """self 模式按 manifest 的 policy_class 聚合来源。"""
        with tempfile.TemporaryDirectory() as work_dir:
            work = Path(work_dir)
            research_dir = work / "references" / "research"
            research_dir.mkdir(parents=True)
            (work / "references" / "source-manifest.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "files": [
                            {
                                "relative_path": "notes/owned.md",
                                "policy_class": "authored",
                                "eligible": True,
                            },
                            {
                                "relative_path": "external/ref.md",
                                "policy_class": "external",
                                "eligible": True,
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )

            (research_dir / "01-positioning.md").write_text(
                "---\nsources:\n  - notes/owned.md\n  - external/ref.md\n---\n",
                encoding="utf-8",
            )
            for index, dimension in enumerate(
                (
                    "core-theses",
                    "decisions-and-behavior",
                    "systems-and-cases",
                    "expression-dna",
                    "tensions-and-evolution",
                ),
                start=2,
            ):
                (research_dir / f"0{index}-{dimension}.md").write_text(
                    "---\nsources: []\n---\n",
                    encoding="utf-8",
                )

            result = self._run_cli(str(work), "--mode", "self")

        self.assertEqual(result.returncode, 0, result.stderr)
        # class 计数显示在「总来源(去重)」行右侧 24 字符槽，可能被截断；
        # 完整计数放在表格外。class counts: name=count。
        self.assertIn("class counts: authored=1, external=1", result.stdout)

    def test_self_mode_skips_class_count_when_manifest_missing(self):
        """manifest 缺失时 self 模式仍能运行，但不输出 class 计数。"""
        with tempfile.TemporaryDirectory() as work_dir:
            work = Path(work_dir)
            research_dir = work / "references" / "research"
            research_dir.mkdir(parents=True)
            (research_dir / "01-positioning.md").write_text(
                "---\nsources:\n  - notes/a.md\n---\n", encoding="utf-8"
            )
            for index, dimension in enumerate(
                (
                    "core-theses",
                    "decisions-and-behavior",
                    "systems-and-cases",
                    "expression-dna",
                    "tensions-and-evolution",
                ),
                start=2,
            ):
                (research_dir / f"0{index}-{dimension}.md").write_text(
                    "---\nsources:\n  - notes/a.md\n---\n", encoding="utf-8"
                )

            result = self._run_cli(str(work), "--mode", "self")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(
            "未读取到 references/source-manifest.json", result.stderr
        )
        self.assertNotIn("class:", result.stdout)

    def test_explicit_person_mode_overrides_self_auto_detection(self):
        """SKILL.md frontmatter 标记 self 时，--mode person 显式覆盖自动检测。"""
        with tempfile.TemporaryDirectory() as work_dir:
            work = Path(work_dir)
            (work / "SKILL.md").write_text(
                "---\nprofile_type: self\n---\n", encoding="utf-8"
            )
            research_dir = work / "references" / "research"
            research_dir.mkdir(parents=True)
            for key in (
                "01-writings",
                "02-conversations",
                "03-expression-dna",
                "04-external-views",
                "05-decisions",
                "06-timeline",
            ):
                (research_dir / f"{key}.md").write_text(
                    "https://example.com/a\n", encoding="utf-8"
                )

            auto_result = self._run_cli(str(work))
            explicit_result = self._run_cli(str(work), "--mode", "person")

        self.assertEqual(auto_result.returncode, 0, auto_result.stderr)
        self.assertEqual(explicit_result.returncode, 0, explicit_result.stderr)
        # SKILL.md 标 self 但研究文件是 person 文件名 → 自动检测走 self
        # 时全部维度报告缺失。
        self.assertIn("│ positioning  │ ❌ 缺失", auto_result.stdout)
        # 显式 --mode person 覆盖自动检测，应走 person 路径。
        self.assertIn("│ 著作", explicit_result.stdout)
        self.assertNotIn("│ positioning", explicit_result.stdout)

    def test_auto_detect_self_mode_via_profile_type_frontmatter(self):
        """未传 --mode 且 SKILL.md 含 profile_type: self 时自动走 self。"""
        result = self._run_cli(str(self.FIXTURES / "self"))

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("│ positioning", result.stdout)
        self.assertNotIn("│ 著作", result.stdout)


class QualityStructureTests(unittest.TestCase):
    """覆盖 US-010：quality_check.py self 模式契约。"""

    QUALITY_SCRIPT = REPO_ROOT / "skills" / "nuwa-skill" / "scripts" / "quality_check.py"

    def _run_cli(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(self.QUALITY_SCRIPT), *args],
            capture_output=True,
            text=True,
            check=False,
        )

    def _write_self_profile(self, root: Path, *, missing_sections=(), omit_assets_index=False,
                             assets_link_text="[定位](../assets/positioning.md)",
                             zh_chars: int = 3500) -> None:
        """合成一个 self profile 目录。"""
        profile = root / "test-user-profile"
        profile.mkdir()
        (profile / "assets").mkdir()
        if not omit_assets_index:
            (profile / "assets" / "index.md").write_text("# index", encoding="utf-8")
        sections = [
            "定位与受众",
            "核心心智模型",
            "决策启发式",
            "表达DNA",
            "内容品味与评分标准",
            "价值观与反模式",
            "诚实边界",
        ]
        kept = [s for s in sections if s not in missing_sections]
        body_lines = ["---", "profile_type: self", "---", "", "# Self Profile", ""]
        for section in kept:
            body_lines.append(f"## {section}")
            body_lines.append("")
            body_lines.append(assets_link_text)
            body_lines.append("")
        body_lines.append("中" * zh_chars)
        (profile / "SKILL.md").write_text("\n".join(body_lines), encoding="utf-8")
        return profile

    def test_self_clean_profile_passes(self):
        """干净 self profile 退出码 0，列出五个硬性检查。"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            profile = self._write_self_profile(root)
            result = self._run_cli(str(profile))

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("self 模式契约", result.stdout)
        self.assertIn("七个必需章节", result.stdout)
        self.assertIn("assets/index.md 存在", result.stdout)
        self.assertIn("assets/ 相对链接", result.stdout)
        self.assertIn("token 预算", result.stdout)
        self.assertIn("公开面隐私扫描", result.stdout)
        self.assertIn("5/5 通过", result.stdout)

    def test_self_missing_sections_lists_all_missing(self):
        """缺失章节时退出非零，错误信息列出每个缺失章节名。"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            profile = self._write_self_profile(
                root, missing_sections=("核心心智模型", "表达DNA", "诚实边界")
            )
            result = self._run_cli(str(profile))

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("缺失章节", result.stderr + result.stdout)
        for section in ("核心心智模型", "表达DNA", "诚实边界"):
            self.assertIn(section, result.stdout)

    def test_self_missing_assets_index_fails(self):
        """assets/index.md 缺失时退出非零。"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            profile = self._write_self_profile(root, omit_assets_index=True)
            result = self._run_cli(str(profile))

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("assets/index.md", result.stdout)

    def test_self_missing_assets_link_fails(self):
        """SKILL.md 不含 assets/ 相对链接时退出非零。"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            profile = self._write_self_profile(root, assets_link_text="无任何链接")
            result = self._run_cli(str(profile))

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("assets/", result.stdout)

    def test_self_token_budget_over_6000_fails(self):
        """估算 token > 6000 时退出非零并打印估算值。"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            profile = self._write_self_profile(root, zh_chars=6500)
            result = self._run_cli(str(profile))

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("> 6000", result.stdout)

    def test_self_token_budget_under_3000_warns_but_passes(self):
        """估算 token < 3000 时仅警告，不阻塞（退出码 0）。"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            profile = self._write_self_profile(root, zh_chars=500)
            result = self._run_cli(str(profile))

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("警告", result.stdout)

    def test_self_mode_accepts_skill_md_path_argument(self):
        """quality_check.py 接受 SKILL.md 路径作为 target，与 profile 目录等价。"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            profile = self._write_self_profile(root)
            skill_path = profile / "SKILL.md"
            result = self._run_cli(str(skill_path))

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("self 模式契约", result.stdout)

    def test_explicit_mode_overrides_autodetect(self):
        """显式 --mode 覆盖 frontmatter 自动检测。"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            profile = root / "fake-self"
            profile.mkdir()
            (profile / "assets").mkdir()
            (profile / "assets" / "index.md").write_text("# index", encoding="utf-8")
            # profile_type 是 self，但 --mode person 应该走 person 路径
            # （SKILL.md 没有完整 7 章节，person 检查可能失败；只验证显式模式确实覆盖）。
            (profile / "SKILL.md").write_text(
                "---\nprofile_type: self\n---\n# x\n" + "中" * 3500, encoding="utf-8"
            )
            result = self._run_cli(str(profile), "--mode", "person")

        # person 模式在缺心智模型时会失败；但关键是不能出现 self 模式才有的章节标题输出。
        self.assertIn("person 模式契约", result.stdout)
        self.assertNotIn("七个必需章节", result.stdout)

    def test_person_profile_keeps_backward_compatible_exit_codes(self):
        """person profile 走旧版六项检查，退出码契约不变（全过=0，多项不过=1）。"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            profile = root / "legacy-person"
            profile.mkdir()
            # 完整 person fixture：6 个心智模型、表达 DNA、诚实边界、张力、来源比例。
            body = ["# Person", ""]
            for index in range(5):
                body.append(f"### 模型 {index + 1}")
                body.append("一句话 + 局限性")
                body.append("")
            body.append("## 表达DNA")
            body.append("句式词汇语气幽默节奏确定性引用口头禅")
            body.append("")
            body.append("## 诚实边界")
            body.append("- 不 A")
            body.append("- 不 B")
            body.append("- 不 C")
            body.append("")
            body.append("张力 tension paradox 矛盾 一方面...另一方面")
            body.append("")
            body.append("## 调研来源")
            body.append("一手资料 primary 原始")
            (profile / "SKILL.md").write_text("\n".join(body), encoding="utf-8")
            result = self._run_cli(str(profile))

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("person 模式契约", result.stdout)
        self.assertIn("心智模型数量", result.stdout)

    def test_self_profile_via_frontmatter_detection(self):
        """未传 --mode 时，根据 SKILL.md frontmatter 自动识别 self。"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            profile = self._write_self_profile(root)
            result = self._run_cli(str(profile))

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("detected=self", result.stdout)
        self.assertIn("mode=self", result.stdout)


class PrivacyGateTests(unittest.TestCase):
    """覆盖 US-011：公开面隐私扫描（SKILL.md + assets/*.md）。"""

    QUALITY_SCRIPT = REPO_ROOT / "skills" / "nuwa-skill" / "scripts" / "quality_check.py"

    def _run_cli(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(self.QUALITY_SCRIPT), *args],
            capture_output=True,
            text=True,
            check=False,
        )

    @staticmethod
    def _seed_clean_profile(root: Path) -> Path:
        profile = root / "privacy-profile"
        profile.mkdir()
        (profile / "assets").mkdir()
        (profile / "assets" / "index.md").write_text("# index\n", encoding="utf-8")
        (profile / "assets" / "positioning.md").write_text(
            "# positioning\n\nno sensitive content here.\n",
            encoding="utf-8",
        )
        sections = [
            "定位与受众",
            "核心心智模型",
            "决策启发式",
            "表达DNA",
            "内容品味与评分标准",
            "价值观与反模式",
            "诚实边界",
        ]
        body_lines = ["---", "profile_type: self", "---", "", "# Self Profile", ""]
        for section in sections:
            body_lines.append(f"## {section}")
            body_lines.append("")
            body_lines.append("[定位](../assets/positioning.md)")
            body_lines.append("")
        body_lines.append("中" * 3500)
        (profile / "SKILL.md").write_text("\n".join(body_lines), encoding="utf-8")
        return profile

    def test_clean_self_profile_passes_privacy_scan(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            profile = self._seed_clean_profile(root)
            result = self._run_cli(str(profile))

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("公开面隐私扫描", result.stdout)
        self.assertIn("通过", result.stdout)

    def test_wechat_id_in_skill_md_fails_with_stable_rule_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            profile = self._seed_clean_profile(root)
            skill_md = profile / "SKILL.md"
            text = skill_md.read_text(encoding="utf-8")
            text = text.replace(
                "# Self Profile",
                "# Self Profile\n\nsynthetic contact wxid_fakeabc123\n",
                1,
            )
            skill_md.write_text(text, encoding="utf-8")
            result = self._run_cli(str(profile))

        self.assertNotEqual(result.returncode, 0)
        combined = result.stdout + result.stderr
        self.assertIn("WECHAT_ID", combined)
        self.assertIn("SKILL.md", combined)
        # 隐私契约：完整 wxid_ 串不能回显到 stdout/stderr。
        self.assertNotIn("wxid_fakeabc123", combined)

    def test_chatroom_id_in_assets_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            profile = self._seed_clean_profile(root)
            (profile / "assets" / "team.md").write_text(
                "# team\n\nsynthetic @chatroom secret\n",
                encoding="utf-8",
            )
            result = self._run_cli(str(profile))

        self.assertNotEqual(result.returncode, 0)
        combined = result.stdout + result.stderr
        self.assertIn("CHATROOM_ID", combined)
        self.assertIn("assets/team.md", combined)

    def test_credential_assignment_in_skill_md_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            profile = self._seed_clean_profile(root)
            skill_md = profile / "SKILL.md"
            text = skill_md.read_text(encoding="utf-8")
            text = text.replace(
                "# Self Profile",
                "# Self Profile\n\ntoken = FAKEFAKEFAKEFAKE\n",
                1,
            )
            skill_md.write_text(text, encoding="utf-8")
            result = self._run_cli(str(profile))

        self.assertNotEqual(result.returncode, 0)
        combined = result.stdout + result.stderr
        self.assertIn("CREDENTIAL_ASSIGNMENT", combined)
        self.assertNotIn("FAKEFAKEFAKEFAKE", combined)

    def test_private_ipv4_in_assets_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            profile = self._seed_clean_profile(root)
            (profile / "assets" / "ops.md").write_text(
                "# ops\n\nconnect to 10.0.0.5 internally\n",
                encoding="utf-8",
            )
            result = self._run_cli(str(profile))

        self.assertNotEqual(result.returncode, 0)
        combined = result.stdout + result.stderr
        self.assertIn("PRIVATE_IPV4", combined)
        self.assertIn("assets/ops.md", combined)

    def test_public_ipv4_in_assets_does_not_fail(self):
        """公网 IPv4 不应被标记为 RFC1918。"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            profile = self._seed_clean_profile(root)
            (profile / "assets" / "ops.md").write_text(
                "# ops\n\npublic endpoint 8.8.8.8 reachable\n",
                encoding="utf-8",
            )
            result = self._run_cli(str(profile))

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("公开面隐私扫描", result.stdout)

    def test_references_directory_is_not_scanned(self):
        """references/source-manifest.json 与 references/research/ 含聊天标识也不应误报。"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            profile = self._seed_clean_profile(root)
            references = profile / "references"
            references.mkdir()
            (references / "source-manifest.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "files": [
                            {
                                "relative_path": "chatlog/2024-q1.md",
                                "policy_class": "private-evidence",
                                "eligible": True,
                                "notes": "微信 / wxid_fake_secret @chatroom",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            research_dir = references / "research"
            research_dir.mkdir()
            (research_dir / "01-positioning.md").write_text(
                "synthetic wxid_fake_secret @chatroom 10.0.0.7 token=fake1234abcd\n",
                encoding="utf-8",
            )
            result = self._run_cli(str(profile))

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("公开面隐私扫描通过", result.stdout)

    def test_findings_include_relative_path_and_line_number(self):
        """findings 必须包含 rule id + 相对路径 + 行号。"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            profile = self._seed_clean_profile(root)
            skill_md = profile / "SKILL.md"
            text = skill_md.read_text(encoding="utf-8")
            text = text.replace(
                "# Self Profile",
                "# Self Profile\n\nline1\nline2 with wxid_fakealpha5678\n",
                1,
            )
            skill_md.write_text(text, encoding="utf-8")
            result = self._run_cli(str(profile))

        self.assertNotEqual(result.returncode, 0)
        combined = result.stdout + result.stderr
        self.assertIn("WECHAT_ID", combined)
        self.assertIn("SKILL.md:", combined)
        # 行号必须是整数；粗略断言有数字。
        import re as _re

        self.assertRegex(combined, _re.compile(r"SKILL\.md:\d+"))


class SelfDistillEndToEndTests(unittest.TestCase):
    """覆盖 US-017：合成语料端到端 — 盘点 → policy → 质量门 → 隐私失败。

    整套测试以 `tests/fixtures/nuwa-self-distill/e2e/` 为基础，运行两次 inventory
    （无 policy → 带 policy），断言：源树零写入、profile 目录无源正文副本、
    first-match 分类、duplicate representative、version current、clean self
    profile 通过 quality gate、dirty self profile 失败且不回显凭据值，
    全部 person fixture 仍能通过。
    """

    REPO_ROOT = Path(__file__).resolve().parents[1]
    SCRIPT = REPO_ROOT / "skills" / "nuwa-skill" / "scripts" / "inventory_local_corpus.py"
    QUALITY_SCRIPT = REPO_ROOT / "skills" / "nuwa-skill" / "scripts" / "quality_check.py"
    MERGE_SCRIPT = REPO_ROOT / "skills" / "nuwa-skill" / "scripts" / "merge_research.py"
    FIXTURES = REPO_ROOT / "tests" / "fixtures" / "nuwa-self-distill"
    E2E_CORPUS = FIXTURES / "e2e" / "corpus"
    E2E_POLICY = FIXTURES / "e2e" / "source-policy.json"
    MERGE_FIXTURES = FIXTURES / "merge_research"

    def _run_inventory(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(self.SCRIPT), *args],
            capture_output=True,
            text=True,
            check=False,
        )

    def _run_quality(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(self.QUALITY_SCRIPT), *args],
            capture_output=True,
            text=True,
            check=False,
        )

    def _hash_tree(self, root: Path) -> dict:
        payload: dict = {}
        for path in sorted(root.rglob("*")):
            if path.is_file():
                payload[path.relative_to(root).as_posix()] = (
                    hashlib.sha256(path.read_bytes()).hexdigest()
                )
        return payload

    def _build_clean_self_profile(self, root: Path, *, with_dirty_assets: bool = False,
                                   add_dirty_skill_line: str | None = None) -> Path:
        """合成一个 self profile 目录，含 7 个必需章节和 assets/index.md。

        `with_dirty_assets` 时附加明显的假隐私污染样例以触发质量门失败。
        `add_dirty_skill_line` 在 SKILL.md 内追加一行污染内容（如 wxid_ / @chatroom
        / token=... / 私网 IP）以触发质量门失败。
        """
        profile = root / "synthetic-self-profile"
        profile.mkdir()
        (profile / "assets").mkdir()
        (profile / "assets" / "index.md").write_text(
            "# index\n\nSynthetic profile index for self-distill e2e.\n",
            encoding="utf-8",
        )
        # 8 个 assets 页面：index 之上 7 张资产卡，token 控制在 3000-6000 区间。
        page_stubs = (
            "positioning",
            "core-theses",
            "operating-principles",
            "systems-and-workflows",
            "cases-and-evidence",
            "content-motifs",
            "reusable-products",
        )
        for page in page_stubs:
            (profile / "assets" / f"{page}.md").write_text(
                f"# {page}\n\nSynthetic asset page for e2e fixture.\n",
                encoding="utf-8",
            )

        sections = (
            "定位与受众",
            "核心心智模型",
            "决策启发式",
            "表达DNA",
            "内容品味与评分标准",
            "价值观与反模式",
            "诚实边界",
        )
        body_lines = ["---", "profile_type: self", "---", "", "# Synthetic Self Profile", ""]
        for section in sections:
            body_lines.append(f"## {section}")
            body_lines.append("")
            body_lines.append(f"参见 [链接文本](../assets/{page_stubs[0]}.md)")
            body_lines.append("")
        # 中文段落撑到 ~3500 estimated tokens（US-010 估算公式）
        body_lines.append("中" * 3500)
        if add_dirty_skill_line:
            body_lines.append(add_dirty_skill_line)
        (profile / "SKILL.md").write_text("\n".join(body_lines), encoding="utf-8")

        if with_dirty_assets:
            dirty_assets = {
                "wechat-id.md": "synthetic wxid_fake_dirty_alpha1234 secret\n",
                "chatroom-id.md": "synthetic secret @chatroom_fake12345\n",
                "credential.md": "token=fake_dirty_token_value api access\n",
                "internal-ip.md": "internal only 10.0.0.66 reachable\n",
            }
            for name, body in dirty_assets.items():
                (profile / "assets" / name).write_text(
                    f"# {name}\n\n{body}", encoding="utf-8"
                )
        return profile

    # ---- 静态 fixture 自检（保证目录可复用） ----

    def test_e2e_fixture_layout_is_complete(self):
        """静态 fixture 必须包含 US-017 要求的五类元素。"""
        expected = (
            self.E2E_CORPUS / "authored" / "note-alpha.md",
            self.E2E_CORPUS / "authored" / "note-alpha-copy.md",
            self.E2E_CORPUS / "authored" / "plan-v0.1.md",
            self.E2E_CORPUS / "authored" / "plan-v0.2.md",
            self.E2E_CORPUS / "authored" / "plan-v1.md",
            self.E2E_CORPUS / "private" / "summary-q1.md",
            self.E2E_CORPUS / "private" / "summary-q2.md",
            self.E2E_CORPUS / "adapted" / "derived-1.md",
            self.E2E_CORPUS / "adapted" / "derived-2.md",
            self.E2E_CORPUS / "external" / "article-1.md",
            self.E2E_CORPUS / "external" / "article-2.md",
            self.E2E_CORPUS / "authored" / "legacy.md",
            self.E2E_POLICY,
        )
        for path in expected:
            self.assertTrue(path.is_file(), f"fixture missing: {path}")

        # 精确重复：note-alpha 与 note-alpha-copy 必须有相同 SHA-256
        alpha_hash = hashlib.sha256(
            (self.E2E_CORPUS / "authored" / "note-alpha.md").read_bytes()
        ).hexdigest()
        copy_hash = hashlib.sha256(
            (self.E2E_CORPUS / "authored" / "note-alpha-copy.md").read_bytes()
        ).hexdigest()
        self.assertEqual(alpha_hash, copy_hash)

        # 版本序列：plan-v1 必须存在，被期望为 current
        self.assertTrue((self.E2E_CORPUS / "authored" / "plan-v1.md").is_file())

        # policy 必须合法 JSON，且 schema_version=1 + rules 非空
        policy = json.loads(self.E2E_POLICY.read_text(encoding="utf-8"))
        self.assertEqual(policy["schema_version"], 1)
        self.assertGreaterEqual(len(policy["rules"]), 4)

    # ---- inventory 无 policy 阶段 ----

    def test_no_policy_run_writes_unclassified_manifest_with_can_distill_false(self):
        """无 policy 时所有 eligible 文件保持 unclassified，can_distill=false。"""
        work_dir = Path(tempfile.mkdtemp(prefix="nuwa_e2e_nopolicy_"))
        try:
            source_root = work_dir / "corpus"
            profile_dir = work_dir / "profile"
            self._copy_fixture_corpus(source_root)
            before_hash = self._hash_tree(source_root)

            result = self._run_inventory(str(source_root), "--profile-dir", str(profile_dir))

            after_hash = self._hash_tree(source_root)
            manifest_path = profile_dir / "references" / "source-manifest.json"
            review_path = (
                profile_dir / "references" / "research" / "00-source-inventory.md"
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(manifest_path.is_file())
            self.assertTrue(review_path.is_file())
            self.assertFalse((profile_dir / "source-policy.json").exists())
            # 源目录字节级零写入
            self.assertEqual(before_hash, after_hash)
            # profile 目录内不得有源文件正文副本
            self._assert_profile_has_no_source_bodies(profile_dir, source_root)

            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertFalse(manifest["can_distill"])
            eligible_entries = [
                entry for entry in manifest["files"] if entry["eligible"]
            ]
            self.assertGreater(len(eligible_entries), 0)
            self.assertTrue(
                all(entry["policy_class"] == "unclassified" for entry in eligible_entries)
            )

            # review 不含源正文（关键字探针）
            review_text = review_path.read_text(encoding="utf-8")
            for needle in (
                "synthetic wxid_",
                "@chatroom_fake",
                "10.0.0.66",
                "token=fake",
            ):
                self.assertNotIn(needle, review_text)
        finally:
            shutil.rmtree(work_dir, ignore_errors=True)

    # ---- inventory 带 policy 阶段 ----

    def test_with_policy_classifies_first_match_sets_can_distill_true(self):
        """带 policy 重跑后 all eligible 都有类，can_distill=true。"""
        work_dir = Path(tempfile.mkdtemp(prefix="nuwa_e2e_policy_"))
        try:
            source_root = work_dir / "corpus"
            profile_dir = work_dir / "profile"
            policy_path = work_dir / "source-policy.json"
            self._copy_fixture_corpus(source_root)
            policy_path.write_text(
                self.E2E_POLICY.read_text(encoding="utf-8"), encoding="utf-8"
            )

            result = self._run_inventory(
                str(source_root),
                "--profile-dir",
                str(profile_dir),
                "--policy",
                str(policy_path),
            )
            self.assertEqual(result.returncode, 0, result.stderr)

            manifest = json.loads(
                (profile_dir / "references" / "source-manifest.json").read_text(
                    encoding="utf-8"
                )
            )

            by_path = {entry["relative_path"]: entry for entry in manifest["files"]}

            # 各类至少一条命中
            class_expect = {
                "authored/note-alpha.md": "authored",
                "private/summary-q1.md": "private-evidence",
                "adapted/derived-1.md": "adapted",
                "external/article-1.md": "external",
                "authored/legacy.md": "excluded",
            }
            for rel, expected_class in class_expect.items():
                self.assertEqual(by_path[rel]["policy_class"], expected_class)

            # eligible 文件全部进入 DISTILLABLE_POLICY_CLASSES(excluded 之外) → can_distill=true
            self.assertTrue(manifest["can_distill"])
            # excluded 类别存在，distillable_count 不包含 excluded
            excluded = by_path["authored/legacy.md"]
            self.assertEqual(excluded["policy_class"], "excluded")
            excluded_set = {
                entry["relative_path"]
                for entry in manifest["files"]
                if entry["policy_class"] == "excluded"
            }
            self.assertEqual(excluded_set, {"authored/legacy.md"})

            # duplicate representative：字典序最小者是代表（-copy 在 -alpha 前）
            alpha = by_path["authored/note-alpha.md"]
            alpha_copy = by_path["authored/note-alpha-copy.md"]
            self.assertEqual(alpha["duplicate_group"], alpha_copy["duplicate_group"])
            self.assertTrue(alpha_copy["semantic_read"])
            self.assertFalse(alpha["semantic_read"])
            self.assertEqual(alpha["duplicate_group"], alpha["sha256"])
            self.assertLess("authored/note-alpha-copy.md", "authored/note-alpha.md")

            # version sequence：plan-v1 为 current
            v1 = by_path["authored/plan-v1.md"]
            v01 = by_path["authored/plan-v0.1.md"]
            v02 = by_path["authored/plan-v0.2.md"]
            self.assertEqual(v1["version_group"], v01["version_group"])
            self.assertEqual(v01["version_group"], v02["version_group"])
            self.assertTrue(v1["current_version"])
            self.assertTrue(v01["evolution_only"])
            self.assertTrue(v02["evolution_only"])

            # 源目录 SHA-256 在带 policy 重跑前后仍一致（环境无残留文件）
            final_hash = self._hash_tree(source_root)
            # 比较本次复制后的预期哈希：每个原文按字节重算
            expected_hash = self._hash_tree(self.E2E_CORPUS)
            self.assertEqual(final_hash, expected_hash)
            # profile 目录内不得有源正文副本
            self._assert_profile_has_no_source_bodies(profile_dir, source_root)
        finally:
            shutil.rmtree(work_dir, ignore_errors=True)

    # ---- quality_check 集成：clean profile / dirty profile / person 回归 ----

    def test_clean_self_profile_passes_quality_gate(self):
        """无 policy → quality 收尾：clean self profile 退出码 0。"""
        work_dir = Path(tempfile.mkdtemp(prefix="nuwa_e2e_clean_"))
        try:
            profile = self._build_clean_self_profile(work_dir)
            result = self._run_quality(str(profile))
            self.assertEqual(result.returncode, 0, result.stderr)
            # 关键契约
            self.assertIn("mode=self", result.stdout)
            self.assertIn("公开面隐私扫描", result.stdout)
            self.assertIn("5/5 通过", result.stdout)
        finally:
            shutil.rmtree(work_dir, ignore_errors=True)

    def test_dirty_self_profile_fails_quality_gate_without_echoing_value(self):
        """隐私污染 fixture：quality_check 必须失败，输出不回显完整敏感值。"""
        work_dir = Path(tempfile.mkdtemp(prefix="nuwa_e2e_dirty_"))
        try:
            profile = self._build_clean_self_profile(work_dir, with_dirty_assets=True)
            result = self._run_quality(str(profile))
            combined = result.stdout + result.stderr
            self.assertNotEqual(result.returncode, 0)
            # 规则 id 必须命中（至少 4 种之一）
            self.assertTrue(
                any(
                    rule in combined
                    for rule in (
                        "WECHAT_ID",
                        "CHATROOM_ID",
                        "CREDENTIAL_ASSIGNMENT",
                        "PRIVATE_IPV4",
                    )
                ),
                combined,
            )
            # 敏感值不得完整回显
            for sensitive in (
                "wxid_fake_dirty_alpha1234",
                "@chatroom_fake12345",
                "token=fake_dirty_token_value",
                "10.0.0.66",
            ):
                self.assertNotIn(sensitive, combined)
            # 仍需给出相对路径 + 行号（findings 表友好）
            self.assertIn("assets/", combined)
        finally:
            shutil.rmtree(work_dir, ignore_errors=True)

    def test_existing_person_merge_golden_fixture_still_passes(self):
        """person 模式 merge_research.py golden fixture 在 US-017 后无回归。"""
        golden_path = self.MERGE_FIXTURES / "person_golden_output.txt"
        if not golden_path.is_file():
            self.skipTest("person golden fixture missing")
        golden = golden_path.read_text(encoding="utf-8")

        # 无 mode
        no_mode = subprocess.run(
            [sys.executable, str(self.MERGE_SCRIPT), str(self.MERGE_FIXTURES / "person")],
            capture_output=True,
            text=True,
            check=False,
        )
        # 显式 --mode person
        explicit = subprocess.run(
            [
                sys.executable,
                str(self.MERGE_SCRIPT),
                str(self.MERGE_FIXTURES / "person"),
                "--mode",
                "person",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(no_mode.returncode, 0, no_mode.stderr)
        self.assertEqual(explicit.returncode, 0, explicit.stderr)
        self.assertEqual(no_mode.stdout.rstrip("\n"), golden.rstrip("\n"))
        self.assertEqual(explicit.stdout.rstrip("\n"), golden.rstrip("\n"))

    # ---- 辅助：fixture 复制 + 完整性 ----

    def _copy_fixture_corpus(self, target: Path) -> None:
        """把 tests/fixtures/nuwa-self-distill/e2e/corpus 复制到 target/corpus。"""
        target.mkdir(parents=True)
        for src in self.E2E_CORPUS.rglob("*"):
            if not src.is_file():
                continue
            rel = src.relative_to(self.E2E_CORPUS)
            dst = target / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(src.read_bytes())

    def _assert_profile_has_no_source_bodies(self, profile_dir: Path, source_root: Path) -> None:
        """profile 目录内不允许出现源文件正文副本。"""
        source_bodies = []
        for src in source_root.rglob("*"):
            if not src.is_file():
                continue
            text = src.read_text(encoding="utf-8", errors="ignore")
            # 取第一段非标题且非指令性首行作为探针
            for line in text.splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "synthetic " not in line.lower():
                    source_bodies.append(line)
                    break
        # 至少在 corpus 里找到一些非标题且非说明行作为探针
        self.assertGreater(len(source_bodies), 0, "source corpus empty")

        profile_text = ""
        for path in profile_dir.rglob("*"):
            if path.is_file() and path.suffix in {".md", ".txt", ".json"}:
                profile_text += path.read_text(encoding="utf-8", errors="ignore")
        for needle in source_bodies:
            self.assertNotIn(needle, profile_text, f"profile leaked source body: {needle}")


if __name__ == "__main__":
    unittest.main()
