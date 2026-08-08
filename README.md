# Open Data Warehouse Format

ODFW is an additive profile of OKF v0.2 for describing data warehouses as portable, inspectable systems — topology, contracts, lineage, quality evidence, and operating ownership — without becoming a warehouse engine.

```text
OKF  — knowledge and trust
EMF  — human intent and durable memory
ORF  — research and findings
OPF  — product commitments, UX, slices, and proof
ODFW — warehouse structure, contracts, lineage, and proof
```

It exists because warehouse programs fail the same way without mechanical rules: agents trust static registries as live data, treat published gold as the oracle, compare scalars instead of vectors, ignore definitional exclusions, hardcode entity names, and ship "green" without re-derivation proof. Those failures become **format rules** here.

See [SPEC.md](SPEC.md) (as implemented), [V1.md](V1.md) (roadmap), and [TESTING-AND-CONNECTORS.md](TESTING-AND-CONNECTORS.md) (ODCS/datacontract-cli defaults, adapters). Public fixture: [examples/minimal](examples/minimal).

```bash
python3 -m odfw.validate --selftest
python3 -m odfw.validate --strict examples/minimal
```

## Public vs private packs

| Lives here (public) | Lives elsewhere (private) |
|---|---|
| SPEC, validator, AGENTS | Real warehouse topology, hosts, recipes, metric contracts |
| Fictional `examples/minimal` | Org-private pack repos (one warehouse per pack) |

**Do not** check customer or portfolio warehouse packs into this repository. A pack is a separate private repo (or a path inside a private warehouse monorepo) that *depends on* this format.

## Status

**v0.2.0 draft.** Schema and validator exist. No compatibility promise until a second independent warehouse pack validates cleanly against the public format.

## Install (optional)

```bash
cd path/to/odfw
pip install -e .
odfw-validate --selftest
```
