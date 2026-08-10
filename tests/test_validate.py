"""Tests for odfw.validate (stdlib unittest)."""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from shutil import copytree
from tempfile import TemporaryDirectory

from odfw.validate import main, validate_path

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "minimal"
PROGRESS = ROOT / "examples" / "row-progress"


class ValidateTests(unittest.TestCase):
    def test_selftest(self) -> None:
        self.assertEqual(main(["--selftest"]), 0)

    def test_minimal_example_draft(self) -> None:
        reports = validate_path(EXAMPLE, strict=False)
        self.assertEqual(len(reports), 1)
        errs = reports[0].errors
        self.assertFalse(errs, "\n".join(f"{e.rule}: {e.detail}" for e in errs))

    def test_minimal_example_strict(self) -> None:
        self.assertEqual(main(["--strict", str(EXAMPLE)]), 0)

    def test_sql_write_forbidden(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "log.md").write_text("# l\n", encoding="utf-8")
            (root / "index.md").write_text(
                """---
okf_version: "0.2"
odfw_version: "0.2.1"
type: warehouse
odfw_id: odfw:w:warehouse
title: "w"
status: inventory
verified:
  by: human:daniel
  at: 2026-08-07
  method: "t"
  stale_after: 2027-01-01
---
""",
                encoding="utf-8",
            )
            (root / "concepts").mkdir()
            (root / "concepts" / "p.md").write_text(
                """---
okf_version: "0.2"
odfw_version: "0.2.1"
type: warehouse-concept
odfw_id: odfw:w:sql-packet:bad
kind: sql-packet
title: "bad"
basis: bronze
posture: select-only
sql_body: "DELETE FROM t"
verified:
  by: human:daniel
  at: 2026-08-07
  method: "t"
---
""",
                encoding="utf-8",
            )
            rep = validate_path(root, strict=True)[0]
            self.assertTrue(any(p.rule == "sql.write" for p in rep.errors))

    def test_progress_fixture_passes(self) -> None:
        self.assertEqual(main(["--progress", str(PROGRESS)]), 0)

    def test_progress_silent_omit_fails(self) -> None:
        with TemporaryDirectory() as tmp:
            dest = Path(tmp) / "pack"
            copytree(PROGRESS, dest)
            man = dest / "evidence" / "demo_metric-progress.json"
            cells = json.loads(man.read_text(encoding="utf-8"))
            man.write_text(json.dumps([cells[0]], indent=2) + "\n", encoding="utf-8")
            self.assertEqual(main(["--progress", str(dest)]), 1)

    def test_progress_absent_manifests_fails(self) -> None:
        """Explicit --progress with zero progress files is not fair (not green)."""
        with TemporaryDirectory() as tmp:
            dest = Path(tmp) / "empty_pack"
            dest.mkdir()
            (dest / "evidence").mkdir()
            (dest / "evidence" / "prove-window.json").write_text(
                '{"period_start":"2025-01","period_end":"2025-01"}\n',
                encoding="utf-8",
            )
            self.assertEqual(main(["--progress", str(dest)]), 1)

    def test_progress_rejects_path_escape(self) -> None:
        """Absolute paths and .. traversal cannot satisfy evidence existence."""
        with TemporaryDirectory() as tmp:
            dest = Path(tmp) / "pack"
            copytree(PROGRESS, dest)
            outside = Path(tmp) / "outside.md"
            outside.write_text("not in pack\n", encoding="utf-8")
            man = dest / "evidence" / "demo_metric-progress.json"
            cells = json.loads(man.read_text(encoding="utf-8"))
            cells[0]["result"] = str(outside.resolve())
            man.write_text(json.dumps(cells, indent=2) + "\n", encoding="utf-8")
            self.assertEqual(main(["--progress", str(dest)]), 1)

            cells[0]["result"] = "../outside.md"
            man.write_text(json.dumps(cells, indent=2) + "\n", encoding="utf-8")
            self.assertEqual(main(["--progress", str(dest)]), 1)


if __name__ == "__main__":
    unittest.main()
