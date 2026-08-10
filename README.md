# Open Data Warehouse Format

ODWF is an additive profile of OKF v0.2 for **self-contained packages that prove an original spreadsheet against bronze warehouse data**.

```text
OKF  — knowledge and trust
EMF  — human intent and durable memory
ORF  — research and findings
OPF  — product commitments, UX, slices, and proof
ODWF — spreadsheet → bronze proof packages (portable, fail-closed)
OPFF — personal finance packs (https://github.com/eidos-agi/opff; not warehouse proof)
```

## Intention (read this first)

**[INTENTION.md](INTENTION.md)** is load-bearing:

1. **Proof direction:** original spreadsheet (explorer-pinned) → **bronze** arbiter.  
2. **Seeds** ship in the pack when needed — labeled, not fake bronze.  
3. **Self-contained** — no coupling to a particular metrics app; learn patterns elsewhere freely.  
4. **Gold / MCP / dashboards** are not the core prove path.  
5. **Downstream:** a complete pack is what an AI can compile into a full analytics metrics package without re-paying discovery months.

Mechanical rules: [SPEC.md](SPEC.md). Language roadmap: [V1.md](V1.md). Connectors/DQ compose: [TESTING-AND-CONNECTORS.md](TESTING-AND-CONNECTORS.md). Fixture: [examples/minimal](examples/minimal).

```bash
python3 -m odwf.validate --selftest
python3 -m odwf.validate --strict examples/minimal
python3 -m odwf.validate --inventory --strict /path/to/private-pack
```

## Public vs private packs

| Lives here (public) | Lives elsewhere (private) |
|---|---|
| SPEC, validator, INTENTION, docs | Real workbooks, SQL, seeds, hosts, results |
| Fictional `examples/minimal` | Org-private pack repos (one warehouse + sheet corpus per pack) |

**Do not** check customer/portfolio packs into this repository.

## Status

**v0.2.5 draft.** Schema and validator exist. Intention is spreadsheet→bronze packages (row-first chronological prove for sheet metrics — SPEC §8a) as AI compile input for later metrics stacks.

## Install (optional)

```bash
cd path/to/odwf
pip install -e .
odwf-validate --selftest
```

New packs use `odwf_version`, `odwf_id`, `odwf:` IDs, and the `odwf-row-inventory-v1`
schema. The former `odfw` Python package, CLI, fields, IDs, and inventory schema remain
read-compatible so published pack identities do not have to change.

Row inventories may set `claim_level: semantic` and embed an `odwf-row-semantics-v1`
contract; `odwf-validate --inventory` then reconciles every row rule, period outcome,
comparison rule, and lineage summary without opening the workbook.
