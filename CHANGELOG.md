# Changelog

## 0.2.5 — 2026-08-10

- Correct the canonical acronym to ODWF: Open Data Warehouse Format
- Canonical Python package, CLI, fields, IDs, and inventory schema now use `odwf`
- Preserve read compatibility for legacy `odfw` packages, commands, fields, IDs, and inventories

## 0.2.4 — 2026-08-10

- Source-complete workbook row inventory contract (`odwf-row-inventory-v1`)
- Separate physical-row and metric-row denominators with exact reconciliation
- Structural row roles and semantic metric kinds; unresolved classifications fail strict validation
- Cold, stdlib-only `odwf-validate --inventory --strict` validation without reopening Excel

## 0.2.3 — 2026-08-08

- **SPEC §8a** — spreadsheet-derived metrics: **row-first chronological** prove (normative); per-cell evidence; explicit non-calc classification
- Rationale: column-first thrash; row keeps definition/authority/calc context across the series
- Result outcomes: `NOT_APPLICABLE`, `SOURCE_ONLY`, `CARRIED_STRUCTURAL`; optional `non_calc_class`
- Validator accepts new outcomes; requires `notes` for non-calc (warn / strict error)
- **§8a.5** — incomplete warehouse years: consult **designated complementary source** (e.g. GMS) before FAIL on empty bronze; record present/absent; non-calc ≠ skipped GMS lookup
- Prospective + current path only — no bulk migration of historical results
- INTENTION + AGENTS cross-links

## 0.2.2 — 2026-08-07

- Kinds: `data-contract`, `connector`
- `check.engine` + bind to ODCS/datacontract-cli (default external test runner)
- See TESTING-AND-CONNECTORS.md

## 0.2.1 — 2026-08-07

- Kinds: `sql-packet`, `check`, `test`, `result`, `workbook` (+ strengthened `answer-key` explorer pins)
- Validator gates: SELECT-only SQL, sql_path resolution, check compare, test steps, result outcomes, workbook tool
- Public minimal example exercises packet/check/test/result
- Slice may prove via sql-packet + check (not only recipe + metric-contract)

## 0.2.0 — 2026-08-07

First draft of ODWF as an additive OKF v0.2 profile.

- SPEC: warehouse face, atomic kinds, oracle/serving honesty, metric-contracts, vector triangulation verdicts, lifecycle gates
- Stdlib validator with `--selftest` and `--strict`
- Public fixture only: `examples/minimal` (fictional)
- Private warehouse packs are **out of scope** for this repo; they live in private org repositories and consume this format
- **V1.md** — format north star: sql-packet, check, test, result, workbook pins (eidos-spreadsheet-explorer), proof ladder
