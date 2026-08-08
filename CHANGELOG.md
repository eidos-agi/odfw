# Changelog

## 0.2.1 — 2026-08-07

- Kinds: `sql-packet`, `check`, `test`, `result`, `workbook` (+ strengthened `answer-key` explorer pins)
- Validator gates: SELECT-only SQL, sql_path resolution, check compare, test steps, result outcomes, workbook tool
- Public minimal example exercises packet/check/test/result
- Slice may prove via sql-packet + check (not only recipe + metric-contract)

## 0.2.0 — 2026-08-07

First draft of ODFW as an additive OKF v0.2 profile.

- SPEC: warehouse face, atomic kinds, oracle/serving honesty, metric-contracts, vector triangulation verdicts, lifecycle gates
- Stdlib validator with `--selftest` and `--strict`
- Public fixture only: `examples/minimal` (fictional)
- Private warehouse packs are **out of scope** for this repo; they live in private org repositories and consume this format
- **V1.md** — format north star: sql-packet, check, test, result, workbook pins (eidos-spreadsheet-explorer), proof ladder
