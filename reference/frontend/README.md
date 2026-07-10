# Steward Commons — Web UI (reference frontend)

A fully **client-side** vault for the Steward Commons protocol. No server, no
build step, no dependencies beyond a browser. Records are validated against the
same JSON schemas used by `steward.py` before they are saved.

## Run it

It is a single static file served by GitHub Pages:

**https://mellowambience.github.io/steward-commons/reference/frontend/index.html**

(That is the Web UI's own GitHub Pages sub-path, mounted under the main
`steward-commons` site. Opening `index.html` directly from disk also works —
it is 100% offline.)

## What it does

- Forms for all six entity types: project, decision, proposal, evidence,
  outcome, reflection. (A dedicated "Decide" form marks a decision decided and
  selects the winning proposal.)
- **Live schema validation** on every save — identical rules to `steward.py`.
- A **live Mermaid reasoning graph** that re-renders as you build.
- **Demo seed**, **Validate all**, **import / export** (full vault JSON and
  CLI-compatible JSONL), and **clear**.

## Interop with the CLI

The **Export CLI JSONL** button writes one file per entity
(`projects.jsonl`, `decisions.jsonl`, `proposals.jsonl`, `evidence.jsonl`,
`outcomes.jsonl`, `reflections.jsonl`) — the exact format `steward.py` reads.

Drop those files in a folder next to `steward.py` and run:

```bash
python steward.py validate   # checks every record against schemas/*.json
python steward.py show        # renders the reasoning graph as text
```

The Web UI and the Python CLI share one protocol and one set of schemas, so a
vault built in the browser validates cleanly under the CLI and vice versa.

## Files

- `index.html` — the entire app (HTML + CSS + JS, no external deps except the
  Mermaid CDN for the graph).
- Vault state persists in the browser's `localStorage` under the key
  `steward_commons_vault_v1`.
