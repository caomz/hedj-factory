#!/usr/bin/env python3
"""Negative tests for check_image_prompt_schema.py without recursive cleanup."""
from __future__ import annotations

import importlib.util
import shutil
import tempfile
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parent
CHECKER = SCRIPTS / "check_image_prompt_schema.py"
SPEC = importlib.util.spec_from_file_location("image_prompt_schema_checker", CHECKER)
assert SPEC is not None and SPEC.loader is not None
CHECKER_MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECKER_MODULE)
SOURCE_ROOT = SCRIPTS.parents[2]


class ImagePromptSchemaCheckerTests(unittest.TestCase):
    def fixture(self) -> Path:
        root = Path(tempfile.mkdtemp(prefix="image-prompt-schema-check-"))
        for relative in [CHECKER_MODULE.SCHEMA_REL, *CHECKER_MODULE.WIRING]:
            source = SOURCE_ROOT / relative
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        return root

    def test_current_contract_passes(self) -> None:
        self.assertEqual(CHECKER_MODULE.check_repo(SOURCE_ROOT), [])

    def test_missing_heading_fails(self) -> None:
        root = self.fixture()
        schema = root / CHECKER_MODULE.SCHEMA_REL
        text = schema.read_text(encoding="utf-8").replace(
            "## 来源登记与生成后验收", "## 来源登记"
        )
        schema.write_text(text, encoding="utf-8")
        self.assertTrue(any("缺精确章节" in item for item in CHECKER_MODULE.check_repo(root)))

    def test_square_grid_conflict_fails(self) -> None:
        root = self.fixture()
        schema = root / CHECKER_MODULE.SCHEMA_REL
        schema.write_text(
            schema.read_text(encoding="utf-8") + "\n单张 1:1 画布等分 3×3 九格\n",
            encoding="utf-8",
        )
        self.assertTrue(any("冲突合同" in item for item in CHECKER_MODULE.check_repo(root)))

    def test_missing_wiring_semantics_fails(self) -> None:
        root = self.fixture()
        skill = root / "skills/book-narration-video/SKILL.md"
        skill.write_text(
            skill.read_text(encoding="utf-8").replace("不能伪造或复刻书封", "不可使用假图"),
            encoding="utf-8",
        )
        self.assertTrue(any("缺接线语义" in item for item in CHECKER_MODULE.check_repo(root)))


if __name__ == "__main__":
    unittest.main(verbosity=2)
