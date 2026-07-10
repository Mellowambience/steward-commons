# Steward CLI

A zero-dependency command line that turns the Steward Commons protocol into
something you can actually run. Every record is validated against the JSON
schemas in `schemas/` before it is stored, so a vault can never drift out of
protocol.

## Install

No dependencies. Requires Python 3.8+.

```bash
# from the repo root
python steward.py --help
```

## Quick start

```bash
python steward.py init                                  # create ./.steward vault

python steward.py project new --name "Atlas" \
    --description "Move analytics off the dying warehouse"

python steward.py decision new --project <proj_id> \
    --title "Choose a storage engine" --context "Warehouse EOL in Q3."

python steward.py proposal add --decision <dec_id> \
    --title "DuckDB" --summary "Embedded, zero ops" --tradeoff "Limited concurrency"

python steward.py evidence add --proposal <prop_id> \
    --source-type benchmark --summary "Scans 2B rows in <4s"

python steward.py decide --decision <dec_id> --proposal <prop_id>

python steward.py outcome add --decision <dec_id> \
    --summary "Shipped, no incidents" --metric p95_latency_ms=11

python steward.py reflection add --decision <dec_id> \
    --summary "Held up under load" --lesson "Embedded-first was right"

python steward.py validate                                 # check every record vs schemas
python steward.py show --project <proj_id>                 # render the reasoning graph
python steward.py demo                                     # self-contained end-to-end example
```

## Storage

Records live in `./.steward/` as JSONL (one object per line), one file per
entity type: `projects.jsonl`, `decisions.jsonl`, `proposals.jsonl`,
`evidence.jsonl`, `outcomes.jsonl`, `reflections.jsonl`. This is intentionally
plain and portable — fork it, diff it, audit it.

## Commands

| Command | Purpose |
| --- | --- |
| `init` | Create a `.steward` vault in the current directory |
| `project new` | Create a project (id, name, description) |
| `decision new` | Record a decision inside a project |
| `proposal add` | Add a competing proposal to a decision |
| `evidence add` | Attach evidence/objections to a proposal or decision |
| `decide` | Mark a decision decided and select a proposal |
| `outcome add` | Record what happened after the decision |
| `reflection add` | Capture lessons learned |
| `validate` | Validate all records against `schemas/*.json` |
| `show` | Render the full reasoning graph as text |
| `demo` | Build + validate a sample project end-to-end |

## Why this exists

The README defines a five-point MVP. This CLI is the reference implementation
of that MVP: it proves the protocol is not just a document but a working
standard. Because validation is built in, a Steward Commons vault is
self-policing — non-conformant records are rejected or flagged, not silently
accepted.
