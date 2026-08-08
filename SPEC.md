# ODFW v0.2.2 — Open Data Warehouse Format

**An additive profile of OKF v0.2.** Every ODFW document preserves OKF provenance and trust. OKF renderers may ignore ODFW fields and still display the documents.

```text
OKF  — knowledge and trust
EMF  — human intent and durable memory
ORF  — approved research and graded findings
OPF  — product commitments, experience, slices, and proof
ODFW — warehouse topology, contracts, lineage, quality evidence, and ownership
```

ODFW composes these formats; it does not merge them. Human intent remains EMF. Research remains ORF. Product surfaces remain OPF. ODFW owns the portable description of a data warehouse as an inspectable system: what sources land, what layers mean, which plane is the oracle, how metrics are contracted, how proof is produced, and who may touch what.

If a requirement conflicts with OKF v0.2, **OKF wins for base structure**. ODFW only adds required frontmatter, pack layout conventions, warehouse concept kinds, and biting gates.

---

## 1. Why ODFW exists (measured failures)

Each addition exists because a failure was felt or measured on real multi-vendor warehouse programs — not because medallion orthodoxy looks tidy.

| Observed failure | ODFW rule |
|---|---|
| Agents treat a **static registry/MCP** as live warehouse truth; stale names (`sage_bronze.gl_journal_entries` vs real `dd5_sage_bronze.gl_entries`) poison recipes | `serving-plane` objects declare what they are (catalog / cache / live query). Live names resolve from `information_schema` (or equivalent), never from catalog prose alone |
| **Gold is partial and may be wrong**, yet agents use gold (or the registry snapshot of gold) as the oracle | Every warehouse names exactly one `oracle` layer. When bronze is complete and gold is partial, the oracle is **bronze**. Gold is under test |
| A single month/scalar match hides series conflation and forecast holes | Metric proof compares **vectors** (grain series), not baselines |
| Intentional **exclusions** (one-offs) are flagged as "gold wrong" by raw bronze sums | Exclusion sets are first-class `exclusion-set` concepts; recipes that claim to match gold **must** reference them |
| Hardcoded location strings break on renames (`Hometown` → `Memphis`) | Entity resolution goes through an `entity-map` concept with version, never free-text location filters alone |
| Summing all series for a metric **double-counts** (~$3.4M class error) | A metric pins exactly one live `series` (or an explicit multi-series composition with proof of no double-count) |
| Decommissioned substrates (v4 Supabase, disabled repos) keep getting used | Pack face lists `retired_substrates`; validators warn on references into them |
| Host alias drift (stale MagicDNS name → current primary) breaks "proven" connection recipes | `host` concepts carry durable selection rules and alias maps |
| Credentials printed into chat; agents invent connection paths | Credential material is **never** in ODFW docs; only `credential-plane` pointers (Knox/Vault/path-on-host) |
| Fan-out of 10 metric rows thrash before any recipe lands | Slice discipline: one `metric-contract` or one provider closure at a time until a recipe is proven |
| Answer-key / workbook values quietly become the "bronze recipe" | `answer-key` is a separate evidence plane; recipes that depend on it must declare `basis: answer-key` and cannot claim `basis: bronze` |
| Registry ships without values; MCP answers from an old substrate | Publish paths are explicit `publish-path` chains with freshness and plane-of-record |
| "Shipped" without re-derivation proof | Acceptance for a metric requires a triangulation verdict with evidence pointers |

ODFW is the place those rules become mechanical — so the next agent does not relearn them from a 180-line skill after another false green.

---

## 2. Relationship to siblings

| Layer | Owns |
|---|---|
| **OKF** | Bundle tree, `index.md` / `log.md`, concept = markdown + frontmatter, trust ladder, `verified`, `sources` |
| **EMF** | Human intent (`type: intent`), altitude, concerns — what the warehouse is *for* as stated by a human |
| **ORF** | Investigations that discover recipes, failure modes, prior art — graded findings agents may promote |
| **OPF** | Product faces (dashboards, sheets) that *consume* warehouse outputs |
| **ODFW** | Warehouse structure, data contracts, lineage, transforms, quality evidence, operating ownership |

```text
OKF v0.2
├── EMF   — memory (intent / claims / altitude)
├── ORF   — research / investigation packs
├── OPF   — product commitments and UX proof
├── ODDF  — capital diligence (out of scope)
└── ODFW  — data warehouse portability and proof
```

**Compose, don't merge.** A metric face may link `intent: emf:…`, `research: orf:…`, and `product: opf:…`. It does not restate human intent or invent product promises.

---

## 3. Unit of distribution

One ODFW pack defines **one warehouse** or one **independently governed warehouse domain** (e.g. `acme-ops` vs a second domain that can retire independently).

```text
docs/odfw/                    # or pack root
  index.md                    # required warehouse face
  log.md                      # append-only warehouse-definition history
  concepts/                   # atomic warehouse concepts
    *.md
  evidence/                   # optional extracts, scorecards, sanitized query outputs — no secrets
  contracts/                  # optional home for metric-contract docs (also allowed under concepts/)
```

Folders aid navigation; **IDs and typed references** define the graph. Split a pack when a domain can be governed, versioned, or retired independently.

Default home for a private pack: either a dedicated private pack repo, or `docs/odfw/` inside a private warehouse monorepo. **This public repository ships only the specification, validator, and fictional fixtures.** Real warehouse packs must not be checked in here.

---

## 4. Warehouse face (`index.md`)

```yaml
---
okf_version: "0.2"
odfw_version: "0.2.0"
profile: odfw
type: warehouse
odfw_id: odfw:acme-ops:warehouse
title: "Acme ops warehouse"
status: operating
imports: [emf:acme-data@2026-07-06]
intent: [emf:acme-data:bronze-is-oracle@2026-07-06]
oracle: odfw:acme-ops:oracle:bronze
layers: [odfw:acme-ops:layer:bronze, odfw:acme-ops:layer:silver, odfw:acme-ops:layer:gold]
providers: [odfw:acme-ops:provider:erp, odfw:acme-ops:provider:ops]
hosts: [odfw:acme-ops:host:primary-postgres]
credential_plane: odfw:acme-ops:credential-plane:vault
authority: [odfw:acme-ops:authority:select-only-prod]
serving_planes: [odfw:acme-ops:serving:live-pg, odfw:acme-ops:serving:registry-mcp]
publish_paths: [odfw:acme-ops:publish:gold-to-app]
first_slice: odfw:acme-ops:slice:revenue-prove
non_goals: ["public TCP proxy for the financial DB", "gold as oracle", "writing to production from agents"]
retired_substrates: ["legacy-v4-manifest", "retired-cloud-db as warehouse of record"]
proof: [odfw:acme-ops:acceptance:bronze-probe]
verified:
  by: human:daniel
  at: 2026-08-07
  method: "illustrative face — real packs stay in private repos"
  stale_after: 2027-02-07
---
```

### Lifecycle gates

| status | mechanical meaning |
|---|---|
| `inventory` | face named; incomplete structure allowed |
| `contracting` | oracle, layers, at least one provider, host, credential_plane, authority resolve |
| `implementing` | contracting plus first_slice with a complete proof path for at least one metric-contract |
| `proving` | implementing plus at least one acceptance with `status: observed` and pinned evidence |
| `operating` | proving plus freshness/heartbeat concepts and no live references into `retired_substrates` |
| `retired` | `retirement_reason` required; historical pack remains readable |

Lifecycle is not percent complete. Placeholder values (`TBD`, `TODO`, `later`, `unknown`, `n/a`) do not satisfy admission.

---

## 5. Atomic concepts and IDs

Every non-face document uses:

```yaml
type: warehouse-concept
odfw_id: odfw:<warehouse>:<kind>:<slug>
kind: metric-contract
```

Allowed `kind` values:

| kind | Meaning |
|---|---|
| `provider` | External system that lands data (Sage, Navusoft, Fleetio, …) |
| `layer` | Medallion or equivalent plane with semantics (bronze/silver/gold/…) |
| `oracle` | The layer (or surface) that arbitrates truth for verification |
| `schema` | Named schema in the live store |
| `table` | Named relation; physical name from live catalog |
| `column` | Optional column-level contract when needed |
| `entity-map` | Versioned mapping of business entities ↔ source keys |
| `exclusion-set` | Definitional exclusions (one-offs, CFO carve-outs) |
| `seed` | Attested rule/seed not re-derived from bronze |
| `pipeline` | Ingestion or transform runner (dlt, dbt, Dagster job) |
| `transform` | Named transform/model with inputs → outputs |
| `recipe` | Reproducible derivation steps for a metric or table |
| `measure` | Unit/definition of a measured quantity |
| `metric` | Business metric identity (catalog id, grain, semantics) |
| `series` | One published series for a metric (entity × period grain) |
| `metric-contract` | Ratified verification contract for one metric |
| `serving-plane` | How consumers read data (live SQL, registry, MCP, dashboard cache) |
| `publish-path` | Ordered chain warehouse → serving surfaces |
| `host` | Runtime host / connection target with alias rules |
| `credential-plane` | Where secrets live (never the secret) |
| `freshness` | Heartbeat / SLA / dead-man for a source or layer |
| `authority-boundary` | Who may read/write/DDL; network posture |
| `slice` | Bounded delivery unit (one provider closure, one metric family) |
| `acceptance` | Falsifiable proof gate with status and evidence |
| `verdict` | Result of a triangulation run (append-only evidence) |
| `decision` | Explicit warehouse decision record |
| `risk` | Known failure mode still in force |
| `answer-key` | External workbook / human reference plane (not bronze); prefer explorer pins |
| `workbook` | Workbook plane pin (spreadsheet-explorer); alias of answer-key with required tool pins |
| `sql-packet` | Named SELECT query packet (body or path), basis-tagged |
| `check` | Executable assertion (vector/peers/tolerance) |
| `test` | Ordered procedure binding packets + checks |
| `result` | Append-only observation of a test/check run |
| `data-contract` | Pin to ODCS (or compatible) contract file + server id |
| `connector` | Get-online adapter pin (odcs-server / datacontract / adbc / …) |

IDs match `odfw:<warehouse>:<kind>:<slug>` (additional stable segments allowed), are unique in the validation closure, and **never change after publication**. A new interpretation gets a new ID and explicit `supersedes` / `superseded_by` (both edges, matching kinds, one live head).

One document makes one warehouse assertion someone could dispute, supersede, implement, or test.

---

## 6. Directed typed edges

Field names are edge types. The validator checks direction and target kind.

| source field | required target kind(s) |
|---|---|
| `oracle` | `oracle` |
| `layers` | `layer` |
| `providers` | `provider` |
| `hosts` | `host` |
| `credential_plane` | `credential-plane` |
| `authority` | `authority-boundary` |
| `serving_planes` | `serving-plane` |
| `publish_paths` | `publish-path` |
| `first_slice` | `slice` |
| `proof`, `validation`, `operational_proof` | `acceptance` |
| `metric` | `metric` |
| `series` | `series` |
| `recipe` | `recipe` |
| `sql_packet` / `sql_packets` | `sql-packet` |
| `check` / `checks` | `check` |
| `test` / `tests` | `test` |
| `results` | `result` |
| `entity_map` | `entity-map` |
| `exclusions` | `exclusion-set` |
| `transforms` | `transform` |
| `tables` | `table` |
| `schemas` | `schema` |
| `pipeline` | `pipeline` |
| `freshness` | `freshness` |
| `lands_in` | `schema`, `table`, `layer` |
| `reads_from` | `table`, `schema`, `layer`, `serving-plane` |
| `writes_to` | `table`, `schema`, `layer`, `serving-plane` |
| `depends_on` | any concept kind |
| `serves` | `metric`, `series`, `slice`, `publish-path` |
| `includes` | journey-equivalent warehouse set (see slice rules) |
| `basis` | not an edge — scalar enum on recipes (see §8) |
| `supersedes` / `superseded_by` | same kind |

Only **composition edges** from the face and admitted structures make a document a member of the warehouse definition. A dangling risk that merely `depends_on` a metric does not join the pack by back-reference alone.

Composition fields from the face:

`providers`, `layers`, `oracle`, `hosts`, `credential_plane`, `authority`, `serving_planes`, `publish_paths`, `first_slice`, `proof`, `validation`, `operational_proof`.

---

## 7. Oracle, layers, and serving planes

### Oracle

```yaml
kind: oracle
layer: odfw:acme-ops:layer:bronze
rule: "Bronze is complete and trusted; gold is under test. Never validate gold with gold."
```

A warehouse face MUST name exactly one `oracle`. Recipes and metric-contracts that claim live verification MUST be re-derivable against that oracle (or declare a different `basis` honestly).

### Layer semantics (required fields)

```yaml
kind: layer
layer_name: bronze          # free string; bronze|silver|gold recommended
role: source-shaped         # source-shaped | semantic | published | other
trusted_as_oracle: true     # at most one layer in the pack should be true; oracle concept points here
```

### Serving plane honesty

```yaml
kind: serving-plane
plane_kind: live-query      # live-query | catalog | cache | mcp | dashboard | workbook
authoritative_for: []       # what may be trusted from this plane
not_authoritative_for: ["metric values", "table names"]
stale_risk: high
```

**Gate:** a `serving-plane` with `plane_kind` in `{catalog, cache, mcp, dashboard}` MUST list metric values or physical table names under `not_authoritative_for` unless an explicit `authoritative_for` + acceptance proves otherwise. This encodes the static-catalog-as-live-data failure in the format.

---

## 8. Recipes, contracts, and triangulation

### Recipe

```yaml
kind: recipe
basis: bronze               # bronze | silver | gold | answer-key | hybrid
inputs: [odfw:…:table:gl-entries, odfw:…:exclusion-set:known]
outputs: [odfw:…:series:revenue-lob-total]
entity_map: odfw:…:entity-map:locations
exclusions: [odfw:…:exclusion-set:known]
grain: [entity_id, period]
notes: "signed by tr_type; revenue = -sum(amount*tr_type)"
```

**Gates:**

1. `basis: bronze` recipes MUST NOT list only answer-key inputs.
2. `basis: answer-key` recipes MUST NOT be used as sole proof that gold is correct.
3. Recipes that claim to reproduce gold semantics MUST reference the exclusion-set and entity-map used by gold (when those concepts exist in the pack).

### Metric contract

```yaml
kind: metric-contract
metric: odfw:acme-ops:metric:revenue
series: odfw:acme-ops:series:lob-total
recipe: odfw:acme-ops:recipe:revenue-lob
tolerance:
  mode: display-half-ulp    # display-half-ulp | absolute | relative
  value: null               # absolute/relative only
compare: vector             # vector | scalar — scalar is warn in draft, error in strict for operating packs
oracle: odfw:acme-ops:oracle:bronze
answer_key: odfw:acme-ops:answer-key:finance-workbook   # optional third plane
proof: [odfw:acme-ops:acceptance:revenue-lob]
```

### Acceptance and verdict

```yaml
kind: acceptance
condition: "Bronze re-derivation vector matches answer-key and live gold within tolerance for series M011"
status: proposed            # proposed | observed | failed
evidence: []                # required when observed or failed
```

```yaml
kind: verdict
metric_contract: odfw:…:metric-contract:revenue-lob
at: 2026-07-06
result: PROVEN              # PROVEN | GOLD_WRONG | RECHECK | NOT_DERIVABLE | REGISTRY_STALE
bronze_vs_key: match
bronze_vs_gold: match
gold_vs_registry: diverge
notes: "Registry June NTX was stale; live gold matched bronze"
```

Triangulation vocabulary (normative meanings):

| result | Meaning |
|---|---|
| `PROVEN` | bronze ↔ key ↔ live gold agree (under contract) |
| `GOLD_WRONG` | bronze = key, ≠ live gold |
| `RECHECK` | bronze = gold, ≠ key (spec / source-copy) |
| `NOT_DERIVABLE` | could not re-derive — fail loud |
| `REGISTRY_STALE` | live gold ≠ serving catalog/cache |

### SQL packet

```yaml
kind: sql-packet
basis: bronze
sql_path: sql/revenue-lob.sql    # relative to pack root; OR sql_body inline
grain: [entity_id, period]
inputs: [odfw:…:table:gl-entries]
entity_map: odfw:…:entity-map:locations
exclusions: [odfw:…:exclusion-set:known]
posture: select-only             # required; writes forbidden
```

**Gates:** `basis` required (same enum as recipe); `sql_path` or nonempty `sql_body`; posture must be `select-only`; secrets heuristic applies to packet body/files when present in pack; `basis: bronze` cannot be answer-key-only inputs.

The validator does **not** execute SQL. Harnesses do.

### Check

```yaml
kind: check
engine: datacontract          # datacontract | dbt | great-expectations | soda | sql-packet | custom
data_contract: odfw:…:data-contract:…
bind: contracts/gl-entries-bronze.odcs.yaml
```

Or sql-packet triangulation:

```yaml
kind: check
metric_contract: odfw:…:metric-contract:revenue-lob
sql_packet: odfw:…:sql-packet:revenue-lob
compare: vector
tolerance:
  mode: display-half-ulp
peers: [bronze, live-gold, answer-key]   # free strings documenting peer planes
```

**Gates:** `compare` required; `metric_contract` or `sql_packet` required; scalar forbidden under strict for operating packs.

### Test

```yaml
kind: test
title: "First slice revenue prove"
steps: ["run sql-packet revenue-lob", "apply check revenue-lob-vector", "append result"]
sql_packets: [odfw:…:sql-packet:revenue-lob]
checks: [odfw:…:check:revenue-lob-vector]
proof: [odfw:…:acceptance:revenue-lob]
```

**Gates:** at least one of `sql_packets` / `checks` / nonempty `steps`; `steps` must not be placeholder-only.

### Result

```yaml
kind: result
test: odfw:…:test:revenue-prove
check: odfw:…:check:revenue-lob-vector
at: 2026-08-07
by: agent:odfw
outcome: NOT_RUN            # PASS | FAIL | NOT_RUN | BLOCKED | PROVEN | GOLD_WRONG | RECHECK | NOT_DERIVABLE | REGISTRY_STALE
evidence: []
notes: "blocked: warehouse not reached this session"
```

**Gates:** `at`, `by`, `outcome` required. Results are append-only evidence; they need not be composition-reachable from the face. `acceptance.evidence` MAY point at result ids.

### Workbook / answer-key pins (spreadsheet-explorer)

```yaml
kind: answer-key   # or workbook
tool: eidos-spreadsheet-explorer
source_basename: metrics.xlsx
source_md5: "optional-until-built"
facts_digest: "optional-until-built"
manifest_sidecar: workbooks/metrics.xlsx.<md5>.json
analysis_sidecar: workbooks/metrics.xlsx.analysis.json
fidelity: unknown            # source | derivative | unknown | …
```

**Gates:** when `tool` is set it MUST be `eidos-spreadsheet-explorer` (or empty for legacy). Prefer pinning digests once sidecars exist. Do not embed whole-sheet JSON in concept bodies.

---

## 9. Slices and first proof path

A `slice` declares:

- `serves`: metrics or publish-paths it advances
- `includes`: concepts it delivers (providers, tables, recipes, contracts, …)
- `proof`: acceptance concepts that can fail
- `non_goals`: tempting adjacent scope

The face names exactly one `first_slice`. That slice MUST include:

1. at least one `provider` or `table` on the oracle path,
2. at least one `recipe` with explicit `basis`,
3. at least one `metric-contract` (or table-level acceptance for non-metric warehouses),
4. an `acceptance` on the proof path.

A deployed scaffold or "dbt build green" alone does **not** satisfy this gate.

---

## 10. Hosts, credentials, authority

```yaml
kind: host
address_kind: tailnet       # tailnet | private | public | local
selection_rule: "use warehouse-primary; alias warehouse-legacy → warehouse-primary"
aliases: ["warehouse-legacy"]
```

```yaml
kind: credential-plane
plane: vault                # vault | knox | env-file-on-host | secret-manager
locator: "org vault / secret manager; optional host-local env file never committed"
forbids: ["print password", "paste secret into chat", "commit .env"]
```

```yaml
kind: authority-boundary
allows: ["SELECT on bronze/silver/gold for verification agents"]
denies: ["writes", "DDL", "public internet exposure of Postgres"]
network: "Tailscale-only"
```

**Gates:**

- No document may embed password-like strings (validator heuristic + `forbids` on credential-plane).
- `operating` packs with financial data SHOULD have `address_kind` ≠ `public` on primary hosts (warn; strict error if `authority` denies public exposure).

---

## 11. External references

Pinned strings:

```text
emf:<pack>:<object>@<revision>
orf:<pack>:<object>@<revision>
opf:<pack>:<object>@<revision>
okf:<pack>:<object>@<revision>
```

Face `imports` closure:

```yaml
imports: [emf:acme-data@2026-07-06, orf:bronze-lessons@2026-07-06]
```

- `intent` accepts EMF only.
- `research` accepts ORF only.
- `product` accepts OPF only.
- `evidence` accepts ORF or OKF (and local ODFW verdict/acceptance ids).

Draft validation warns on unpinned or undeclared externals; `--strict` fails. v0.2.0 validates declared pins but does not fetch remote packs.

---

## 12. Validation modes and parser

Default mode is **draft**: all local structure, target kinds, directed reachability, lifecycle, oracle, first-slice, supersession rules apply; external pin/import defects and some honesty gates warn.

`--strict` turns warnings into errors and requires pinned imported externals. Strict validation is the publication gate.

The validator accepts only the documented YAML subset: scalar values, inline scalar lists, indented scalar lists, and nested maps such as `verified` / `tolerance`. Duplicate keys, tabs, multiline scalars, inline maps, lists of maps, and malformed lines fail closed. Stdlib only — same discipline as OPF/ORF/EMF.

```bash
python3 -m odfw.validate --selftest
python3 -m odfw.validate examples/minimal
python3 -m odfw.validate --strict examples/minimal
python3 -m odfw.validate --strict /path/to/private-warehouse-pack
```

---

## 13. Conformance

- Every document declares `okf_version: "0.2"` and `odfw_version` on the `0.2.x` line (`X.Y` MUST equal `okf_version`).
- `index.md` uses `type: warehouse`; other ODFW documents use `type: warehouse-concept`.
- Lifecycle, target-kind, oracle, first-slice, recipe-basis, acceptance, supersession, and parser gates pass.
- IDs are unique, internal references resolve, and every concept is reachable through directed composition edges.
- Every document carries OKF `verified.by` and a nonempty `verified.method`.
- Strict validation has no warnings.

Versioning: ODFW inherits its first two components from OKF. First release on OKF 0.2 is `0.2.0`; profile-only revisions are `0.2.1`, …. OKF `0.3` starts ODFW `0.3.0`.

---

## 14. Non-goals

ODFW is a **format**, not:

- a warehouse engine, dbt project, or Dagster deployment
- a credentials store
- a global metric database or issue tracker
- a replacement for `information_schema` or live SQL
- a product PRD (use OPF for product UI)

Issue trackers execute work. dbt owns model SQL. Dagster owns run history. EMF owns human intent. ORF owns research. OPF owns product commitments. **ODFW owns the warehouse commitments and typed links connecting those authorities.**

---

## 15. Prior art and grounding corpus

| Source | What ODFW took |
|---|---|
| **OPF** | Additive OKF profile pattern, atomic concepts, directed edges, lifecycle gates, first-slice proof, stdlib validator |
| **ORF** | Measured-failures table, admission rules that bite, evidence grades pattern (adapted to verdicts) |
| **EMF** | Intent separation, trust ladder discipline, supersession |
| **Production warehouse dogfood (private)** | Bronze-as-oracle, vector compare, exclusions, entity-map, series pinning, registry/MCP honesty, host durability, network posture — lessons encoded as rules; **details stay in private packs** |
| **eidos-warehouse-explorer** | Deterministic lineage facts vs judgment; provenance digests as evidence sidecars (optional under `evidence/`) |

---

## 16. Version

| | |
|---|---|
| Profile | ODFW **0.2.2** |
| Base | OKF **0.2** |
| Status | Draft — sql-packet / check / test / result / workbook pins; private packs dogfood |
