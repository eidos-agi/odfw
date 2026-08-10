"""Validate Open Data Warehouse Format v0.2.x documents and packs.

Stdlib only. The parser accepts the deliberately small YAML subset ODWF specifies
and fails closed on syntax it cannot represent faithfully.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from . import ODWF_VERSION, OKF_VERSION

TYPES = {"warehouse", "warehouse-concept"}
KINDS = {
    "provider",
    "layer",
    "oracle",
    "schema",
    "table",
    "column",
    "entity-map",
    "exclusion-set",
    "seed",
    "pipeline",
    "transform",
    "recipe",
    "measure",
    "metric",
    "series",
    "metric-contract",
    "serving-plane",
    "publish-path",
    "host",
    "credential-plane",
    "freshness",
    "authority-boundary",
    "slice",
    "acceptance",
    "verdict",
    "decision",
    "risk",
    "answer-key",
    "workbook",
    "sql-packet",
    "check",
    "test",
    "result",
    "data-contract",
    "connector",
}
CHECK_ENGINES = {
    "datacontract",
    "dbt",
    "great-expectations",
    "soda",
    "sql-packet",
    "custom",
}
STATUSES = {"inventory", "contracting", "implementing", "proving", "operating", "retired"}
TIERS = {"human", "job", "agent"}
ACCEPTANCE_STATUSES = {"proposed", "observed", "failed"}
RECIPE_BASES = {"bronze", "silver", "gold", "answer-key", "hybrid"}
PLANE_KINDS = {"live-query", "catalog", "cache", "mcp", "dashboard", "workbook"}
COMPARE_MODES = {"vector", "scalar"}
RESULT_OUTCOMES = {
    "PASS",
    "FAIL",
    "NOT_RUN",
    "BLOCKED",
    "PROVEN",
    "GOLD_WRONG",
    "RECHECK",
    "NOT_DERIVABLE",
    "REGISTRY_STALE",
    # Explicit non-calc classifications (SPEC §8a) — not silent skips
    "NOT_APPLICABLE",
    "SOURCE_ONLY",
    "CARRIED_STRUCTURAL",
}
NON_CALC_CLASSES = {
    "not_applicable",
    "carried_structural",
    "source_only",
    "blank",
    "forecast_out_of_window",
}
NON_CALC_OUTCOMES = {"NOT_APPLICABLE", "SOURCE_ONLY", "CARRIED_STRUCTURAL"}
ROW_INVENTORY_SCHEMA = "odwf-row-inventory-v1"
LEGACY_ROW_INVENTORY_SCHEMA = "odfw-row-inventory-v1"
ROW_SEMANTICS_SCHEMA = "odwf-row-semantics-v1"
ROW_ROLES = {"blank", "title", "section_header", "column_header", "note", "metric", "unknown"}
METRIC_KINDS = {
    "source_input",
    "derived_metric",
    "total_subtotal",
    "rate_ratio",
    "variance_change",
    "unclear",
}
INVENTORY_OUTCOMES = {"PASS", "FAIL", "NOT_APPLICABLE"}
PLACEHOLDERS = {"tbd", "todo", "later", "unknown", "none", "n/a", "placeholder"}
NON_AUTHORITATIVE_PLANES = {"catalog", "cache", "mcp", "dashboard"}
ID_RE = re.compile(r"^(?:odwf|odfw):[a-z0-9][a-z0-9._-]*(?::[a-z0-9][a-z0-9._-]*){1,6}$")
EXTERNAL_RE = re.compile(
    r"^(?P<profile>emf|orf|opf|okf):(?P<pack>[a-z0-9][a-z0-9._-]*):"
    r"(?P<object>[a-z0-9][a-z0-9:._/-]*)@(?P<revision>[A-Za-z0-9._-]+)$"
)
IMPORT_RE = re.compile(
    r"^(?P<profile>emf|orf|opf|okf):(?P<pack>[a-z0-9][a-z0-9._-]*)@"
    r"(?P<revision>[A-Za-z0-9._-]+)$"
)
SECRETISH = re.compile(
    r"(?i)(password\s*[:=]\s*\S+|postgres(ql)?://[^:]+:[^@]+@|-----BEGIN (RSA |OPENSSH )?PRIVATE KEY-----)"
)
WRITEISH_SQL = re.compile(
    r"(?is)\b(insert|update|delete|drop|alter|truncate|create|grant|revoke)\b"
)

EDGE_TARGET_KINDS: dict[str, set[str]] = {
    "oracle": {"oracle"},
    "layers": {"layer"},
    "providers": {"provider"},
    "hosts": {"host"},
    "credential_plane": {"credential-plane"},
    "authority": {"authority-boundary"},
    "serving_planes": {"serving-plane"},
    "publish_paths": {"publish-path"},
    "first_slice": {"slice"},
    "proof": {"acceptance"},
    "validation": {"acceptance"},
    "operational_proof": {"acceptance"},
    "metric": {"metric"},
    "series": {"series"},
    "recipe": {"recipe"},
    "sql_packet": {"sql-packet"},
    "sql_packets": {"sql-packet"},
    "check": {"check"},
    "checks": {"check"},
    "test": {"test"},
    "tests": {"test"},
    "results": {"result"},
    "entity_map": {"entity-map"},
    "exclusions": {"exclusion-set"},
    "transforms": {"transform"},
    "tables": {"table"},
    "schemas": {"schema"},
    "pipeline": {"pipeline"},
    "freshness": {"freshness"},
    "lands_in": {"schema", "table", "layer"},
    "reads_from": {"table", "schema", "layer", "serving-plane"},
    "writes_to": {"table", "schema", "layer", "serving-plane"},
    "serves": {"metric", "series", "slice", "publish-path", "metric-contract"},
    "includes": KINDS - {"risk", "decision", "verdict", "result"},
    "depends_on": KINDS,
    "supersedes": KINDS,
    "superseded_by": KINDS,
    "layer": {"layer"},
    "answer_key": {"answer-key", "workbook"},
    "metric_contract": {"metric-contract"},
    "data_contract": {"data-contract"},
    "data_contracts": {"data-contract"},
    "connector": {"connector"},
    "connectors": {"connector"},
    "inputs": {"table", "schema", "exclusion-set", "entity-map", "seed", "answer-key", "workbook"},
}
REF_FIELDS = set(EDGE_TARGET_KINDS)
EXTERNAL_FIELDS = {
    "intent": {"emf"},
    "research": {"orf"},
    "product": {"opf"},
    "evidence": {"okf", "orf"},
}
COMPOSITION_FIELDS = {
    "providers",
    "layers",
    "oracle",
    "hosts",
    "credential_plane",
    "authority",
    "serving_planes",
    "publish_paths",
    "first_slice",
    "proof",
    "validation",
    "operational_proof",
    "freshness",
}
CONTRACTING_REQUIRED = {
    "oracle",
    "layers",
    "providers",
    "hosts",
    "credential_plane",
    "authority",
}


@dataclass
class Problem:
    level: str  # error | warn
    rule: str
    detail: str


@dataclass
class Report:
    path: Path
    problems: list[Problem] = field(default_factory=list)

    @property
    def errors(self) -> list[Problem]:
        return [p for p in self.problems if p.level == "error"]

    @property
    def warnings(self) -> list[Problem]:
        return [p for p in self.problems if p.level == "warn"]

    def add(self, level: str, rule: str, detail: str) -> None:
        self.problems.append(Problem(level, rule, detail))


@dataclass
class Doc:
    path: Path
    meta: dict[str, Any]
    body: str


# --- YAML subset parser (shared discipline with OPF/ORF) ---


def parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        raise ValueError("unterminated frontmatter")
    meta = _parse_yaml_block(text[3:end])
    body = text[end + 4 :].lstrip("\n")
    return meta, body


def _parse_yaml_block(block: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    stack: list[tuple[int, Any]] = [(-1, out)]
    lines = block.splitlines()
    i = 0
    while i < len(lines):
        raw = lines[i]
        if not raw.strip() or raw.lstrip().startswith("#"):
            i += 1
            continue
        if "\t" in raw:
            raise ValueError(f"tabs not allowed: {raw!r}")
        indent = len(raw) - len(raw.lstrip())
        line = raw.strip()
        while len(stack) > 1 and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]

        if line.startswith("- "):
            if not isinstance(parent, list):
                raise ValueError(f"list item without list parent: {line!r}")
            parent.append(_parse_scalar(line[2:].strip()))
            i += 1
            continue

        if ":" not in line:
            raise ValueError(f"expected key: value, got {line!r}")
        key, _, rest = line.partition(":")
        key = key.strip()
        rest = rest.strip()
        if not isinstance(parent, dict):
            raise ValueError(f"map entry under non-map: {line!r}")
        if key in parent:
            raise ValueError(f"duplicate key: {key}")

        if rest == "":
            # look ahead: list or nested map?
            j = i + 1
            while j < len(lines) and (not lines[j].strip() or lines[j].lstrip().startswith("#")):
                j += 1
            if j < len(lines):
                nxt = lines[j]
                nindent = len(nxt) - len(nxt.lstrip())
                if nindent > indent and nxt.strip().startswith("- "):
                    parent[key] = []
                    stack.append((indent, parent[key]))
                elif nindent > indent:
                    parent[key] = {}
                    stack.append((indent, parent[key]))
                else:
                    parent[key] = None
            else:
                parent[key] = None
        else:
            if rest.startswith("{") or rest.startswith("[") and ":" in rest:
                # reject inline maps / complex structures
                if rest.startswith("{"):
                    raise ValueError(f"inline maps not allowed: {rest!r}")
            parent[key] = _parse_scalar(rest)
        i += 1
    return out


def _parse_scalar(s: str) -> Any:
    if s.startswith("[") and s.endswith("]"):
        inner = s[1:-1].strip()
        if not inner:
            return []
        parts: list[str] = []
        buf = ""
        in_q = False
        for ch in inner:
            if ch in "\"'":
                in_q = not in_q
                continue
            if ch == "," and not in_q:
                parts.append(buf.strip())
                buf = ""
                continue
            buf += ch
        parts.append(buf.strip())
        return [_parse_scalar(p) if p else "" for p in parts]
    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        return s[1:-1]
    if s.lower() in {"true", "false"}:
        return s.lower() == "true"
    if s.lower() in {"null", "~"}:
        return None
    if re.fullmatch(r"-?\d+", s):
        return int(s)
    if re.fullmatch(r"-?\d+\.\d+", s):
        return float(s)
    return s


def _as_list(val: Any) -> list[Any]:
    if val is None:
        return []
    if isinstance(val, list):
        return val
    return [val]


def _is_placeholder(val: Any) -> bool:
    if val is None:
        return True
    if isinstance(val, str) and val.strip().lower() in PLACEHOLDERS:
        return True
    return False


def _refs(val: Any) -> list[str]:
    out: list[str] = []
    for item in _as_list(val):
        if isinstance(item, str) and item:
            out.append(item)
    return out


# --- load pack ---


def load_doc(path: Path) -> Doc:
    text = path.read_text(encoding="utf-8")
    meta, body = parse_frontmatter(text)
    # Compatibility for packs published before the acronym was corrected.
    if "odwf_version" not in meta and "odfw_version" in meta:
        meta["odwf_version"] = meta["odfw_version"]
    if "odwf_id" not in meta and "odfw_id" in meta:
        meta["odwf_id"] = meta["odfw_id"]
    if meta.get("profile") == "odfw":
        meta["profile"] = "odwf"
    return Doc(path=path, meta=meta, body=body)


def load_pack(root: Path) -> tuple[Doc | None, list[Doc], list[Path]]:
    root = root.resolve()
    face_path = root / "index.md"
    face = load_doc(face_path) if face_path.is_file() else None
    docs: list[Doc] = []
    extras: list[Path] = []
    for p in sorted(root.rglob("*.md")):
        if p.name == "log.md":
            extras.append(p)
            continue
        if p == face_path:
            continue
        if p.name in {"README.md", "CHANGELOG.md", "AGENTS.md"}:
            extras.append(p)
            continue
        if p.name == "index.md" and p.parent != root:
            continue
        doc = load_doc(p)
        if not doc.meta:
            extras.append(p)
            continue
        docs.append(doc)
    return face, docs, extras


# --- validation ---


def _validate_doc_base(doc: Doc, report: Report) -> None:
    meta = doc.meta
    if not meta:
        report.add("error", "frontmatter.missing", f"{doc.path.name}: YAML frontmatter required")
        return
    if str(meta.get("okf_version", "")) != OKF_VERSION:
        report.add("error", "version.okf", f"{doc.path.name}: okf_version must be {OKF_VERSION!r}")
    odwf_v = str(meta.get("odwf_version", ""))
    if not re.fullmatch(r"\d+\.\d+\.\d+", odwf_v):
        report.add("error", "version.odwf", f"{doc.path.name}: odwf_version must be X.Y.Z")
    elif odwf_v.rsplit(".", 1)[0] != str(meta.get("okf_version", "")):
        report.add("error", "version.align", f"{doc.path.name}: odwf_version X.Y must equal okf_version")
    if meta.get("type") not in TYPES:
        report.add("error", "type", f"{doc.path.name}: type must be warehouse or warehouse-concept")
    if _is_placeholder(meta.get("title")) or not meta.get("title"):
        report.add("error", "title", f"{doc.path.name}: title required")
    odwf_id = meta.get("odwf_id")
    if not isinstance(odwf_id, str) or not ID_RE.match(odwf_id):
        report.add("error", "id", f"{doc.path.name}: odwf_id must match odwf:<warehouse>:…")


def validate_path(path: Path, *, strict: bool = False) -> list[Report]:
    path = path.resolve()
    if path.is_file():
        return [validate_docs(None, [load_doc(path)], [], path, strict=strict)]
    face, docs, extras = load_pack(path)
    return [validate_docs(face, docs, extras, path, strict=strict)]


def validate_docs(
    face: Doc | None,
    docs: list[Doc],
    extras: list[Path],
    root: Path,
    *,
    strict: bool,
) -> Report:
    report = Report(path=root)
    if face is None:
        report.add("error", "face.missing", "pack requires index.md warehouse face")
        return report

    all_docs = [face, *docs]
    by_id: dict[str, Doc] = {}

    for doc in all_docs:
        _validate_doc_base(doc, report)
        meta = doc.meta
        odwf_id = meta.get("odwf_id")
        if isinstance(odwf_id, str) and ID_RE.match(odwf_id):
            if odwf_id in by_id:
                report.add("error", "id.duplicate", f"{odwf_id} in {doc.path.name} and {by_id[odwf_id].path.name}")
            else:
                by_id[odwf_id] = doc

    # face-specific
    fm = face.meta
    if fm.get("type") != "warehouse":
        report.add("error", "face.type", "index.md must have type: warehouse")
    status = fm.get("status")
    if status not in STATUSES:
        report.add("error", "face.status", f"status must be one of {sorted(STATUSES)}")

    for field_name in ("title", "odwf_id"):
        if _is_placeholder(fm.get(field_name)) or not fm.get(field_name):
            report.add("error", "face.required", f"face missing non-placeholder {field_name}")

    # version alignment
    okf_v = str(fm.get("okf_version", ""))
    odwf_v = str(fm.get("odwf_version", ""))
    if okf_v != OKF_VERSION:
        report.add("error", "version.okf", f"okf_version must be {OKF_VERSION!r}")
    if not re.fullmatch(r"\d+\.\d+\.\d+", odwf_v):
        report.add("error", "version.odwf", "odwf_version must be X.Y.Z")
    elif odwf_v.rsplit(".", 1)[0] != okf_v:
        report.add("error", "version.align", "odwf_version X.Y must equal okf_version")

    if not (root / "log.md").is_file() and not any(p.name == "log.md" for p in extras):
        report.add("warn", "log.missing", "pack should include append-only log.md")

    # concept docs
    for doc in docs:
        if doc.meta.get("type") != "warehouse-concept":
            report.add("error", "concept.type", f"{doc.path.name}: type must be warehouse-concept")
        kind = doc.meta.get("kind")
        if kind not in KINDS:
            report.add("error", "concept.kind", f"{doc.path.name}: kind must be one of ODWF kinds")
        odwf_id = doc.meta.get("odwf_id")
        if not isinstance(odwf_id, str) or not ID_RE.match(odwf_id):
            report.add("error", "concept.id", f"{doc.path.name}: invalid odwf_id")
        elif isinstance(kind, str):
            # ID should include the kind, or a documented short alias of it.
            kind_aliases = {
                "authority-boundary": {"authority-boundary", "authority"},
                "serving-plane": {"serving-plane", "serving"},
                "publish-path": {"publish-path", "publish"},
                "credential-plane": {"credential-plane", "credential"},
                "entity-map": {"entity-map", "entity"},
                "exclusion-set": {"exclusion-set", "exclusion"},
                "metric-contract": {"metric-contract", "contract"},
                "answer-key": {"answer-key", "answerkey"},
            }
            tokens = set(str(odwf_id).split(":"))
            allowed = kind_aliases.get(str(kind), {str(kind)})
            if tokens.isdisjoint(allowed):
                report.add(
                    "warn",
                    "concept.id.kind",
                    f"{doc.path.name}: odwf_id should include kind {kind!r}",
                )

    # edge resolution
    for doc in all_docs:
        meta = doc.meta
        for field_name, allowed in EDGE_TARGET_KINDS.items():
            if field_name not in meta:
                continue
            for ref in _refs(meta.get(field_name)):
                if ref.startswith(("emf:", "orf:", "opf:", "okf:")):
                    continue
                target = by_id.get(ref)
                if target is None:
                    report.add("error", "edge.resolve", f"{doc.path.name}: {field_name} -> {ref} not found")
                    continue
                tkind = target.meta.get("kind") if target.meta.get("type") == "warehouse-concept" else None
                if target is face:
                    report.add("error", "edge.face", f"{doc.path.name}: {field_name} must not target face")
                elif tkind not in allowed:
                    report.add(
                        "error",
                        "edge.kind",
                        f"{doc.path.name}: {field_name} -> {ref} kind {tkind!r} not in {sorted(allowed)}",
                    )

        # external refs
        for field_name, profiles in EXTERNAL_FIELDS.items():
            for ref in _refs(meta.get(field_name)):
                m = EXTERNAL_RE.match(ref)
                if not m:
                    # local result/acceptance/okf ids allowed on evidence
                    if field_name == "evidence" and ref in by_id:
                        continue
                    report.add("warn" if not strict else "error", "external.pin", f"{doc.path.name}: bad external {ref}")
                    continue
                if m.group("profile") not in profiles:
                    report.add(
                        "error",
                        "external.profile",
                        f"{doc.path.name}: {field_name} rejects profile {m.group('profile')}",
                    )
                imports = {_i for _i in _refs(fm.get("imports"))}
                pack_pin = f"{m.group('profile')}:{m.group('pack')}@{m.group('revision')}"
                # also accept imports of whole pack without object
                ok_import = any(
                    IMPORT_RE.match(imp)
                    and IMPORT_RE.match(imp).group("profile") == m.group("profile")  # type: ignore[union-attr]
                    and IMPORT_RE.match(imp).group("pack") == m.group("pack")  # type: ignore[union-attr]
                    and IMPORT_RE.match(imp).group("revision") == m.group("revision")  # type: ignore[union-attr]
                    for imp in imports
                )
                if not ok_import:
                    report.add(
                        "warn" if not strict else "error",
                        "external.import",
                        f"{doc.path.name}: {ref} not covered by face imports",
                    )

        # secret heuristic
        blob = doc.path.read_text(encoding="utf-8")
        if SECRETISH.search(blob):
            report.add("error", "secrets", f"{doc.path.name}: looks like an embedded secret")

    # lifecycle gates
    if status in {"contracting", "implementing", "proving", "operating"}:
        for req in CONTRACTING_REQUIRED:
            vals = _refs(fm.get(req)) if req != "credential_plane" else _refs(fm.get("credential_plane"))
            # credential_plane is scalar ref often
            if req == "credential_plane":
                v = fm.get("credential_plane")
                vals = _refs(v)
            if not vals or any(_is_placeholder(v) for v in vals):
                report.add("error", "lifecycle.contracting", f"status {status} requires {req}")
            for v in vals:
                if v not in by_id:
                    report.add("error", "lifecycle.contracting", f"{req} {v} does not resolve")

        # providers at least one
        if not _refs(fm.get("providers")):
            report.add("error", "lifecycle.providers", "at least one provider required")
        if not _refs(fm.get("layers")):
            report.add("error", "lifecycle.layers", "at least one layer required")

    if status in {"implementing", "proving", "operating"}:
        fs = fm.get("first_slice")
        if not isinstance(fs, str) or fs not in by_id:
            report.add("error", "lifecycle.slice", "first_slice must resolve")
        else:
            _check_first_slice(by_id[fs], by_id, report)

    if status in {"proving", "operating"}:
        proofs = _refs(fm.get("proof")) + _refs(fm.get("validation")) + _refs(fm.get("operational_proof"))
        observed = False
        for pid in proofs:
            acc = by_id.get(pid)
            if acc and acc.meta.get("status") == "observed" and _refs(acc.meta.get("evidence")):
                observed = True
        if not observed:
            report.add(
                "error",
                "lifecycle.proof",
                "proving/operating requires acceptance with status: observed and evidence",
            )

    if status == "operating":
        # freshness concept reachable
        has_fresh = any(d.meta.get("kind") == "freshness" for d in docs)
        if not has_fresh:
            report.add("warn", "lifecycle.freshness", "operating packs should define freshness concepts")
        retired = {str(x).lower() for x in _as_list(fm.get("retired_substrates"))}
        if retired:
            for doc in all_docs:
                body_l = (doc.body + str(doc.meta)).lower()
                for r in retired:
                    if r and r in body_l and doc is not face:
                        report.add(
                            "warn",
                            "retired.ref",
                            f"{doc.path.name}: mentions retired substrate {r!r}",
                        )

    if status == "retired" and _is_placeholder(fm.get("retirement_reason")):
        report.add("error", "lifecycle.retired", "retired requires retirement_reason")

    # oracle uniqueness / layer flags
    oracles = [d for d in docs if d.meta.get("kind") == "oracle"]
    if status not in {"inventory", None} and status in STATUSES:
        if len(_refs(fm.get("oracle"))) != 1 and status != "inventory":
            if status in {"contracting", "implementing", "proving", "operating"}:
                pass  # already required
        trusted = [d for d in docs if d.meta.get("kind") == "layer" and d.meta.get("trusted_as_oracle") is True]
        if len(trusted) > 1:
            report.add("error", "oracle.layers", "at most one layer may set trusted_as_oracle: true")

    for doc in docs:
        kind = doc.meta.get("kind")
        if kind == "recipe":
            basis = doc.meta.get("basis")
            if basis not in RECIPE_BASES:
                report.add("error", "recipe.basis", f"{doc.path.name}: basis must be one of {sorted(RECIPE_BASES)}")
            if basis == "bronze":
                inputs = _refs(doc.meta.get("inputs")) + _refs(doc.meta.get("depends_on"))
                only_ak = inputs and all(
                    (
                        by_id.get(i)
                        and by_id[i].meta.get("kind") in {"answer-key", "workbook"}
                    )
                    for i in inputs
                    if i in by_id
                )
                if only_ak:
                    report.add("error", "recipe.basis.bronze", f"{doc.path.name}: basis bronze cannot be answer-key-only")
        if kind == "sql-packet":
            basis = doc.meta.get("basis")
            if basis not in RECIPE_BASES:
                report.add("error", "sql.basis", f"{doc.path.name}: basis must be one of {sorted(RECIPE_BASES)}")
            sql_path = doc.meta.get("sql_path")
            sql_body = doc.meta.get("sql_body")
            if _is_placeholder(sql_path) and _is_placeholder(sql_body):
                # body may live in markdown after frontmatter as fenced sql — allow if body has SELECT
                if "select" not in doc.body.lower():
                    report.add(
                        "error",
                        "sql.source",
                        f"{doc.path.name}: sql_path, sql_body, or SELECT body required",
                    )
            posture = str(doc.meta.get("posture", "select-only")).lower()
            if posture != "select-only":
                report.add("error", "sql.posture", f"{doc.path.name}: posture must be select-only")
            blob = str(sql_body or "") + "\n" + doc.body
            if re.search(
                r"(?im)^\s*(insert|update|delete|drop|alter|truncate|create)\b",
                blob,
            ):
                report.add("error", "sql.write", f"{doc.path.name}: write/DDL SQL forbidden")
            if basis == "bronze":
                inputs = _refs(doc.meta.get("inputs")) + _refs(doc.meta.get("depends_on"))
                only_ak = inputs and all(
                    (
                        by_id.get(i)
                        and by_id[i].meta.get("kind") in {"answer-key", "workbook"}
                    )
                    for i in inputs
                    if i in by_id
                )
                if only_ak:
                    report.add("error", "sql.basis.bronze", f"{doc.path.name}: bronze packet cannot be answer-key-only")
            # resolve sql_path if relative to pack root
            if isinstance(sql_path, str) and sql_path and not _is_placeholder(sql_path):
                cand = root / sql_path
                if root.is_dir() and not cand.is_file():
                    report.add("error", "sql.path", f"{doc.path.name}: sql_path not found: {sql_path}")
                elif cand.is_file():
                    text = cand.read_text(encoding="utf-8", errors="replace")
                    if SECRETISH.search(text):
                        report.add("error", "secrets", f"{sql_path}: looks like an embedded secret")
                    if re.search(r"(?im)^\s*(insert|update|delete|drop|alter|truncate|create)\b", text):
                        report.add("error", "sql.write", f"{sql_path}: write/DDL SQL forbidden")
        if kind == "check":
            engine = doc.meta.get("engine")
            if engine is not None and engine not in CHECK_ENGINES:
                report.add(
                    "error",
                    "check.engine",
                    f"{doc.path.name}: engine must be one of {sorted(CHECK_ENGINES)}",
                )
            compare = doc.meta.get("compare")
            if compare is not None and compare not in COMPARE_MODES:
                report.add("error", "check.compare", f"{doc.path.name}: compare must be vector|scalar")
            elif compare == "scalar" and status == "operating":
                report.add(
                    "warn" if not strict else "error",
                    "check.scalar",
                    f"{doc.path.name}: scalar compare forbidden for operating packs under strict",
                )
            has_target = (
                _refs(doc.meta.get("metric_contract"))
                or _refs(doc.meta.get("sql_packet"))
                or _refs(doc.meta.get("data_contract"))
                or (
                    isinstance(doc.meta.get("bind"), str)
                    and not _is_placeholder(doc.meta.get("bind"))
                )
            )
            if not has_target:
                report.add(
                    "error",
                    "check.target",
                    f"{doc.path.name}: metric_contract, sql_packet, data_contract, or bind required",
                )
            if engine == "datacontract" and not (
                _refs(doc.meta.get("data_contract"))
                or (isinstance(doc.meta.get("bind"), str) and str(doc.meta.get("bind")).endswith((".yaml", ".yml")))
            ):
                report.add(
                    "warn" if not strict else "error",
                    "check.datacontract.bind",
                    f"{doc.path.name}: engine datacontract requires data_contract ref or bind path to ODCS yaml",
                )
        if kind == "data-contract":
            bind = doc.meta.get("bind") or doc.meta.get("contract_path")
            if _is_placeholder(bind) or not bind:
                report.add("error", "contract.bind", f"{doc.path.name}: bind/contract_path to ODCS file required")
            elif root.is_dir() and isinstance(bind, str):
                cand = root / bind
                if not cand.is_file():
                    report.add("error", "contract.path", f"{doc.path.name}: contract file not found: {bind}")
            std = doc.meta.get("standard")
            if std and std not in {"odcs", "ODCS", "datacontract"}:
                report.add("warn", "contract.standard", f"{doc.path.name}: preferred standard is odcs")
        if kind == "connector":
            eng = doc.meta.get("engine")
            if eng not in {"odcs-server", "adbc", "sqlalchemy", "datacontract", "custom"}:
                report.add(
                    "error",
                    "connector.engine",
                    f"{doc.path.name}: engine must be odcs-server|adbc|sqlalchemy|datacontract|custom",
                )
            if _is_placeholder(doc.meta.get("server_id")) and eng in {"odcs-server", "datacontract"}:
                report.add("error", "connector.server", f"{doc.path.name}: server_id required for odcs/datacontract")
        if kind == "test":
            has_steps = bool([s for s in _as_list(doc.meta.get("steps")) if not _is_placeholder(s)])
            has_packets = bool(_refs(doc.meta.get("sql_packets")) or _refs(doc.meta.get("sql_packet")))
            has_checks = bool(_refs(doc.meta.get("checks")) or _refs(doc.meta.get("check")))
            if not (has_steps or has_packets or has_checks):
                report.add("error", "test.empty", f"{doc.path.name}: steps, sql_packets, or checks required")
        if kind == "result":
            if _is_placeholder(doc.meta.get("at")) or not doc.meta.get("at"):
                report.add("error", "result.at", f"{doc.path.name}: at required")
            if _is_placeholder(doc.meta.get("by")) or not doc.meta.get("by"):
                report.add("error", "result.by", f"{doc.path.name}: by required")
            outcome = doc.meta.get("outcome")
            if outcome not in RESULT_OUTCOMES:
                report.add(
                    "error",
                    "result.outcome",
                    f"{doc.path.name}: outcome must be one of {sorted(RESULT_OUTCOMES)}",
                )
            ncc = doc.meta.get("non_calc_class")
            if ncc is not None and ncc != "" and ncc not in NON_CALC_CLASSES:
                report.add(
                    "error",
                    "result.non_calc_class",
                    f"{doc.path.name}: non_calc_class must be one of {sorted(NON_CALC_CLASSES)}",
                )
            # SPEC §8a: non-calc outcomes need a reason (prospective honesty)
            if outcome in NON_CALC_OUTCOMES or (ncc in NON_CALC_CLASSES if ncc else False):
                notes = doc.meta.get("notes")
                if _is_placeholder(notes) or not notes:
                    report.add(
                        "error" if strict else "warn",
                        "result.non_calc_notes",
                        f"{doc.path.name}: non-calc outcome/class requires notes reason (SPEC §8a)",
                    )
        if kind in {"answer-key", "workbook"}:
            tool = doc.meta.get("tool")
            if tool and tool != "eidos-spreadsheet-explorer":
                report.add(
                    "error",
                    "workbook.tool",
                    f"{doc.path.name}: tool must be eidos-spreadsheet-explorer when set",
                )
        if kind == "serving-plane":
            pk = doc.meta.get("plane_kind")
            if pk not in PLANE_KINDS:
                report.add("error", "serving.kind", f"{doc.path.name}: plane_kind invalid")
            elif pk in NON_AUTHORITATIVE_PLANES:
                na = [str(x).lower() for x in _as_list(doc.meta.get("not_authoritative_for"))]
                blob = " ".join(na)
                if "metric" not in blob and "table" not in blob and "value" not in blob:
                    report.add(
                        "warn" if not strict else "error",
                        "serving.honesty",
                        f"{doc.path.name}: non-live plane must declare not_authoritative_for metric values or table names",
                    )
        if kind == "metric-contract":
            compare = doc.meta.get("compare")
            if compare not in COMPARE_MODES:
                report.add("error", "contract.compare", f"{doc.path.name}: compare must be vector|scalar")
            elif compare == "scalar" and status == "operating":
                report.add(
                    "warn" if not strict else "error",
                    "contract.scalar",
                    f"{doc.path.name}: scalar compare is not allowed for operating packs under strict",
                )
            for req in ("metric", "recipe", "oracle"):
                if not _refs(doc.meta.get(req)):
                    report.add("error", "contract.required", f"{doc.path.name}: missing {req}")
        if kind == "acceptance":
            st = doc.meta.get("status")
            if st not in ACCEPTANCE_STATUSES:
                report.add("error", "acceptance.status", f"{doc.path.name}: bad status")
            if st in {"observed", "failed"} and not _refs(doc.meta.get("evidence")):
                report.add("error", "acceptance.evidence", f"{doc.path.name}: observed/failed requires evidence")
            if _is_placeholder(doc.meta.get("condition")):
                report.add("error", "acceptance.condition", f"{doc.path.name}: condition required")
        if kind == "credential-plane":
            if not doc.meta.get("locator"):
                report.add("error", "credential.locator", f"{doc.path.name}: locator required")

    # supersession pairing
    for doc in docs:
        sid = doc.meta.get("odwf_id")
        for other_id in _refs(doc.meta.get("supersedes")):
            other = by_id.get(other_id)
            if not other:
                continue
            if sid not in _refs(other.meta.get("superseded_by")):
                report.add(
                    "error",
                    "supersede.pair",
                    f"{doc.path.name}: supersedes {other_id} but target missing superseded_by",
                )
            if doc.meta.get("kind") != other.meta.get("kind"):
                report.add("error", "supersede.kind", f"{doc.path.name}: supersession kinds must match")

    # reachability via composition from face
    reachable: set[str] = set()
    stack = []
    for f in COMPOSITION_FIELDS:
        stack.extend(_refs(fm.get(f)))
    while stack:
        cur = stack.pop()
        if cur in reachable or cur not in by_id:
            continue
        reachable.add(cur)
        d = by_id[cur]
        walk_fields = set(EDGE_TARGET_KINDS) | COMPOSITION_FIELDS | {
            "includes",
            "serves",
            "inputs",
            "outputs",
        }
        for f in walk_fields:
            stack.extend(_refs(d.meta.get(f)))

    for doc in docs:
        oid = doc.meta.get("odwf_id")
        if isinstance(oid, str) and oid not in reachable and doc.meta.get("kind") not in {
            "risk",
            "decision",
            "verdict",
            "result",
        }:
            report.add(
                "warn",
                "reachability",
                f"{doc.path.name}: not reachable via composition edges from face",
            )

    # verified on every doc
    for doc in all_docs:
        v = doc.meta.get("verified")
        if not isinstance(v, dict):
            report.add("error", "verified", f"{doc.path.name}: verified map required")
            continue
        by = str(v.get("by", ""))
        if not by or ":" not in by or by.split(":", 1)[0] not in TIERS:
            report.add("error", "verified.by", f"{doc.path.name}: verified.by must be tier:name")
        if _is_placeholder(v.get("method")) or not v.get("method"):
            report.add("error", "verified.method", f"{doc.path.name}: verified.method required")

    if strict:
        for p in list(report.problems):
            if p.level == "warn":
                p.level = "error"

    return report


def _check_first_slice(slice_doc: Doc, by_id: dict[str, Doc], report: Report) -> None:
    if slice_doc.meta.get("kind") != "slice":
        report.add("error", "slice.kind", "first_slice must point at kind: slice")
        return
    included = _refs(slice_doc.meta.get("includes"))
    kinds = {i: by_id[i].meta.get("kind") for i in included if i in by_id}
    kind_set = set(kinds.values())
    if not (kind_set & {"provider", "table", "schema"}):
        report.add("error", "slice.path", "first_slice must include a provider or table/schema")
    if "recipe" not in kind_set and "sql-packet" not in kind_set:
        has_recipe = False
        for i, k in kinds.items():
            if k == "metric-contract":
                if _refs(by_id[i].meta.get("recipe")) or _refs(by_id[i].meta.get("sql_packet")):
                    has_recipe = True
            if k in {"recipe", "sql-packet"}:
                has_recipe = True
        if not has_recipe:
            report.add(
                "error",
                "slice.recipe",
                "first_slice must include a recipe or sql-packet (or contract with one)",
            )
    if "metric-contract" not in kind_set and "acceptance" not in kind_set and "check" not in kind_set:
        report.add(
            "error",
            "slice.contract",
            "first_slice must include metric-contract, check, or acceptance",
        )
    if not _refs(slice_doc.meta.get("proof")):
        report.add("error", "slice.proof", "first_slice must declare proof acceptances")


# --- CLI / selftest ---



# --- Progress fairness (SPEC §8a.6) ---

PERIOD_RE = re.compile(r"^\d{4}-\d{2}$")


def _month_range(start: str, end: str) -> list[str]:
    """Inclusive YYYY-MM range."""
    ys, ms = int(start[:4]), int(start[5:7])
    ye, me = int(end[:4]), int(end[5:7])
    out: list[str] = []
    y, m = ys, ms
    while (y, m) <= (ye, me):
        out.append(f"{y:04d}-{m:02d}")
        m += 1
        if m > 12:
            m = 1
            y += 1
    return out


def _load_json(path: Path) -> Any:
    import json

    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_pack_path(root: Path, rel: str) -> tuple[str | None, Path | None]:
    """Resolve a pack-relative evidence path.

    Returns (error_detail, resolved_path). error_detail set if the path is not
    allowed (absolute, ``..`` traversal, or escapes pack root). resolved_path is
    set when the path is pack-relative and stays under root (file need not exist).
    """
    if not isinstance(rel, str) or not rel or _is_placeholder(rel):
        return "path required", None
    p = Path(rel)
    if p.is_absolute():
        return f"absolute path forbidden: {rel}", None
    if ".." in p.parts:
        return f"path escapes pack via ..: {rel}", None
    root_res = root.resolve()
    cand = (root_res / rel).resolve()
    try:
        cand.relative_to(root_res)
    except ValueError:
        return f"path escapes pack root: {rel}", None
    return None, cand


def validate_progress(root: Path) -> Report:
    """File-only progress fairness. No live SQL. Stdlib only."""
    import json

    report = Report(path=root)
    if not root.is_dir():
        report.add("error", "progress.root", "progress validation requires a pack directory")
        return report

    evidence = root / "evidence"
    manifests = sorted(evidence.glob("*-progress.json")) if evidence.is_dir() else []
    if not manifests:
        # Explicit --progress with nothing to score is pending/absent, not fair.
        report.add(
            "error",
            "progress.absent",
            "no evidence/*-progress.json — progress claim pending/absent, not fair",
        )
        return report

    window: list[str] | None = None
    win_path = evidence / "prove-window.json"
    if win_path.is_file():
        try:
            win = _load_json(win_path)
        except (OSError, json.JSONDecodeError) as e:
            report.add("error", "progress.window.json", f"prove-window.json: {e}")
            return report
        if not isinstance(win, dict):
            report.add("error", "progress.window.shape", "prove-window.json must be an object")
            return report
        ps, pe = win.get("period_start"), win.get("period_end")
        if not (isinstance(ps, str) and PERIOD_RE.match(ps) and isinstance(pe, str) and PERIOD_RE.match(pe)):
            report.add(
                "error",
                "progress.window.fields",
                "prove-window.json requires period_start and period_end as YYYY-MM",
            )
            return report
        if (int(ps[:4]), int(ps[5:7])) > (int(pe[:4]), int(pe[5:7])):
            report.add("error", "progress.window.order", "period_start must be <= period_end")
            return report
        window = _month_range(ps, pe)

    for man_path in manifests:
        try:
            cells = _load_json(man_path)
        except (OSError, json.JSONDecodeError) as e:
            report.add("error", "progress.manifest.json", f"{man_path.name}: {e}")
            continue
        if not isinstance(cells, list):
            report.add("error", "progress.manifest.shape", f"{man_path.name}: must be a JSON array")
            continue

        by_period: dict[str, dict[str, Any]] = {}
        for i, cell in enumerate(cells):
            if not isinstance(cell, dict):
                report.add("error", "progress.cell.shape", f"{man_path.name}[{i}]: cell must be object")
                continue
            period = cell.get("period")
            if not isinstance(period, str) or not PERIOD_RE.match(period):
                report.add(
                    "error",
                    "progress.cell.period",
                    f"{man_path.name}[{i}]: period must be YYYY-MM",
                )
                continue
            if period in by_period:
                report.add(
                    "error",
                    "progress.cell.duplicate",
                    f"{man_path.name}: duplicate period {period}",
                )
            by_period[period] = cell

            outcome = cell.get("outcome")
            if outcome not in RESULT_OUTCOMES:
                report.add(
                    "error",
                    "progress.cell.outcome",
                    f"{man_path.name} {period}: outcome must be one of result outcomes",
                )

            result_rel = cell.get("result")
            err, resolved = _resolve_pack_path(root, result_rel if isinstance(result_rel, str) else "")
            if err and (not isinstance(result_rel, str) or not result_rel or _is_placeholder(result_rel)):
                report.add(
                    "error",
                    "progress.evidence.result",
                    f"{man_path.name} {period}: result path required",
                )
            elif err:
                report.add(
                    "error",
                    "progress.evidence.path",
                    f"{man_path.name} {period}: result {err}",
                )
            elif resolved is not None and not resolved.is_file():
                report.add(
                    "error",
                    "progress.evidence.result",
                    f"{man_path.name} {period}: missing result file {result_rel}",
                )

            sql_rel = cell.get("sql")
            if outcome in {"PASS", "FAIL"}:
                if not isinstance(sql_rel, str) or not sql_rel or _is_placeholder(sql_rel):
                    report.add(
                        "error",
                        "progress.evidence.sql",
                        f"{man_path.name} {period}: PASS/FAIL requires sql path",
                    )
                else:
                    serr, sresolved = _resolve_pack_path(root, sql_rel)
                    if serr:
                        report.add(
                            "error",
                            "progress.evidence.path",
                            f"{man_path.name} {period}: sql {serr}",
                        )
                    elif sresolved is not None and not sresolved.is_file():
                        report.add(
                            "error",
                            "progress.evidence.sql",
                            f"{man_path.name} {period}: missing sql file {sql_rel}",
                        )

            if outcome in NON_CALC_OUTCOMES:
                ncc = cell.get("non_calc_class")
                if ncc not in NON_CALC_CLASSES:
                    report.add(
                        "error",
                        "progress.non_calc_class",
                        f"{man_path.name} {period}: non-calc outcome requires non_calc_class",
                    )

            q = cell.get("quality_score")
            if q is not None:
                try:
                    qi = int(q)
                except (TypeError, ValueError):
                    report.add(
                        "error",
                        "progress.quality",
                        f"{man_path.name} {period}: quality_score must be int",
                    )
                    continue
                if outcome == "FAIL" and qi >= 8:
                    report.add(
                        "error",
                        "progress.quality.inflation",
                        f"{man_path.name} {period}: FAIL quality_score {qi} >= 8",
                    )
                if outcome == "PASS" and qi != 8:
                    report.add(
                        "error",
                        "progress.quality.honest",
                        f"{man_path.name} {period}: PASS quality_score {qi} (expected 8)",
                    )

        # window coverage
        expected = window
        if expected is None:
            if by_period:
                periods_sorted = sorted(by_period)
                expected = _month_range(periods_sorted[0], periods_sorted[-1])
            else:
                expected = []
        missing = [p for p in expected if p not in by_period]
        if missing:
            report.add(
                "error",
                "progress.coverage",
                f"{man_path.name}: silent omit periods {missing}",
            )

    return report


# --- Source-complete workbook row inventory ---

CELL_RE = re.compile(r"^(?P<column>[A-Z]+)(?P<row>[1-9]\d*)$")
DIMENSION_RE = re.compile(r"^[A-Z]+[1-9]\d*:[A-Z]+(?P<last_row>[1-9]\d*)$")


def validate_row_inventory(root: Path) -> Report:
    """Validate self-contained physical-row inventories without opening Excel."""
    import json
    from collections import Counter

    report = Report(path=root)
    if not root.is_dir():
        report.add("error", "inventory.root", "inventory validation requires a pack directory")
        return report

    evidence = root / "evidence"
    manifests = sorted(evidence.glob("*-row-inventory.json")) if evidence.is_dir() else []
    if not manifests:
        report.add("error", "inventory.absent", "no evidence/*-row-inventory.json")
        return report

    for path in manifests:
        try:
            data = _load_json(path)
        except (OSError, json.JSONDecodeError) as error:
            report.add("error", "inventory.json", f"{path.name}: {error}")
            continue
        if not isinstance(data, dict):
            report.add("error", "inventory.shape", f"{path.name}: root must be an object")
            continue
        if data.get("schema_version") not in {ROW_INVENTORY_SCHEMA, LEGACY_ROW_INVENTORY_SCHEMA}:
            report.add(
                "error",
                "inventory.schema",
                f"{path.name}: schema_version must be {ROW_INVENTORY_SCHEMA!r}",
            )

        workbook = data.get("workbook")
        if not isinstance(workbook, dict):
            report.add("error", "inventory.workbook", f"{path.name}: workbook object required")
            workbook = {}
        for field_name in ("source_basename", "sheet"):
            if not isinstance(workbook.get(field_name), str) or not workbook[field_name].strip():
                report.add("error", "inventory.workbook", f"{path.name}: workbook.{field_name} required")
        source_md5 = workbook.get("source_md5")
        if not isinstance(source_md5, str) or not re.fullmatch(r"[0-9a-fA-F]{32}", source_md5):
            report.add("error", "inventory.workbook.pin", f"{path.name}: workbook.source_md5 must be 32 hex")

        rows = data.get("rows")
        if not isinstance(rows, list):
            report.add("error", "inventory.rows", f"{path.name}: rows must be an array")
            continue
        counts = data.get("counts")
        if not isinstance(counts, dict):
            report.add("error", "inventory.counts", f"{path.name}: counts object required")
            counts = {}

        claim_level = data.get("claim_level", "structural")
        if claim_level not in {"structural", "semantic"}:
            report.add("error", "inventory.claim_level", f"{path.name}: claim_level must be structural or semantic")
        semantic_contract = data.get("semantic_contract")
        semantic = claim_level == "semantic"
        period_columns: dict[str, str] = {}
        role_rules: set[str] = set()
        kind_rules: set[str] = set()
        source_class_defs: set[str] = set()
        if semantic:
            if not isinstance(semantic_contract, dict):
                report.add("error", "inventory.semantic.contract", f"{path.name}: semantic_contract object required")
                semantic_contract = {}
            if semantic_contract.get("schema_version") != ROW_SEMANTICS_SCHEMA:
                report.add(
                    "error",
                    "inventory.semantic.schema",
                    f"{path.name}: semantic_contract.schema_version must be {ROW_SEMANTICS_SCHEMA!r}",
                )
            period_window = semantic_contract.get("period_window")
            columns = period_window.get("columns") if isinstance(period_window, dict) else None
            if not isinstance(columns, dict) or not columns:
                report.add("error", "inventory.semantic.periods", f"{path.name}: semantic period column map required")
            else:
                period_columns = {str(column): str(period) for column, period in columns.items()}
                if len(period_columns) != len(set(period_columns.values())):
                    report.add("error", "inventory.semantic.periods", f"{path.name}: semantic periods must be unique")
                for column, period in period_columns.items():
                    if not re.fullmatch(r"[A-Z]+", column) or not re.fullmatch(r"\d{4}-\d{2}", period):
                        report.add(
                            "error",
                            "inventory.semantic.periods",
                            f"{path.name}: invalid semantic period mapping {column!r}: {period!r}",
                        )
            for field_name, target in (
                ("row_role_rules", role_rules),
                ("metric_kind_rules", kind_rules),
                ("source_class_definitions", source_class_defs),
            ):
                definitions = semantic_contract.get(field_name)
                if not isinstance(definitions, dict) or not definitions:
                    report.add(
                        "error",
                        f"inventory.semantic.{field_name}",
                        f"{path.name}: semantic_contract.{field_name} definitions required",
                    )
                else:
                    target.update(str(key) for key in definitions)
            outcome_definitions = semantic_contract.get("outcome_definitions")
            if not isinstance(outcome_definitions, dict) or not INVENTORY_OUTCOMES <= set(outcome_definitions):
                report.add(
                    "error",
                    "inventory.semantic.outcomes",
                    f"{path.name}: definitions required for {sorted(INVENTORY_OUTCOMES)}",
                )

        physical_rows = counts.get("physical_rows")
        metric_rows = counts.get("metric_rows")
        if not isinstance(physical_rows, int) or physical_rows < 1:
            report.add("error", "inventory.denominator.physical", f"{path.name}: positive counts.physical_rows required")
            physical_rows = len(rows)
        if not isinstance(metric_rows, int) or metric_rows < 0:
            report.add("error", "inventory.denominator.metric", f"{path.name}: nonnegative counts.metric_rows required")
            metric_rows = -1
        if len(rows) != physical_rows:
            report.add(
                "error",
                "inventory.denominator.physical",
                f"{path.name}: {len(rows)} rows != physical_rows {physical_rows}",
            )

        dimension = workbook.get("sheet_dimension")
        match = DIMENSION_RE.fullmatch(dimension) if isinstance(dimension, str) else None
        if not match or int(match.group("last_row")) != physical_rows:
            report.add(
                "error",
                "inventory.workbook.dimension",
                f"{path.name}: sheet_dimension must end at physical row {physical_rows}",
            )

        actual_roles: Counter[str] = Counter()
        actual_kinds: Counter[str] = Counter()
        seen_rows: set[int] = set()
        seen_metric_ids: set[str] = set()
        for index, row in enumerate(rows):
            location = f"{path.name} rows[{index}]"
            if not isinstance(row, dict):
                report.add("error", "inventory.row.shape", f"{location}: must be an object")
                continue
            sheet_row = row.get("sheet_row")
            if not isinstance(sheet_row, int) or sheet_row < 1:
                report.add("error", "inventory.row.number", f"{location}: positive sheet_row required")
                continue
            if sheet_row in seen_rows:
                report.add("error", "inventory.row.duplicate", f"{path.name}: duplicate sheet_row {sheet_row}")
            seen_rows.add(sheet_row)

            role = row.get("row_role")
            if role not in ROW_ROLES:
                report.add("error", "inventory.row.role", f"{location}: row_role must be one of {sorted(ROW_ROLES)}")
            else:
                actual_roles[role] += 1
                if role == "unknown":
                    report.add("warn", "inventory.row.unknown", f"{path.name} row {sheet_row}: unresolved row role")

            if not isinstance(row.get("row_label"), str):
                report.add("error", "inventory.row.label", f"{location}: row_label must be a string (blank allowed)")
            basis = row.get("classification_basis")
            if not isinstance(basis, str) or not basis.strip():
                report.add("error", "inventory.row.basis", f"{location}: classification_basis required")
            if semantic and row.get("row_role_rule") not in role_rules:
                report.add(
                    "error",
                    "inventory.semantic.row_rule",
                    f"{path.name} row {sheet_row}: row_role_rule must name a declared rule",
                )

            included = row.get("included_in_metric_denominator")
            if not isinstance(included, bool) or included != (role == "metric"):
                report.add(
                    "error",
                    "inventory.denominator.membership",
                    f"{path.name} row {sheet_row}: included_in_metric_denominator must equal row_role == metric",
                )

            metric_kind = row.get("metric_kind")
            metric_id = row.get("metric_id")
            if role == "metric":
                if metric_kind not in METRIC_KINDS:
                    report.add(
                        "error",
                        "inventory.metric.kind",
                        f"{path.name} row {sheet_row}: metric_kind must be one of {sorted(METRIC_KINDS)}",
                    )
                else:
                    actual_kinds[metric_kind] += 1
                    if metric_kind == "unclear":
                        report.add("warn", "inventory.metric.unclear", f"{path.name} row {sheet_row}: unresolved metric kind")
                if not isinstance(metric_id, str) or not metric_id.strip():
                    report.add("error", "inventory.metric.id", f"{path.name} row {sheet_row}: metric_id required")
                elif metric_id in seen_metric_ids:
                    report.add("error", "inventory.metric.id", f"{path.name}: duplicate metric_id {metric_id}")
                else:
                    seen_metric_ids.add(metric_id)
                if semantic and row.get("metric_kind_rule") not in kind_rules:
                    report.add(
                        "error",
                        "inventory.semantic.metric_rule",
                        f"{path.name} row {sheet_row}: metric_kind_rule must name a declared rule",
                    )
            elif metric_kind is not None or metric_id is not None:
                report.add(
                    "error",
                    "inventory.metric.nonmetric",
                    f"{path.name} row {sheet_row}: non-metric rows cannot carry metric_id or metric_kind",
                )

            if semantic:
                evidence_rows = row.get("outcome_evidence", [])
                declared_outcomes = row.get("outcomes", {})
                lineage = row.get("lineage", {})
                if role != "metric":
                    if evidence_rows or declared_outcomes or row.get("source_classes"):
                        report.add(
                            "error",
                            "inventory.semantic.nonmetric_evidence",
                            f"{path.name} row {sheet_row}: current outcome evidence is metric-only",
                        )
                elif not isinstance(evidence_rows, list) or len(evidence_rows) != len(period_columns):
                    report.add(
                        "error",
                        "inventory.semantic.evidence_count",
                        f"{path.name} row {sheet_row}: one outcome_evidence record required per semantic period",
                    )
                else:
                    actual_outcomes: Counter[str] = Counter()
                    actual_calc_sources: set[str] = set()
                    actual_non_calc: set[str] = set()
                    seen_periods: set[str] = set()
                    expected_by_period = {period: column for column, period in period_columns.items()}
                    for evidence_index, item in enumerate(evidence_rows):
                        item_location = f"{location} outcome_evidence[{evidence_index}]"
                        if not isinstance(item, dict):
                            report.add("error", "inventory.semantic.evidence", f"{item_location}: must be an object")
                            continue
                        period = item.get("period")
                        if period not in expected_by_period or period in seen_periods:
                            report.add("error", "inventory.semantic.period", f"{item_location}: bad or duplicate period {period!r}")
                        else:
                            seen_periods.add(period)
                            expected_a1 = f"{expected_by_period[period]}{sheet_row}"
                            if item.get("a1") != expected_a1:
                                report.add(
                                    "error",
                                    "inventory.semantic.a1",
                                    f"{item_location}: a1 must be {expected_a1}",
                                )
                        outcome = item.get("outcome")
                        if outcome not in INVENTORY_OUTCOMES:
                            report.add("error", "inventory.semantic.outcome", f"{item_location}: invalid outcome {outcome!r}")
                            continue
                        actual_outcomes[outcome] += 1
                        comparison_rule = item.get("comparison_rule")
                        if not isinstance(comparison_rule, str) or not comparison_rule.strip():
                            report.add("error", "inventory.semantic.comparison", f"{item_location}: comparison_rule required")
                        source_class = item.get("source_class")
                        if source_class not in source_class_defs:
                            report.add(
                                "error",
                                "inventory.semantic.source_class",
                                f"{item_location}: source_class must have a semantic definition",
                            )
                        if outcome in {"PASS", "FAIL"}:
                            actual_calc_sources.add(source_class)
                            if not isinstance(item.get("delta"), (int, float)):
                                report.add("error", "inventory.semantic.delta", f"{item_location}: numeric delta required")
                        else:
                            non_calc_class = item.get("non_calc_class")
                            if not isinstance(non_calc_class, str) or not non_calc_class.strip():
                                report.add(
                                    "error",
                                    "inventory.semantic.non_calc",
                                    f"{item_location}: non_calc_class required for NOT_APPLICABLE",
                                )
                            else:
                                actual_non_calc.add(non_calc_class)
                    normalized_outcomes = (
                        {str(key): value for key, value in declared_outcomes.items() if value}
                        if isinstance(declared_outcomes, dict)
                        else None
                    )
                    if normalized_outcomes != dict(sorted(actual_outcomes.items())):
                        report.add(
                            "error",
                            "inventory.semantic.outcome_counts",
                            f"{path.name} row {sheet_row}: outcomes do not reconcile with embedded evidence",
                        )
                    expected_lineage = {
                        "calculation_source_classes": sorted(actual_calc_sources),
                        "non_calc_classes": sorted(actual_non_calc),
                    }
                    if row.get("source_classes") != expected_lineage["calculation_source_classes"]:
                        report.add(
                            "error",
                            "inventory.semantic.source_classes",
                            f"{path.name} row {sheet_row}: source_classes do not reconcile with embedded evidence",
                        )
                    if lineage != expected_lineage:
                        report.add(
                            "error",
                            "inventory.semantic.lineage",
                            f"{path.name} row {sheet_row}: lineage does not reconcile; actual={expected_lineage}",
                        )

            cells = row.get("cells")
            if not isinstance(cells, list):
                report.add("error", "inventory.row.cells", f"{path.name} row {sheet_row}: cells must be an array")
                continue
            seen_cells: set[str] = set()
            for cell_index, cell in enumerate(cells):
                if not isinstance(cell, dict):
                    report.add("error", "inventory.cell.shape", f"{location} cells[{cell_index}]: must be an object")
                    continue
                a1 = cell.get("a1")
                cell_match = CELL_RE.fullmatch(a1) if isinstance(a1, str) else None
                if not cell_match or int(cell_match.group("row")) != sheet_row:
                    report.add("error", "inventory.cell.address", f"{location}: bad cell address {a1!r}")
                elif a1 in seen_cells:
                    report.add("error", "inventory.cell.duplicate", f"{location}: duplicate cell {a1}")
                else:
                    seen_cells.add(a1)
                if "value" not in cell and "formula" not in cell:
                    report.add("error", "inventory.cell.content", f"{location} {a1}: value or formula required")

        expected_rows = set(range(1, physical_rows + 1))
        if seen_rows != expected_rows:
            missing = sorted(expected_rows - seen_rows)
            extra = sorted(seen_rows - expected_rows)
            report.add(
                "error",
                "inventory.row.coverage",
                f"{path.name}: rows must cover 1..{physical_rows}; missing={missing}, extra={extra}",
            )
        if actual_roles.get("metric", 0) != metric_rows:
            report.add(
                "error",
                "inventory.denominator.metric",
                f"{path.name}: classified metrics {actual_roles.get('metric', 0)} != metric_rows {metric_rows}",
            )

        for field_name, actual in (("row_roles", actual_roles), ("metric_kinds", actual_kinds)):
            declared = counts.get(field_name)
            normalized = {str(k): v for k, v in declared.items() if v} if isinstance(declared, dict) else None
            if normalized != dict(sorted(actual.items())):
                report.add(
                    "error",
                    f"inventory.counts.{field_name}",
                    f"{path.name}: counts.{field_name} does not reconcile; actual={dict(sorted(actual.items()))}",
                )

    return report


def format_report(report: Report) -> str:
    lines = [f"{report.path}:"]
    if not report.problems:
        lines.append("  OK")
        return "\n".join(lines)
    for p in report.problems:
        lines.append(f"  {p.level.upper():5} {p.rule}: {p.detail}")
    return "\n".join(lines)


def _write_minimal_pack(root: Path) -> None:
    (root / "concepts").mkdir(parents=True)
    (root / "log.md").write_text("# log\n\n- init\n", encoding="utf-8")
    (root / "index.md").write_text(
        """---
okf_version: "0.2"
odwf_version: "0.2.2"
profile: odwf
type: warehouse
odwf_id: odwf:demo:warehouse
title: "Demo warehouse"
status: contracting
oracle: odwf:demo:oracle:bronze
layers: [odwf:demo:layer:bronze]
providers: [odwf:demo:provider:source]
hosts: [odwf:demo:host:local]
credential_plane: odwf:demo:credential-plane:env
authority: [odwf:demo:authority:readonly]
non_goals: ["writes"]
verified:
  by: human:daniel
  at: 2026-08-07
  method: "selftest fixture"
  stale_after: 2027-08-07
---

# Demo warehouse
""",
        encoding="utf-8",
    )
    concepts = {
        "oracle-bronze.md": """---
okf_version: "0.2"
odwf_version: "0.2.2"
type: warehouse-concept
odwf_id: odwf:demo:oracle:bronze
kind: oracle
title: "Bronze oracle"
layer: odwf:demo:layer:bronze
rule: "Bronze arbitrates"
verified:
  by: human:daniel
  at: 2026-08-07
  method: "selftest"
---
""",
        "layer-bronze.md": """---
okf_version: "0.2"
odwf_version: "0.2.2"
type: warehouse-concept
odwf_id: odwf:demo:layer:bronze
kind: layer
title: "Bronze"
layer_name: bronze
role: source-shaped
trusted_as_oracle: true
verified:
  by: human:daniel
  at: 2026-08-07
  method: "selftest"
---
""",
        "provider.md": """---
okf_version: "0.2"
odwf_version: "0.2.2"
type: warehouse-concept
odwf_id: odwf:demo:provider:source
kind: provider
title: "Source"
verified:
  by: human:daniel
  at: 2026-08-07
  method: "selftest"
---
""",
        "host.md": """---
okf_version: "0.2"
odwf_version: "0.2.2"
type: warehouse-concept
odwf_id: odwf:demo:host:local
kind: host
title: "Local"
address_kind: local
selection_rule: "localhost"
verified:
  by: human:daniel
  at: 2026-08-07
  method: "selftest"
---
""",
        "cred.md": """---
okf_version: "0.2"
odwf_version: "0.2.2"
type: warehouse-concept
odwf_id: odwf:demo:credential-plane:env
kind: credential-plane
title: "Env file"
plane: env-file-on-host
locator: ".env.local on host"
forbids: ["print password"]
verified:
  by: human:daniel
  at: 2026-08-07
  method: "selftest"
---
""",
        "auth.md": """---
okf_version: "0.2"
odwf_version: "0.2.2"
type: warehouse-concept
odwf_id: odwf:demo:authority:readonly
kind: authority-boundary
title: "Read only"
allows: ["SELECT"]
denies: ["writes", "DDL"]
network: "private"
verified:
  by: human:daniel
  at: 2026-08-07
  method: "selftest"
---
""",
    }
    for name, body in concepts.items():
        (root / "concepts" / name).write_text(body, encoding="utf-8")


def selftest() -> int:
    with TemporaryDirectory() as tmp:
        root = Path(tmp) / "pack"
        root.mkdir()
        _write_minimal_pack(root)
        reports = validate_path(root, strict=False)
        errs = [e for r in reports for e in r.errors]
        if errs:
            for r in reports:
                print(format_report(r))
            print("SELFTEST FAIL: minimal contracting pack should pass")
            return 1
        # broken: done-like operating without proof
        face = (root / "index.md").read_text(encoding="utf-8")
        face = face.replace("status: contracting", "status: operating")
        (root / "index.md").write_text(face, encoding="utf-8")
        reports = validate_path(root, strict=False)
        errs = [e for r in reports for e in r.errors]
        if not errs:
            print("SELFTEST FAIL: operating without first_slice should error")
            return 1
    print("SELFTEST OK")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="odwf-validate", description="Validate ODWF packs")
    p.add_argument("paths", nargs="*", type=Path, help="pack dirs or markdown files")
    p.add_argument("--strict", action="store_true", help="warnings become errors; require imports")
    modes = p.add_mutually_exclusive_group()
    modes.add_argument(
        "--progress",
        action="store_true",
        help="progress fairness only (SPEC §8a.6): full-window coverage + evidence paths",
    )
    modes.add_argument(
        "--inventory",
        action="store_true",
        help="source-complete workbook row inventory only (SPEC §8b)",
    )
    p.add_argument("--selftest", action="store_true", help="run built-in fixture checks")
    args = p.parse_args(argv)

    if args.selftest:
        return selftest()
    if not args.paths:
        p.error("provide paths or --selftest")

    exit_code = 0
    for path in args.paths:
        if not path.exists():
            print(f"{path}: ERROR path.missing: not found")
            exit_code = 1
            continue
        if args.progress:
            report = validate_progress(path if path.is_dir() else path.parent)
            if args.strict:
                for prob in list(report.problems):
                    if prob.level == "warn":
                        prob.level = "error"
            print(format_report(report))
            if report.errors:
                exit_code = 1
            continue
        if args.inventory:
            report = validate_row_inventory(path if path.is_dir() else path.parent)
            if args.strict:
                for prob in list(report.problems):
                    if prob.level == "warn":
                        prob.level = "error"
            print(format_report(report))
            if report.errors:
                exit_code = 1
            continue
        for report in validate_path(path, strict=args.strict):
            print(format_report(report))
            if report.errors:
                exit_code = 1
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
