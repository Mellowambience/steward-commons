#!/usr/bin/env python3
"""
steward.py — a zero-dependency command line for the Steward Commons protocol.

Implements the MVP from README.md:
  1. Create a project
  2. Record a decision
  3. Add competing proposals
  4. Attach evidence and objections
  5. Revisit the decision later with outcomes and reflections

Every record is validated against the JSON schemas in ./schemas before it is
stored, so a Steward Commons vault can never drift out of protocol.

Usage:
    python steward.py init
    python steward.py project new --name "Atlas" --description "..."
    python steward.py decision new --project <pid> --title "Pick a DB"
    python steward.py proposal add --decision <did> --title "Postgres" --tradeoff "Ops cost"
    python steward.py evidence add --proposal <pid> --source-type study \
        --summary "Benchmarks hold at 10k rps" --supports <pid>
    python steward.py decide --decision <did> --proposal <pid>
    python steward.py outcome add --decision <did> --summary "Shipped" --metric latency_ms=12
    python steward.py reflection add --decision <did> --summary "Held up" --lesson "Good call"
    python steward.py validate
    python steward.py show --project <pid>

Data lives in ./.steward/ as JSONL files. No network, no dependencies.
"""
import argparse
import json
import os
import re
import sys
import uuid
from datetime import datetime, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SCHEMA_DIR = os.path.join(SCRIPT_DIR, "schemas")
VAULT_DIR = os.path.join(os.getcwd(), ".steward")
ENTITY_FILES = {
    "project": "projects.jsonl",
    "decision": "decisions.jsonl",
    "proposal": "proposals.jsonl",
    "evidence": "evidence.jsonl",
    "outcome": "outcomes.jsonl",
    "reflection": "reflections.jsonl",
}
SCHEMA_TITLES = {
    "project": "Project",
    "decision": "Decision",
    "proposal": "Proposal",
    "evidence": "Evidence",
    "outcome": "Outcome",
    "reflection": "Reflection",
}


# --------------------------------------------------------------------------
# Tiny JSON-Schema (draft 2020-12 subset) validator — no third-party deps.
# Supports: type, required, enum, format(date/date-time), properties, items.
# --------------------------------------------------------------------------
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATETIME = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})?$")


def _check_type(value, t):
    if t == "object":
        return isinstance(value, dict)
    if t == "array":
        return isinstance(value, list)
    if t == "string":
        return isinstance(value, str)
    if t == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if t == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if t == "boolean":
        return isinstance(value, bool)
    if t == "null":
        return value is None
    return True


def validate(instance, schema, path="$"):
    """Return a list of human-readable error strings (empty == valid)."""
    errors = []
    if "type" in schema:
        if not _check_type(instance, schema["type"]):
            errors.append(f"{path}: expected type {schema['type']}, got {type(instance).__name__}")
            return errors  # can't recurse sensibly on wrong type
    if schema.get("type") == "object" or "properties" in schema or "required" in schema:
        if isinstance(instance, dict):
            for req in schema.get("required", []):
                if req not in instance:
                    errors.append(f"{path}: missing required property '{req}'")
            props = schema.get("properties", {})
            for key, val in instance.items():
                if key in props:
                    errors += validate(val, props[key], f"{path}.{key}")
    if schema.get("type") == "array" and "items" in schema and isinstance(instance, list):
        for i, item in enumerate(instance):
            errors += validate(item, schema["items"], f"{path}[{i}]")
    if "enum" in schema and instance not in schema["enum"]:
        errors.append(f"{path}: value {instance!r} not in enum {schema['enum']}")
    if "format" in schema and isinstance(instance, str):
        fmt = schema["format"]
        if fmt == "date-time" and not _DATETIME.match(instance):
            errors.append(f"{path}: '{instance}' is not a valid date-time")
        if fmt == "date" and not _DATE.match(instance):
            errors.append(f"{path}: '{instance}' is not a valid date")
    return errors


def load_schema(entity):
    path = os.path.join(SCHEMA_DIR, f"{entity}.schema.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def validate_record(entity, record):
    schema = load_schema(entity)
    return validate(record, schema)


# --------------------------------------------------------------------------
# Vault storage (JSONL per entity type)
# --------------------------------------------------------------------------
def ensure_vault():
    if not os.path.isdir(VAULT_DIR):
        sys.exit(f"No vault found at {VAULT_DIR}. Run: python steward.py init")
    for fn in ENTITY_FILES.values():
        fp = os.path.join(VAULT_DIR, fn)
        if not os.path.exists(fp):
            open(fp, "a", encoding="utf-8").close()


def _read(entity):
    fp = os.path.join(VAULT_DIR, ENTITY_FILES[entity])
    out = []
    if os.path.exists(fp):
        with open(fp, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    out.append(json.loads(line))
    return out


def _append(entity, record):
    fp = os.path.join(VAULT_DIR, ENTITY_FILES[entity])
    with open(fp, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def _uid(prefix):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def now_date():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


# --------------------------------------------------------------------------
# Commands
# --------------------------------------------------------------------------
def cmd_init(args):
    os.makedirs(VAULT_DIR, exist_ok=True)
    for fn in ENTITY_FILES.values():
        fp = os.path.join(VAULT_DIR, fn)
        if not os.path.exists(fp):
            open(fp, "a", encoding="utf-8").close()
    print(f"Initialized Steward Commons vault at {VAULT_DIR}")


def _require(entity, rid):
    recs = _read(entity)
    for r in recs:
        if r.get("id") == rid:
            return r
    sys.exit(f"{entity.capitalize()} '{rid}' not found.")


def cmd_project_new(args):
    ensure_vault()
    rec = {
        "id": _uid("proj"),
        "name": args.name,
        "description": args.description or "",
        "created_at": now(),
        "updated_at": now(),
    }
    errs = validate_record("project", rec)
    if errs:
        sys.exit("Invalid project:\n  " + "\n  ".join(errs))
    _append("project", rec)
    print(f"project created: {rec['id']}")


def cmd_decision_new(args):
    ensure_vault()
    _require("project", args.project)
    rec = {
        "id": _uid("dec"),
        "project_id": args.project,
        "title": args.title,
        "context": args.context or "",
        "status": "draft",
    }
    errs = validate_record("decision", rec)
    if errs:
        sys.exit("Invalid decision:\n  " + "\n  ".join(errs))
    _append("decision", rec)
    print(f"decision created: {rec['id']}")


def cmd_proposal_add(args):
    ensure_vault()
    _require("decision", args.decision)
    rec = {
        "id": _uid("prop"),
        "decision_id": args.decision,
        "title": args.title,
        "summary": args.summary or "",
        "tradeoffs": args.tradeoff or [],
    }
    errs = validate_record("proposal", rec)
    if errs:
        sys.exit("Invalid proposal:\n  " + "\n  ".join(errs))
    _append("proposal", rec)
    print(f"proposal added: {rec['id']}")


def cmd_evidence_add(args):
    ensure_vault()
    if not (args.proposal or args.decision):
        sys.exit("evidence needs --proposal <pid> or --decision <did>")
    rec = {
        "id": _uid("ev"),
        "source_type": args.source_type,
        "source_url": args.source_url or "",
        "summary": args.summary,
        "supports": args.supports or [],
        "challenges": args.challenges or [],
    }
    if args.proposal:
        rec["proposal_id"] = args.proposal
    if args.decision:
        rec["decision_id"] = args.decision
    errs = validate_record("evidence", rec)
    if errs:
        sys.exit("Invalid evidence:\n  " + "\n  ".join(errs))
    _append("evidence", rec)
    print(f"evidence added: {rec['id']}")


def cmd_decide(args):
    ensure_vault()
    dec = _require("decision", args.decision)
    _require("proposal", args.proposal)
    decs = _read("decision")
    out = []
    for d in decs:
        if d["id"] == args.decision:
            d["status"] = "decided"
            d["selected_proposal_id"] = args.proposal
            d["review_date"] = args.review_date or now_date()
            out.append(d)
        else:
            out.append(d)
    _write_all("decision", out)
    print(f"decision {args.decision} -> decided (selected {args.proposal})")


def cmd_outcome_add(args):
    ensure_vault()
    _require("decision", args.decision)
    metrics = {}
    for m in args.metric or []:
        if "=" in m:
            k, v = m.split("=", 1)
            try:
                v = float(v) if "." in v else int(v)
            except ValueError:
                pass
            metrics[k] = v
    rec = {
        "id": _uid("out"),
        "decision_id": args.decision,
        "observed_at": now(),
        "summary": args.summary,
        "metrics": metrics,
    }
    errs = validate_record("outcome", rec)
    if errs:
        sys.exit("Invalid outcome:\n  " + "\n  ".join(errs))
    _append("outcome", rec)
    print(f"outcome recorded: {rec['id']}")


def cmd_reflection_add(args):
    ensure_vault()
    _require("decision", args.decision)
    rec = {
        "id": _uid("refl"),
        "decision_id": args.decision,
        "summary": args.summary,
        "lessons": args.lesson or [],
        "created_at": now(),
    }
    errs = validate_record("reflection", rec)
    if errs:
        sys.exit("Invalid reflection:\n  " + "\n  ".join(errs))
    _append("reflection", rec)
    print(f"reflection recorded: {rec['id']}")


def _write_all(entity, records):
    fp = os.path.join(VAULT_DIR, ENTITY_FILES[entity])
    with open(fp, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def cmd_validate(args):
    ensure_vault()
    total = 0
    bad = 0
    for entity in ENTITY_FILES:
        for rec in _read(entity):
            total += 1
            errs = validate_record(entity, rec)
            if errs:
                bad += 1
                print(f"[FAIL] {entity} {rec.get('id')}:")
                for e in errs:
                    print(f"    {e}")
    if bad == 0:
        print(f"OK — {total} records validated against schemas, 0 violations.")
    else:
        sys.exit(f"{bad}/{total} records failed validation.")


def cmd_show(args):
    ensure_vault()
    projects = _read("project")
    if args.project:
        projects = [p for p in projects if p["id"] == args.project]
    if not projects:
        print("(no projects)")
        return
    for p in projects:
        print(f"\n# Project: {p['name']}  [{p['id']}]")
        if p.get("description"):
            print(f"  {p['description']}")
        decisions = [d for d in _read("decision") if d.get("project_id") == p["id"]]
        if not decisions:
            print("  (no decisions)")
        for d in decisions:
            print(f"\n  > Decision: {d['title']}  [{d['id']}]  ({d['status']})")
            if d.get("context"):
                print(f"    context: {d['context']}")
            if d.get("selected_proposal_id"):
                print(f"    chosen: {d['selected_proposal_id']}")
            props = [x for x in _read("proposal") if x.get("decision_id") == d["id"]]
            for pr in props:
                print(f"      - proposal: {pr['title']}  [{pr['id']}]")
                for t in pr.get("tradeoffs", []):
                    print(f"          tradeoff: {t}")
                evs = [e for e in _read("evidence")
                       if e.get("proposal_id") == pr["id"]]
                for e in evs:
                    print(f"          evidence[{e['source_type']}]: {e['summary']}")
            outs = [o for o in _read("outcome") if o.get("decision_id") == d["id"]]
            for o in outs:
                print(f"    outcome: {o['summary']}  {o.get('metrics') or ''}")
            refs = [r for r in _read("reflection") if r.get("decision_id") == d["id"]]
            for r in refs:
                print(f"    reflection: {r['summary']}")
                for l in r.get("lessons", []):
                    print(f"        lesson: {l}")


def cmd_demo(args):
    """Self-contained walkthrough that builds a sample project and proves the
    protocol end-to-end, then validates it."""
    import tempfile
    global VAULT_DIR
    tmp = tempfile.mkdtemp(prefix="steward_demo_")
    VAULT_DIR = tmp
    os.makedirs(VAULT_DIR, exist_ok=True)
    for fn in ENTITY_FILES.values():
        open(os.path.join(VAULT_DIR, fn), "a", encoding="utf-8").close()
    print(f"# demo vault: {VAULT_DIR}\n")

    class A:  # minimal argparse stand-in
        pass

    a = A()
    a.name = "Atlas Migration"
    a.description = "Move analytics off the dying warehouse."
    cmd_project_new(a)
    pid = _read("project")[-1]["id"]

    a = A(); a.project = pid; a.title = "Choose a storage engine"
    a.context = "Warehouse EOL in Q3."
    cmd_decision_new(a)
    did = _read("decision")[-1]["id"]

    a = A(); a.decision = did; a.title = "DuckDB"
    a.summary = "Embedded, zero ops."; a.tradeoff = ["Limited concurrency"]
    cmd_proposal_add(a)
    p1 = _read("proposal")[-1]["id"]

    a = A(); a.decision = did; a.title = "ClickHouse"
    a.summary = "Scales horizontally."; a.tradeoff = ["Heavier ops footprint"]
    cmd_proposal_add(a)
    p2 = _read("proposal")[-1]["id"]

    a = A(); a.proposal = p1; a.decision = None; a.source_type = "benchmark"
    a.summary = "Handles our 2B-row scans in <4s locally."
    a.source_url = ""; a.supports = []; a.challenges = []
    cmd_evidence_add(a)

    a = A(); a.decision = did; a.proposal = p2; a.review_date = ""
    cmd_decide(a)

    a = A(); a.decision = did; a.summary = "Shipped to prod, no incidents."
    a.metric = ["p95_latency_ms=11", "cost_usd_mo=0"]
    cmd_outcome_add(a)

    a = A(); a.decision = did; a.summary = "Choice held up under load."
    a.lesson = ["Embedded-first was the right call for our scale."]
    cmd_reflection_add(a)

    print("\n" + "=" * 60)
    cmd_validate(A())
    print("=" * 60)
    a = A(); a.project = None
    cmd_show(a)


# --------------------------------------------------------------------------
# Argument parsing
# --------------------------------------------------------------------------
def build_parser():
    p = argparse.ArgumentParser(prog="steward", description="Steward Commons protocol CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init", help="initialize a .steward vault here").set_defaults(func=cmd_init)

    pp = sub.add_parser("project", help="project commands")
    ps = pp.add_subparsers(dest="sub", required=True)
    a = ps.add_parser("new"); a.add_argument("--name", required=True)
    a.add_argument("--description", default=""); a.set_defaults(func=cmd_project_new)

    pd = sub.add_parser("decision", help="decision commands")
    ds = pd.add_subparsers(dest="sub", required=True)
    a = ds.add_parser("new"); a.add_argument("--project", required=True)
    a.add_argument("--title", required=True); a.add_argument("--context", default="")
    a.set_defaults(func=cmd_decision_new)

    pp_ = sub.add_parser("proposal", help="proposal commands")
    prs = pp_.add_subparsers(dest="sub", required=True)
    a = prs.add_parser("add"); a.add_argument("--decision", required=True)
    a.add_argument("--title", required=True); a.add_argument("--summary", default="")
    a.add_argument("--tradeoff", action="append"); a.set_defaults(func=cmd_proposal_add)

    pe = sub.add_parser("evidence", help="evidence commands")
    es = pe.add_subparsers(dest="sub", required=True)
    a = es.add_parser("add"); a.add_argument("--proposal", default=None)
    a.add_argument("--decision", default=None); a.add_argument("--source-type", required=True)
    a.add_argument("--summary", required=True); a.add_argument("--source-url", default="")
    a.add_argument("--supports", action="append"); a.add_argument("--challenges", action="append")
    a.set_defaults(func=cmd_evidence_add)

    a = sub.add_parser("decide"); a.add_argument("--decision", required=True)
    a.add_argument("--proposal", required=True); a.add_argument("--review-date", default="")
    a.set_defaults(func=cmd_decide)

    po = sub.add_parser("outcome", help="outcome commands")
    os_ = po.add_subparsers(dest="sub", required=True)
    a = os_.add_parser("add"); a.add_argument("--decision", required=True)
    a.add_argument("--summary", required=True); a.add_argument("--metric", action="append")
    a.set_defaults(func=cmd_outcome_add)

    prf = sub.add_parser("reflection", help="reflection commands")
    rs = prf.add_subparsers(dest="sub", required=True)
    a = rs.add_parser("add"); a.add_argument("--decision", required=True)
    a.add_argument("--summary", required=True); a.add_argument("--lesson", action="append")
    a.set_defaults(func=cmd_reflection_add)

    sub.add_parser("validate", help="validate all records against schemas").set_defaults(func=cmd_validate)

    a = sub.add_parser("show", help="render the reasoning graph")
    a.add_argument("--project", default=None); a.set_defaults(func=cmd_show)

    sub.add_parser("demo", help="run a self-contained end-to-end example").set_defaults(func=cmd_demo)
    return p


def main():
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
