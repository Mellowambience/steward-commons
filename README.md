# Steward Commons

![Steward Compatible v1.0](assets/steward-compatible-badge.svg)

**An open protocol for preserving how ideas, decisions, evidence, and outcomes evolve.**

Steward Commons is a protocol-first project for making reasoning durable. It captures not only final decisions, but the proposals, evidence, objections, tradeoffs, reflections, and later outcomes that shaped them.

## Why this exists

Most tools preserve outputs. Few preserve the living path of judgment: what was considered, why something was chosen, what assumptions were made, and whether the choice held up over time.

Steward Commons treats reasoning as a public good. It gives projects a shared structure for decision histories that can be reviewed, forked, audited, improved, and extended.

## Core idea

Every project becomes a reasoning graph:

- Projects contain decisions.
- Decisions compare proposals.
- Proposals are supported or challenged by evidence.
- Decisions create outcomes.
- Outcomes trigger reflection.
- Reflection improves future decisions.

## Project layers

1. **The Steward Project** — the broader vision for long-term knowledge stewardship.
2. **Steward Commons** — the open protocol and shared standard.
3. **Reference implementations** — software built on top of the protocol.

## MVP scope

The first version should do five things well:

1. Create a project.
2. Record a decision.
3. Add competing proposals.
4. Attach evidence and objections.
5. Revisit the decision later with outcomes and reflections.

## Repository structure

```text
steward-commons/
  README.md
  LICENSE
  CONTRIBUTING.md
  CODE_OF_CONDUCT.md
  CHANGELOG.md
  ROADMAP.md
  GOVERNANCE.md
  docs/
  schemas/
  examples/
  reference/
  research/
  assets/
```

## Status

Draft v0.1. This is an early foundation for an open standard.
