"""Tests for odwf.validate (stdlib unittest)."""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from shutil import copytree
from tempfile import TemporaryDirectory

from odfw.validate import main as legacy_main
from odwf.validate import main, validate_path

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

    def test_legacy_odfw_names_remain_readable(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp) / "legacy"
            copytree(EXAMPLE, root)
            for path in root.rglob("*.md"):
                text = path.read_text(encoding="utf-8")
                path.write_text(text.replace("ODWF", "ODFW").replace("odwf", "odfw"), encoding="utf-8")
            self.assertEqual(legacy_main(["--strict", str(root)]), 0)

    def test_sql_write_forbidden(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "log.md").write_text("# l\n", encoding="utf-8")
            (root / "index.md").write_text(
                """---
okf_version: "0.2"
odwf_version: "0.2.1"
type: warehouse
odwf_id: odwf:w:warehouse
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
odwf_version: "0.2.1"
type: warehouse-concept
odwf_id: odwf:w:sql-packet:bad
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

    def _write_row_inventory(self, root: Path) -> Path:
        evidence = root / "evidence"
        evidence.mkdir(parents=True)
        path = evidence / "demo-row-inventory.json"
        path.write_text(
            json.dumps(
                {
                    "schema_version": "odwf-row-inventory-v1",
                    "workbook": {
                        "source_basename": "demo.xlsx",
                        "source_md5": "0123456789abcdef0123456789abcdef",
                        "sheet": "Metrics",
                        "sheet_dimension": "A1:C3",
                    },
                    "counts": {
                        "physical_rows": 3,
                        "metric_rows": 1,
                        "row_roles": {"title": 1, "column_header": 1, "metric": 1},
                        "metric_kinds": {"source_input": 1},
                    },
                    "rows": [
                        {
                            "sheet_row": 1,
                            "row_label": "Demo",
                            "row_role": "title",
                            "metric_kind": None,
                            "metric_id": None,
                            "included_in_metric_denominator": False,
                            "classification_basis": "workbook title",
                            "cells": [{"a1": "A1", "value": "Demo"}],
                        },
                        {
                            "sheet_row": 2,
                            "row_label": "Month",
                            "row_role": "column_header",
                            "metric_kind": None,
                            "metric_id": None,
                            "included_in_metric_denominator": False,
                            "classification_basis": "month headings",
                            "cells": [{"a1": "A2", "value": "Month"}],
                        },
                        {
                            "sheet_row": 3,
                            "row_label": "Units",
                            "row_role": "metric",
                            "metric_kind": "source_input",
                            "metric_id": "r003_units",
                            "included_in_metric_denominator": True,
                            "classification_basis": "monthly numeric series",
                            "cells": [{"a1": "A3", "value": "Units"}, {"a1": "C3", "value": 7}],
                        },
                    ],
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        return path

    def test_row_inventory_passes_cold(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_row_inventory(root)
            self.assertEqual(main(["--inventory", "--strict", str(root)]), 0)

    def test_legacy_odfw_inventory_schema_remains_readable(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = self._write_row_inventory(root)
            data = json.loads(path.read_text(encoding="utf-8"))
            data["schema_version"] = "odfw-row-inventory-v1"
            path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
            self.assertEqual(legacy_main(["--inventory", "--strict", str(root)]), 0)

    def test_row_inventory_denominators_fail_closed(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = self._write_row_inventory(root)
            data = json.loads(path.read_text(encoding="utf-8"))
            data["counts"]["metric_rows"] = 2
            path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
            self.assertEqual(main(["--inventory", str(root)]), 1)

    def test_row_inventory_requires_exact_physical_coverage(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = self._write_row_inventory(root)
            data = json.loads(path.read_text(encoding="utf-8"))
            data["rows"][1]["sheet_row"] = 3
            data["rows"][1]["cells"][0]["a1"] = "A3"
            path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
            self.assertEqual(main(["--inventory", str(root)]), 1)

    def test_row_inventory_unknown_fails_strict(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = self._write_row_inventory(root)
            data = json.loads(path.read_text(encoding="utf-8"))
            data["rows"][1]["row_role"] = "unknown"
            data["counts"]["row_roles"] = {"title": 1, "unknown": 1, "metric": 1}
            path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
            self.assertEqual(main(["--inventory", str(root)]), 0)
            self.assertEqual(main(["--inventory", "--strict", str(root)]), 1)

    def test_row_inventory_unclear_metric_fails_strict(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = self._write_row_inventory(root)
            data = json.loads(path.read_text(encoding="utf-8"))
            data["rows"][2]["metric_kind"] = "unclear"
            data["counts"]["metric_kinds"] = {"unclear": 1}
            path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
            self.assertEqual(main(["--inventory", str(root)]), 0)
            self.assertEqual(main(["--inventory", "--strict", str(root)]), 1)


if __name__ == "__main__":
    unittest.main()
