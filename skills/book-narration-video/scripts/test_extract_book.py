#!/usr/bin/env python3
"""extract_book.py unittest — fixtures 全部生成在 TemporaryDirectory，不碰仓库、不 rm -rf。"""
from __future__ import annotations

import hashlib
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
        cls._tmp.cleanup()  # tempfile API，不是 shell rm -rf

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
        self.assertIn("来源SHA256：", src)
        self.assertIn("范围：章节段 4", src)

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
        # second extract with different --name appends source record
        run([str(self.epub), "--out", str(out), "--chapters", "3", "--name", "原文-ch3.txt"])
        src2 = (out / "source.txt").read_text(encoding="utf-8")
        self.assertEqual(src2.count("extract_book.py"), 2)

    def test_pdf_page_range(self):
        out = Path(self._tmp.name) / "out-pdf"
        r = run([str(self.pdf), "--list"])
        self.assertIn("共 2 页", r.stdout)
        run([str(self.pdf), "--out", str(out), "--pages", "2",
             "--title", "Tiny Habits Field Notes"])
        text = (out / "原文.txt").read_text(encoding="utf-8")
        self.assertIn("Page two marker", text)
        self.assertNotIn("Chapter one", text)
        self.assertIn("sample.pdf（pdf", (out / "source.txt").read_text(encoding="utf-8"))

    def test_max_chars_truncation(self):
        r = run([str(self.txt), "--max-chars", "260"])
        self.assertIn("[已截断", r.stdout)

    def test_refuse_overwrite_without_force(self):
        out = Path(self._tmp.name) / "out-ow"
        run([str(self.txt), "--out", str(out), "--chapters", "4", "--title", "t"])
        r = run([str(self.txt), "--out", str(out), "--chapters", "4", "--title", "t"],
                check=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("输出已存在", r.stderr)

    def test_force_backup(self):
        out = Path(self._tmp.name) / "out-force"
        run([str(self.txt), "--out", str(out), "--chapters", "4", "--title", "t1"])
        run([str(self.txt), "--out", str(out), "--chapters", "4", "--title", "t2", "--force"])
        self.assertTrue((out / "原文.txt").exists())
        self.assertTrue((out / "原文.txt.bak").exists())

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
        self.assertIn(f"来源SHA256：{digest}", src)


if __name__ == "__main__":
    unittest.main(verbosity=2)
