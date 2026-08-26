#!/usr/bin/env python3
"""Smoke checks for pack_transplant_bundle.py (mkdtemp, no recursive cleanup)."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
PACK = SCRIPTS / "pack_transplant_bundle.py"


def run(args, check=True):
    return subprocess.run(
        [sys.executable, str(PACK), *args],
        capture_output=True, text=True, check=check,
    )


class PackBundleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(tempfile.mkdtemp(prefix="pack-bundle-"))

    def test_dry_run(self):
        out = self.root / "dry"
        r = run(["--out", str(out), "--dry-run"])
        self.assertEqual(r.returncode, 0)
        self.assertIn("[dry-run]", r.stdout)
        self.assertFalse(out.exists())

    def test_pack_and_manifest(self):
        out = self.root / "bundle"
        r = run(["--out", str(out)])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue((out / "scripts/extract_book.py").is_file())
        self.assertTrue((out / "scripts/test_extract_book.py").is_file())
        self.assertTrue((out / "references/transplant-to-state-machine.md").is_file())
        man = json.loads((out / "TRANSPLANT_MANIFEST.json").read_text(encoding="utf-8"))
        self.assertEqual(man["schema_version"], 1)
        self.assertGreaterEqual(len(man["files"]), 5)

    def test_refuse_nonempty_without_force(self):
        out = self.root / "nonempty"
        run(["--out", str(out)])
        r = run(["--out", str(out)], check=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("非空", r.stderr)

    def test_force_overwrite(self):
        out = self.root / "force"
        run(["--out", str(out)])
        r = run(["--out", str(out), "--force"])
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_include_image_prompt(self):
        out = self.root / "with-schema"
        r = run(["--out", str(out), "--include-image-prompt"])
        self.assertEqual(r.returncode, 0, r.stderr)
        schema = out / "skills/hyperframes/references/image-prompt-schema.md"
        checker = out / "skills/hyperframes/scripts/check_image_prompt_schema.py"
        self.assertTrue(schema.is_file())
        self.assertTrue(checker.is_file())
        man = json.loads((out / "TRANSPLANT_MANIFEST.json").read_text(encoding="utf-8"))
        self.assertTrue(man.get("include_image_prompt"))
        paths = {f["path"] for f in man["files"]}
        self.assertIn("skills/hyperframes/references/image-prompt-schema.md", paths)
        self.assertGreaterEqual(len(man["files"]), 8)


if __name__ == "__main__":
    unittest.main(verbosity=2)
