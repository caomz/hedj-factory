#!/usr/bin/env python3
"""extract_book.py unittest — fixtures 全部生成在 TemporaryDirectory。"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
EXTRACT = SCRIPTS / "extract_book.py"
MAKE_FIX = SCRIPTS / "make_fixtures.py"


def run(args, check=True):
    return subprocess.run(
        [sys.executable, str(EXTRACT), *args],
        capture_output=True, text=True, check=check,
    )


class ExtractBookTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory(prefix="extract-book-")
        cls.fix = Path(cls._tmp.name) / "fixtures"
        subprocess.run(
            [sys.executable, str(MAKE_FIX), "--out", str(cls.fix)],
            check=True, capture_output=True, text=True,
        )
        cls.txt = cls.fix / "sample.txt"
        cls.epub = cls.fix / "sample.epub"
        cls.pdf = cls.fix / "sample.pdf"

    @classmethod
    def tearDownClass(cls):
        # Controlled temp dir created by tempfile; not a shell rm -rf of user paths.
        cls._tmp.cleanup()

    def test_help(self):
        r = run(["--help"])
        self.assertIn("--chapters", r.stdout)
        self.assertIn("--dry-run", r.stdout)
        self.assertIn("--force", r.stdout)

    def test_txt_list_and_chapter_range(self):
        out = Path(self._tmp.name) / "out-txt"
        r = run([str(self.txt), "--list"])
        self.assertIn("第二章 环境的杠杆", r.stdout)
        run([str(self.txt), "--out", str(out), "--chapters", "4",
             "--title", "微型习惯手册", "--author", "测试员"])
        text = (out / "原文.txt").read_text(encoding="utf-8")
        self.assertIn("身份的复利", text)
        self.assertNotIn("环境的杠杆", text)
        src = (out / "source.txt").read_text(encoding="utf-8")
        self.assertIn("书名：微型习惯手册", src)
        self.assertIn("输入SHA256：", src)
        self.assertIn("输出SHA256：", src)
        self.assertNotIn("来源SHA256：", src)
        man = json.loads((out / "extraction-manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(len(man["extractions"]), 1)
        self.assertEqual(man["latest"]["input_sha256"],
                         hashlib.sha256(self.txt.read_bytes()).hexdigest())

    def test_epub_meta_range_and_append(self):
        out = Path(self._tmp.name) / "out-epub"
        r = run([str(self.epub), "--list"])
        self.assertIn("微型习惯手册", r.stdout)
        self.assertIn("共 3 个章节段", r.stdout)
        run([str(self.epub), "--out", str(out), "--chapters", "1-2"])
        text = (out / "原文.txt").read_text(encoding="utf-8")
        self.assertIn("俯卧撑", text)
        self.assertIn("你不是缺自律", text)
        self.assertNotIn("身份的复利", text)
        src = (out / "source.txt").read_text(encoding="utf-8")
        self.assertIn("作者：测试员", src)
        run([str(self.epub), "--out", str(out), "--chapters", "3", "--name", "原文-ch3.txt"])
        src2 = (out / "source.txt").read_text(encoding="utf-8")
        self.assertEqual(src2.count("extract_book.py"), 2)
        man = json.loads((out / "extraction-manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(len(man["extractions"]), 2)

    def test_multi_source_full_hashes(self):
        """EPUB then TXT: both full input hashes must remain recoverable."""
        out = Path(self._tmp.name) / "out-multi"
        epub_sha = hashlib.sha256(self.epub.read_bytes()).hexdigest()
        txt_sha = hashlib.sha256(self.txt.read_bytes()).hexdigest()
        run([str(self.epub), "--out", str(out), "--chapters", "1", "--name", "原文-epub.txt"])
        run([str(self.txt), "--out", str(out), "--chapters", "4", "--name", "原文-txt.txt",
             "--title", "微型习惯手册"])
        src = (out / "source.txt").read_text(encoding="utf-8")
        self.assertIn(f"输入SHA256：{epub_sha}", src)
        self.assertIn(f"输入SHA256：{txt_sha}", src)
        self.assertNotIn("来源SHA256：", src)
        man = json.loads((out / "extraction-manifest.json").read_text(encoding="utf-8"))
        hashes = {e["input_sha256"] for e in man["extractions"]}
        self.assertEqual(hashes, {epub_sha, txt_sha})
        self.assertEqual(man["latest"]["input_sha256"], txt_sha)

    def test_pdf_page_range(self):
        out = Path(self._tmp.name) / "out-pdf"
        r = run([str(self.pdf), "--list"])
        self.assertIn("共 2 页", r.stdout)
        run([str(self.pdf), "--out", str(out), "--pages", "2",
             "--title", "Tiny Habits Field Notes"])
        text = (out / "原文.txt").read_text(encoding="utf-8")
        self.assertIn("Page two marker", text)
        self.assertNotIn("Chapter one", text)

    def test_max_chars_truncation(self):
        r = run([str(self.txt), "--max-chars", "260"])
        self.assertIn("[已截断", r.stdout)

    def test_reject_negative_max_chars(self):
        r = run([str(self.txt), "--max-chars", "-1"], check=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("--max-chars", r.stderr)

    def test_reject_directory_source(self):
        r = run([str(self.fix), "--list"], check=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("必须是文件", r.stderr)

    def test_refuse_overwrite_without_force(self):
        out = Path(self._tmp.name) / "out-ow"
        run([str(self.txt), "--out", str(out), "--chapters", "4", "--title", "t"])
        r = run([str(self.txt), "--out", str(out), "--chapters", "4", "--title", "t"],
                check=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("输出已存在", r.stderr)

    def test_force_backup_nested_name(self):
        out = Path(self._tmp.name) / "out-force"
        run([str(self.txt), "--out", str(out), "--chapters", "4", "--title", "t1",
             "--name", "nested/原文.txt"])
        run([str(self.txt), "--out", str(out), "--chapters", "4", "--title", "t2",
             "--name", "nested/原文.txt", "--force"])
        self.assertTrue((out / "nested" / "原文.txt").exists())
        self.assertTrue((out / "nested" / "原文.txt.bak").exists())
        self.assertFalse((out / "原文.txt.bak").exists())

    def test_dry_run_no_write(self):
        out = Path(self._tmp.name) / "out-dry"
        r = run([str(self.txt), "--out", str(out), "--chapters", "4", "--dry-run"])
        self.assertIn("[dry-run]", r.stdout)
        self.assertFalse(out.exists())

    def test_path_escape_rejected(self):
        out = Path(self._tmp.name) / "out-esc"
        out.mkdir(parents=True, exist_ok=True)
        r = run([str(self.txt), "--out", str(out), "--chapters", "4",
                 "--name", "../../escaped.txt"], check=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertTrue("不允许" in r.stderr or "逃出" in r.stderr or "绝对路径" in r.stderr)
        self.assertFalse((Path(self._tmp.name) / "escaped.txt").exists())

    def test_sha256_matches_source(self):
        out = Path(self._tmp.name) / "out-sha"
        digest = hashlib.sha256(self.epub.read_bytes()).hexdigest()
        run([str(self.epub), "--out", str(out), "--chapters", "1"])
        src = (out / "source.txt").read_text(encoding="utf-8")
        self.assertIn(f"输入SHA256：{digest}", src)
        man = json.loads((out / "extraction-manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(man["latest"]["input_sha256"], digest)


if __name__ == "__main__":
    unittest.main(verbosity=2)
