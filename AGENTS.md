# Open Data Warehouse Format

ODFW is an additive OKF profile, not a warehouse, credentials store, or metric database.

- Preserve OKF v0.2 trust and provenance.
- Name exactly one **oracle** layer; for source-complete warehouses that is often **bronze**. Gold is under test.
- Prefer **live catalog names** (`information_schema`) over registry/MCP table strings.
- Metric proof compares **vectors** under a ratified `metric-contract`, not lucky scalars.
- Exclusion sets and entity maps are concepts; do not re-derive gold while ignoring them.
- Credentials never appear in pack documents — only `credential-plane` locators.
- Serving planes declare what they are *not* authoritative for (catalog/cache/MCP honesty).
- Link EMF intent and ORF research; do not impersonate either.
- Concepts are atomic, IDs stable, references resolvable, membership via directed composition edges.
- Add a field or rule only for an observed failure; keep the validator stdlib-only.
- Run `python3 -m odfw.validate --strict` before calling a pack published.
- **Never commit private warehouse packs here.** Real packs (hosts, providers, recipes, customer metrics, SQL, results) belong in private org repos. This repo stays format + fictional fixtures only.
- Build the **language** toward [V1.md](V1.md): sql-packet, check, test, result, workbook/answer-key pins to eidos-spreadsheet-explorer. Private packs carry instance TARGET files.
