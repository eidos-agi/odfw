# Open Data Warehouse Format

ODFW is an additive OKF profile for **spreadsheet → bronze** proof packages — not a warehouse engine, credentials store, or metrics UI.

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
- Exclusion sets, entity maps, and **seeds** are first-class; never launder seeds as bronze.  
- Credentials never appear in pack documents — only `credential-plane` locators.  
- Serving planes declare what they are *not* authoritative for.  
- Concepts atomic, IDs stable, directed composition membership.  
- Add fields only for observed failures; validator stdlib-only for gates.  
- `python3 -m odfw.validate --strict` before calling a pack published.  
- **Never commit private warehouse packs here.**  
- Language roadmap: [V1.md](V1.md). Connectors: [TESTING-AND-CONNECTORS.md](TESTING-AND-CONNECTORS.md).  
