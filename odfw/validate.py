"""Validate Open Data Warehouse Format v0.2.1 documents and packs.

Stdlib only. The parser accepts the deliberately small YAML subset ODFW specifies
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

from . import ODFW_VERSION, OKF_VERSION

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
}
PLACEHOLDERS = {"tbd", "todo", "later", "unknown", "none", "n/a", "placeholder"}
NON_AUTHORITATIVE_PLANES = {"catalog", "cache", "mcp", "dashboard"}
ID_RE = re.compile(r"^odfw:[a-z0-9][a-z0-9._-]*(?::[a-z0-9][a-z0-9._-]*){1,6}$")
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
    odfw_v = str(meta.get("odfw_version", ""))
    if not re.fullmatch(r"\d+\.\d+\.\d+", odfw_v):
        report.add("error", "version.odfw", f"{doc.path.name}: odfw_version must be X.Y.Z")
    elif odfw_v.rsplit(".", 1)[0] != str(meta.get("okf_version", "")):
        report.add("error", "version.align", f"{doc.path.name}: odfw_version X.Y must equal okf_version")
    if meta.get("type") not in TYPES:
        report.add("error", "type", f"{doc.path.name}: type must be warehouse or warehouse-concept")
    if _is_placeholder(meta.get("title")) or not meta.get("title"):
        report.add("error", "title", f"{doc.path.name}: title required")
    odfw_id = meta.get("odfw_id")
    if not isinstance(odfw_id, str) or not ID_RE.match(odfw_id):
        report.add("error", "id", f"{doc.path.name}: odfw_id must match odfw:<warehouse>:…")


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
        odfw_id = meta.get("odfw_id")
        if isinstance(odfw_id, str) and ID_RE.match(odfw_id):
            if odfw_id in by_id:
                report.add("error", "id.duplicate", f"{odfw_id} in {doc.path.name} and {by_id[odfw_id].path.name}")
            else:
                by_id[odfw_id] = doc

    # face-specific
    fm = face.meta
    if fm.get("type") != "warehouse":
        report.add("error", "face.type", "index.md must have type: warehouse")
    status = fm.get("status")
    if status not in STATUSES:
        report.add("error", "face.status", f"status must be one of {sorted(STATUSES)}")

    for field_name in ("title", "odfw_id"):
        if _is_placeholder(fm.get(field_name)) or not fm.get(field_name):
            report.add("error", "face.required", f"face missing non-placeholder {field_name}")

    # version alignment
    okf_v = str(fm.get("okf_version", ""))
    odfw_v = str(fm.get("odfw_version", ""))
    if okf_v != OKF_VERSION:
        report.add("error", "version.okf", f"okf_version must be {OKF_VERSION!r}")
    if not re.fullmatch(r"\d+\.\d+\.\d+", odfw_v):
        report.add("error", "version.odfw", "odfw_version must be X.Y.Z")
    elif odfw_v.rsplit(".", 1)[0] != okf_v:
        report.add("error", "version.align", "odfw_version X.Y must equal okf_version")

    if not (root / "log.md").is_file() and not any(p.name == "log.md" for p in extras):
        report.add("warn", "log.missing", "pack should include append-only log.md")

    # concept docs
    for doc in docs:
        if doc.meta.get("type") != "warehouse-concept":
            report.add("error", "concept.type", f"{doc.path.name}: type must be warehouse-concept")
        kind = doc.meta.get("kind")
        if kind not in KINDS:
            report.add("error", "concept.kind", f"{doc.path.name}: kind must be one of ODFW kinds")
        odfw_id = doc.meta.get("odfw_id")
        if not isinstance(odfw_id, str) or not ID_RE.match(odfw_id):
            report.add("error", "concept.id", f"{doc.path.name}: invalid odfw_id")
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
            tokens = set(str(odfw_id).split(":"))
            allowed = kind_aliases.get(str(kind), {str(kind)})
            if tokens.isdisjoint(allowed):
                report.add(
                    "warn",
                    "concept.id.kind",
                    f"{doc.path.name}: odfw_id should include kind {kind!r}",
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
            compare = doc.meta.get("compare")
            if compare not in COMPARE_MODES:
                report.add("error", "check.compare", f"{doc.path.name}: compare must be vector|scalar")
            elif compare == "scalar" and status == "operating":
                report.add(
                    "warn" if not strict else "error",
                    "check.scalar",
                    f"{doc.path.name}: scalar compare forbidden for operating packs under strict",
                )
            if not _refs(doc.meta.get("metric_contract")) and not _refs(doc.meta.get("sql_packet")):
                report.add("error", "check.target", f"{doc.path.name}: metric_contract or sql_packet required")
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
        sid = doc.meta.get("odfw_id")
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
        oid = doc.meta.get("odfw_id")
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
odfw_version: "0.2.1"
profile: odfw
type: warehouse
odfw_id: odfw:demo:warehouse
title: "Demo warehouse"
status: contracting
oracle: odfw:demo:oracle:bronze
layers: [odfw:demo:layer:bronze]
providers: [odfw:demo:provider:source]
hosts: [odfw:demo:host:local]
credential_plane: odfw:demo:credential-plane:env
authority: [odfw:demo:authority:readonly]
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
odfw_version: "0.2.1"
type: warehouse-concept
odfw_id: odfw:demo:oracle:bronze
kind: oracle
title: "Bronze oracle"
layer: odfw:demo:layer:bronze
rule: "Bronze arbitrates"
verified:
  by: human:daniel
  at: 2026-08-07
  method: "selftest"
---
""",
        "layer-bronze.md": """---
okf_version: "0.2"
odfw_version: "0.2.1"
type: warehouse-concept
odfw_id: odfw:demo:layer:bronze
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
odfw_version: "0.2.1"
type: warehouse-concept
odfw_id: odfw:demo:provider:source
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
odfw_version: "0.2.1"
type: warehouse-concept
odfw_id: odfw:demo:host:local
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
odfw_version: "0.2.1"
type: warehouse-concept
odfw_id: odfw:demo:credential-plane:env
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
odfw_version: "0.2.1"
type: warehouse-concept
odfw_id: odfw:demo:authority:readonly
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
    p = argparse.ArgumentParser(prog="odfw-validate", description="Validate ODFW packs")
    p.add_argument("paths", nargs="*", type=Path, help="pack dirs or markdown files")
    p.add_argument("--strict", action="store_true", help="warnings become errors; require imports")
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
        for report in validate_path(path, strict=args.strict):
            print(format_report(report))
            if report.errors:
                exit_code = 1
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
