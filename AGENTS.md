# Open Data Warehouse Format

ODWF is an additive OKF profile for **spreadsheet → bronze** proof packages — not a warehouse engine, credentials store, or metrics UI.

## Intention

Read **[INTENTION.md](INTENTION.md)** first. Summary:

- Prove the **original pinned spreadsheet** (explorer export) against **bronze**.
- Deliver packs **self-contained**, including **seeds** when bronze cannot honest-claim a cell.
- Do **not** couple packs to GreenmarkSheets or any other product — learn patterns only.
- **Gold / MCP / registry values** are not the prove path (gold later / under test).
- A complete pack is the **compile input** for an AI-built analytics metrics package.

## Rules

- Preserve OKF v0.2 trust and provenance.
- Name exactly one **oracle** layer for this prove path — typically **bronze**.
- Prefer live catalog names (`information_schema`) over registry/MCP table strings.
- Metric proof compares **vectors** under a contract, not lucky scalars.
- **Spreadsheet-derived metrics:** prove **row-first** across the relevant date range (period ascending); retain one metric’s definition/authority/calc context; one result per cell; **classify** non-calc periods explicitly (SPEC §8a). Not column-first thrash. Prospective + current path — no bulk rewrite of old results.
- **Incomplete warehouse years (e.g. 2025):** expect missing bronze; look up the pack’s **designated complementary source** (often GMS) **before** FAIL/DQ-blocker. Record whether GMS (or equivalent) supplied evidence. Non-calc outcomes only for true structural/N/A periods — never to skip the GMS lookup. If neither source works: open blocker naming missing source/credential/definition.
- Exclusion sets, entity maps, and **seeds** are first-class; never launder seeds as bronze.
- Credentials never appear in pack documents — only `credential-plane` locators.
- Serving planes declare what they are *not* authoritative for.
- Source correctness is not enough: scheduled providers declare a face-linked `ingestion-contract` with extraction bounds, checkpoint/reconciliation semantics, all source-I/O paths, a provider-scoped aggregate budget, and enforcement proof. `observe` is not prevention.
- Concepts atomic, IDs stable, directed composition membership.
- Add fields only for observed failures; validator stdlib-only for gates.
- **Prove loop (files only):** for source-complete workbook claims, first write `evidence/*-row-inventory.json` and run `python3 -m odwf.validate --inventory --strict .`; then write cell evidence under `results/` (+ `sql/` when calc) and a row `evidence/*-progress.json` covering the full prove window → run `python3 -m odwf.validate --progress .` (must exit 0) → run `python3 -m odwf.validate --strict .` before calling a pack published.
- Progress fairness (SPEC §8a.6): no silent omitted periods; result path every cell; sql path on PASS/FAIL; non-calc classified; no FAIL@≥8 quality inflation.
- External work trackers (issues/boards) are **optional and non-normative** — they do not replace progress files or structural validate.
- **Never commit private warehouse packs here.**
- Language roadmap: [V1.md](V1.md). Connectors: [TESTING-AND-CONNECTORS.md](TESTING-AND-CONNECTORS.md).
