"""Tests for odfw.validate."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from odfw.validate import main, validate_path

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "minimal"


def test_selftest() -> None:
    assert main(["--selftest"]) == 0


def test_minimal_example_draft() -> None:
    reports = validate_path(EXAMPLE, strict=False)
    assert len(reports) == 1
    errs = reports[0].errors
    assert not errs, "\n".join(f"{e.rule}: {e.detail}" for e in errs)


def test_minimal_example_strict() -> None:
    assert main(["--strict", str(EXAMPLE)]) == 0


def test_sql_write_forbidden() -> None:
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
        assert any(p.rule == "sql.write" for p in rep.errors)
