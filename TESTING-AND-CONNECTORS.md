# ODFW testing frameworks & connectors

**Status:** design target for ODFW ≥ 0.3 / v1 complete  
**Principle:** compose battle-tested open tools; ODFW owns the **tree, pins, and proof**, not a new DQ engine or ELT platform.

---

## 1. Problem

A warehouse proof package without:

1. a **real test runner** (pass/fail against live data), and  
2. a **boring way to connect** to Postgres / BigQuery / files / …  

…is still a document. Agents re-implement probes. Months return.

ODFW must make “get online + run checks” a **standard path**, not a skill file.

---

## 2. Decision (defaults)

| Concern | Adopt (in the wild) | ODFW role |
|---|---|---|
| **Data contract + quality tests** | **[Open Data Contract Standard (ODCS)](https://bitol-io.github.io/open-data-contract-standard/)** + **[datacontract CLI](https://cli.datacontract.com/)** | Pack pins ODCS files; `check`/`test`/`result` bind to `datacontract test` outcomes |
| **SQL / multi-engine execution** | **Ibis** (what datacontract-cli uses today) / dialect SQL via sqlglot | Do not reimplement |
| **Optional DQ engines** | **dbt tests**, **Great Expectations (GX Core)**, **SodaCL** | Export/bind only when pack declares `engine` |
| **Warehouse “get online”** | **ODCS `servers:` block** + env-substituted secrets (never in git) | `host` + `credential-plane` point at server id |
| **File/table interchange** | **Apache Arrow / ADBC** (where available) for columnar; DuckDB for local files | Adapter kind, not format core |
| **SaaS extract (optional)** | **Singer taps** or **Airbyte** connectors | Only for provider land; out of prove-path critical path |
| **Excel answer-key** | **eidos-spreadsheet-explorer** (already chosen) | `answer-key` / `workbook` pins |

**Default prove path for Cerebro-class packs:**

```text
odfw-validate --strict .
datacontract test contracts/<metric-or-table>.odcs.yaml   # uses servers: + quality
# map CLI exit + JSON report → ODFW result concept (append-only)
```

Do **not** invent “ODFW-CL” as a quality language. ODCS quality library + SQL checks already cover rowCount, nulls, freshness, custom SQL.

---

## 3. Why these (not a greenfield framework)

### Testing: ODCS + datacontract-cli

- Open YAML **contract** format (schema + quality + servers + owners).  
- CLI already **tests against live backends** (Postgres, Snowflake, BigQuery, files, …).  
- Quality can be library rules **or** SQL — same as our bronze recipes.  
- Ecosystem: export to dbt / GX when needed; Bitol governance.  
- 2026 reality: datacontract-cli moved execution toward **Ibis** (multi-backend), which is the right “universal SQL adapter” layer.

**Great Expectations** and **Soda** remain first-class *optional* engines for packs that already standardize on them. ODFW does not pick a religious war; it picks a **default** (ODCS) and stable bind points.

**dbt tests** remain the transform-layer runner for teams living in dbt — packs can `engine: dbt` and pin `dbt test --select …` as the test procedure.

### Connectors: servers + ADBC, not a new protocol

“Universal connector format that’s easy to get online” for **warehouse prove**:

```yaml
# ODCS / datacontract style — secrets via env, not literals
servers:
  cerebro_warehouse:
    type: postgres
    host: ${DBT_PG_HOST}
    port: ${DBT_PG_PORT}
    database: ${DBT_PG_DATABASE}
    schema: dd5_sage_bronze
    # user/password from env / credential-plane — never committed
```

That is enough to go online for SELECT checks in minutes once vault/env is injected.

For **broader extract** (SaaS → bronze), reuse **Singer** (simple, many taps) or **Airbyte** (catalog + CDK) — ODFW `provider` + `pipeline` concepts **link** to a tap/source id; they do not redefine the protocol.

**ADBC / Arrow** is the long-term “one client, many DBs” story for agents running packets; document as preferred runtime when available, with SQLAlchemy/psycopg as Cerebro today.

---

## 4. How this hangs on the ODFW tree

```text
warehouse face
├── host + credential_plane
│     └── connector: servers.cerebro_warehouse   # pin to ODCS server id
├── providers / layers / tables
├── contracts/                     # ODCS YAML (or symlink)
│     └── revenue-lob.odcs.yaml
├── sql/                           # ODFW sql-packets (named SELECT bodies)
├── checks/                        # ODFW check concepts
│     engine: datacontract         # or gx | dbt | soda | sql-packet
│     binds: contracts/revenue-lob.odcs.yaml
├── tests/
│     steps: [odfw-validate, datacontract test …, map report]
└── results/                       # append-only; include engine report digest
```

### New / extended kinds (target)

| Kind / field | Meaning |
|---|---|
| `connector` (or fields on `host`) | `engine: odcs-server \| adbc \| sqlalchemy`; `server_id`; env key names only |
| `data-contract` | Pin to ODCS file path + version/digest |
| `check.engine` | `datacontract` \| `dbt` \| `great-expectations` \| `soda` \| `sql-packet` \| `custom` |
| `check.bind` | Path or id of contract / GX suite / dbt selector / SodaCL file |
| `test.runner` | CLI recipe that is **reproducible** (argv template, no secrets) |
| `result.engine_report` | Path/digest of native report JSON |

Validator (stdlib): resolve pins, forbid secrets, require engine ∈ allowlist.  
**Harness** (not stdlib validator): run `datacontract test`, capture exit code + report → write `result`.

---

## 5. Adapter matrix (get online)

| Source class | Adapter | Easy path |
|---|---|---|
| Postgres / warehouse SQL | ODCS `servers.type: postgres` + env | `datacontract test` |
| Snowflake / BQ / etc. | ODCS server types + Ibis backends | same CLI |
| Local parquet/CSV | DuckDB / ODCS file server | same CLI |
| Excel answer-key | eidos-spreadsheet-explorer | row/vector peer, not ODCS schema alone |
| SaaS API → bronze | Singer tap / Airbyte source | pipeline concept only |
| Custom SQL packet | ODFW `sql-packet` + psycopg/ADBC | triangulation harness |

**Cerebro first path:** Postgres ODCS server + sql-packet for bronze re-derive + explorer for key.

---

## 6. Mapping existing ODFW checks

Today’s ODFW `check` / `test` / `result` stay. They become **orchestration and proof**, not the quality DSL.

| ODFW object | External artifact |
|---|---|
| `metric-contract` | May generate or pin an ODCS contract for the series grain |
| `sql-packet` | Custom SQL quality / re-derive (ODCS `type: sql` quality or harness) |
| `check` | One engine invocation + peer list (bronze/gold/key) |
| `test` | Ordered runners: validate → contract test → packet → append result |
| `result` | Engine report + ODFW outcome enum |

Triangulation (bronze ↔ gold ↔ workbook) may need a **thin harness** (Python) that:

1. Runs sql-packet  
2. Reads gold via connector  
3. Reads key via spreadsheet-explorer  
4. Compares vectors under tolerance  
5. Emits `result`

That harness is package-local or `odfw-harness` — still not a new quality language.

---

## 7. What we will not build

- A proprietary ODFW quality language competing with ODCS/SodaCL/GX  
- A new ELT connector CDK (use Singer/Airbyte)  
- Embedding passwords in contracts  
- Making `odfw-validate` execute live SQL (keep stdlib gate separate from harness)

---

## 8. Implementation order

1. **Document** (this file) — done as target.  
2. **SPEC**: `check.engine`, `data-contract`, connector fields on `host`.  
3. **Pack layout**: `contracts/` with one ODCS YAML for a tiny table or metric grain; `servers` env-only.  
4. **Harness script** in private pack: `scripts/prove-first-slice.sh` → validate + datacontract test + optional packet.  
5. **Result adapter**: map datacontract JSON → ODFW `result` outcome.  
6. **Optional**: export path to dbt tests for data-daemon-v5 CI.

---

## 9. Success criteria

- New machine: install `odfw` + `datacontract-cli` + inject env → **one command** fails or passes against live Postgres.  
- No new quality dialect to learn beyond ODCS + existing sql-packets.  
- Connectors for “get online” are **copy-paste server YAML + env**, not a research project.  
- Excel and warehouse stay dual-plane (explorer + ODCS/SQL).

---

## 10. References

- ODCS: https://bitol-io.github.io/open-data-contract-standard/  
- datacontract-cli: https://cli.datacontract.com/  
- Ibis: https://ibis-project.org/  
- Great Expectations: https://greatexpectations.io/  
- SodaCL / Soda Core  
- Singer: https://www.singer.io/  
- ADBC: https://arrow.apache.org/adbc/  
- eidos-spreadsheet-explorer (Excel plane)
