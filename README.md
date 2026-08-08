# Open Data Warehouse Format

ODFW is an additive profile of OKF v0.2 for **self-contained packages that prove an original spreadsheet against bronze warehouse data**.

```text
OKF  — knowledge and trust
EMF  — human intent and durable memory
ORF  — research and findings
OPF  — product commitments, UX, slices, and proof
ODFW — spreadsheet → bronze proof packages (portable, fail-closed)
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
python3 -m odfw.validate --selftest
python3 -m odfw.validate --strict examples/minimal
```

## Public vs private packs

| Lives here (public) | Lives elsewhere (private) |
|---|---|
| SPEC, validator, INTENTION, docs | Real workbooks, SQL, seeds, hosts, results |
| Fictional `examples/minimal` | Org-private pack repos (one warehouse + sheet corpus per pack) |

**Do not** check customer/portfolio packs into this repository.

## Status

**v0.2.2+ draft.** Schema and validator exist. Intention is spreadsheet→bronze packages as AI compile input for later metrics stacks.

## Install (optional)

```bash
cd path/to/odfw
pip install -e .
odfw-validate --selftest
```
