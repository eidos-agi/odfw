# ODFW intention

**Status:** load-bearing product intention for the public format  
**Instance dogfood:** private packs (e.g. `cerebro-odfw-v1`) must share this intention  

---

## One sentence

ODFW is the open format for **self-contained packages that prove an original spreadsheet against bronze warehouse data** — so a completed pack is simple, falsifiable, and rich enough that an AI can later compile it into a full analytics metrics package.

---

## Proof direction

```text
original spreadsheet (starting, often hardcoded)
        │  pin via eidos-spreadsheet-explorer
        │  (xlsx + md5 + facts_digest — not whole-sheet dump)
        ▼
   package claims + recipes + seeds
        │  re-derive / match
        ▼
   bronze (oracle for this proof)
```

| Side | Role |
|---|---|
| **Spreadsheet** | Source of the *claim* — the original starting workbook (explorer export) |
| **Bronze** | Arbiter — re-derive and compare |
| **Seeds** | First-class when bronze alone cannot honest-claim a cell; never laundered as bronze |
| **Gold / silver / dashboards** | **Out of the core prove story** until later; gold is under test, not the target |
| **MCP / static registries** | Catalog hints only — never values |

---

## Self-contained package (not a product coupling)

A private ODFW pack ships everything needed to re-run the prove path:

- pinned workbook + explorer sidecars  
- topology (host, credential-plane, bronze schemas/tables)  
- sql-packets / recipes  
- seeds, entity-maps, exclusion-sets as needed  
- checks, tests, append-only results  

**No runtime dependency** on any particular app (e.g. GreenmarkSheets).  
Patterns may be **learned** from prior reconciles; the pack must not **couple** its identity or execution to those products.

---

## Why this is simpler and more provable

Two sides only for the core claim. Falsifiable in one sentence:

> For this sheet vector (explorer facts @ md5), bronze re-derives the same numbers within tolerance — or the cell is **seed** / **NOT_DERIVABLE** with reason.

No “gold is green,” no “the dashboard agreed,” no product-UI false green.

---

## Downstream intention (AI compile target)

A **complete** pack is the compile input for a later analytics metrics package:

| Pack supplies | AI / engineering can produce |
|---|---|
| Sheet claims + digests | Metric catalog of *what was proven* |
| Bronze recipes / SQL | Models/tests that implement those recipes |
| Seeds (labeled) | Explicit non-source rules in the metrics package |
| Checks + results | Automated tests and regression baselines |
| Grain / series / tolerance | Metric shape |

The format does not *be* the analytics stack (dbt/Dagster/serving). It makes that stack **authorable from evidence** instead of months of rediscovery.

---

## What ODFW is not

- A warehouse engine or credential vault  
- A gold publish pipeline  
- A coupling to any one metrics UI product  
- A place to store production pack instances (those stay private)

---

## Related

- [SPEC.md](SPEC.md) — mechanical rules  
- [V1.md](V1.md) — language roadmap  
- [TESTING-AND-CONNECTORS.md](TESTING-AND-CONNECTORS.md) — ODCS/datacontract for connectivity/DQ, not sheet identity  
- Private pack TARGET/PLAN — instance dogfood of this intention  
