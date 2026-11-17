<p align="center"><img src="images/hero.svg" alt="scout" width="720"></p>

# scout: samples

<p align="center"><b>Five sample tasks from scout, a Harbor benchmark that measures whether an autonomous agent can carry a pinned source tree across a feature release boundary from the release specification alone.</b></p>

<p align="center"><a href="#summary"><img src="https://img.shields.io/badge/tasks-5-845EF7" alt="tasks: 5"></a> <a href="#summary"><img src="https://img.shields.io/badge/harbor_schema-1.4-845EF7" alt="harbor schema: 1.4"></a> <a href="#trials"><img src="https://img.shields.io/badge/mean_reward-0.4731-845EF7" alt="mean reward: 0.4731"></a></p>

<p align="center"><sub><a href="#abstract">Abstract</a> | <a href="#summary">Summary</a> | <a href="#tasks">Tasks</a> | <a href="#trials">Trials</a> | <a href="#coverage">Coverage</a> | <a href="#dataset-structure">Dataset structure</a> | <a href="#reproduction">Reproduction</a> | <a href="#cite">Cite</a> | <a href="#contact">Contact</a></sub></p>

## Abstract

scout is a benchmark of long-horizon agentic tasks in [Harbor](https://github.com/laude-institute/harbor) format. Each task pins a real upstream open source project at a base revision and asks the agent to evolve it across a feature release boundary, working from the release specification alone.

The published answer is withheld rather than hidden in plain sight: pull request numbers, tags and diffs are kept out of the task, and the release prose is restated positionally, because each of those is a retrieval handle to the upstream fix. Every task runs in an offline container and carries a reference solution, a deterministic test suite, and an LLM-judged rubric. The reward is continuous from 0 to 1, a weighted mean of the two channels.

This repository holds the five-task sample. All five are Python, and they span three upstream projects: networkx, celery, and sympy. The surfaces under evolution include maximum flow and centrality, core graph views and generators, community and bipartite analysis, the Celery result backends and worker pipeline, and the SymPy expression core, functions, number theory and printers.

## Summary

| Property | Value |
| --- | --- |
| Tasks | 5 |
| Domain | Software engineering (long-horizon release evolution) |
| Languages | Python |
| Upstream projects | networkx (3 tasks), celery, sympy |
| Format | Harbor task, schema 1.4 |
| Platforms | linux/amd64, linux/arm64 |
| Resources per task | 4 CPUs, 8192 MB |
| Reward | Weighted mean: deterministic tests 0.9, LLM judge 0.1 |
| Agent | Claude Code 2.1.316 with `claude-opus-5-5`, reasoning effort `max` |
| Judge | `openai/gpt-5.6-sol`, reasoning effort `high`, 3 samples per criterion |
| Runs per task | 1 |
| Mean reward | 0.4731 |
| Mean deterministic score | 0.4195 |
| Mean judged score | 0.9557 |

## Tasks

| Task | Project | Language | Objective |
| --- | --- | --- | --- |
| [`24f302c6`](24f302c6-926a-50bb-a40f-4748a8cf11dd/) | [networkx](https://github.com/networkx/networkx) | Python | Evolve maximum flow, connectivity cuts and centrality across a feature release boundary, from the release specification alone. |
| [`674a609d`](674a609d-76d2-5c2d-be33-d26393d4c8c2/) | [celery](https://github.com/celery/celery) | Python | Evolve the result backends, the worker consumer pipeline and the messaging surface across a feature release boundary. |
| [`7fe493f6`](7fe493f6-56d9-568d-bc25-a0c7d28e4b7d/) | [networkx](https://github.com/networkx/networkx) | Python | Evolve the core graph views, serialisation formats, spectral matrices and generators across a feature release boundary. |
| [`b8fff9ab`](b8fff9ab-67b1-5e09-8c9c-679b571afc25/) | [sympy](https://github.com/sympy/sympy) | Python | Evolve the expression core, the function hierarchy, the number-theory surface and the printers across a feature release boundary. |
| [`b9876d0d`](b9876d0d-3754-5ed2-8e50-e40688f31fca/) | [networkx](https://github.com/networkx/networkx) | Python | Evolve community structure and bipartite analysis across a feature release boundary, from the release specification alone. |

## Trials

Each task was run once with Claude Code 2.1.316 driving `claude-opus-5-5` at reasoning effort `max`, and scored by the task's own verifier. Trials are stored in each task's `trials/opus-5.5/`.

| Task | Reward | Deterministic<br/>(weight 0.9) | Judged<br/>(weight 0.1) | Judged<br/>criteria | Agent time | Cost (USD) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| [`24f302c6-926a-50bb-a40f-4748a8cf11dd`](24f302c6-926a-50bb-a40f-4748a8cf11dd/trials/opus-5.5/) | 0.3465 | 0.2739 | 1.0000 | 12 / 12 | 51m 13s | 14.90 |
| [`674a609d-76d2-5c2d-be33-d26393d4c8c2`](674a609d-76d2-5c2d-be33-d26393d4c8c2/trials/opus-5.5/) | 0.6275 | 0.6027 | 0.8500 | 10 / 12 | 54m 13s | 24.55 |
| [`7fe493f6-56d9-568d-bc25-a0c7d28e4b7d`](7fe493f6-56d9-568d-bc25-a0c7d28e4b7d/trials/opus-5.5/) | 0.4293 | 0.3659 | 1.0000 | 12 / 12 | 1h 03m | 22.82 |
| [`b8fff9ab-67b1-5e09-8c9c-679b571afc25`](b8fff9ab-67b1-5e09-8c9c-679b571afc25/trials/opus-5.5/) | 0.3496 | 0.2853 | 0.9286 | 11 / 12 | 2h 33m | 65.44 |
| [`b9876d0d-3754-5ed2-8e50-e40688f31fca`](b9876d0d-3754-5ed2-8e50-e40688f31fca/trials/opus-5.5/) | 0.6128 | 0.5697 | 1.0000 | 12 / 12 | 46m 41s | 12.73 |
| **mean** | **0.4731** | **0.4195** | **0.9557** | **57 / 60** | **1h 13m** | **28.09** |

The reward weights are listed in the [Summary](#summary) table. The judged column is scored by `openai/gpt-5.6-sol` at reasoning effort `high`, sampled 3 times per criterion.

Each trial folder is Harbor's trial output:

| Path | Contents |
| --- | --- |
| `config.json`, `lock.json` | Trial configuration and resolved run settings |
| `result.json` | Agent, model, token usage, cost, timings, and verifier reward |
| `agent/` | Agent trajectory (`trajectory.json`), Claude Code session transcript (`sessions/`), and agent output (`claude-code.txt`) |
| `verifier/` | `reward.json`, `reward-details.json`, `ctrf.json`, `junit.xml`, `final.diff`, and test output |
| `artifacts/` | Files the agent produced, collected from the paths declared in `task.toml` |

## Coverage

Every task carries the same six keywords, so the span of the set is better read from its scale. Each task enumerates the objectives its release specification states, and the deterministic channel scores those objectives in weighted groups while holding the rest of the suite as a regression guard.

| Task | Upstream | Enumerated<br/>objectives | Test<br/>groups | Required<br/>to pass | Regression<br/>guard | Suite |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| [`24f302c6`](24f302c6-926a-50bb-a40f-4748a8cf11dd/) | networkx | 6 | 10 | 81 | 7855 | 9451 |
| [`674a609d`](674a609d-76d2-5c2d-be33-d26393d4c8c2/) | celery | 19 | 20 | 64 | 3144 | 3403 |
| [`7fe493f6`](7fe493f6-56d9-568d-bc25-a0c7d28e4b7d/) | networkx | 7 | 42 | 91 | 7855 | 9423 |
| [`b8fff9ab`](b8fff9ab-67b1-5e09-8c9c-679b571afc25/) | sympy | 14 | 31 | 52 | 4946 | 5388 |
| [`b9876d0d`](b9876d0d-3754-5ed2-8e50-e40688f31fca/) | networkx | 7 | 12 | 162 | 7855 | 9487 |
| **total** | | **53** | **115** | **450** | | |

Alongside the deterministic channel, every task is scored on 12 judged criteria, for 60 across the set.

## Dataset structure

Each task is one Harbor task in a directory named by its uuid.

| Task | Keywords |
| --- | --- |
| [`24f302c6-926a-50bb-a40f-4748a8cf11dd`](24f302c6-926a-50bb-a40f-4748a8cf11dd/) | horizon-length, patch-scope, python, regression-surface, release-evolution, specification-length |
| [`674a609d-76d2-5c2d-be33-d26393d4c8c2`](674a609d-76d2-5c2d-be33-d26393d4c8c2/) | horizon-length, patch-scope, python, regression-surface, release-evolution, specification-length |
| [`7fe493f6-56d9-568d-bc25-a0c7d28e4b7d`](7fe493f6-56d9-568d-bc25-a0c7d28e4b7d/) | horizon-length, patch-scope, python, regression-surface, release-evolution, specification-length |
| [`b8fff9ab-67b1-5e09-8c9c-679b571afc25`](b8fff9ab-67b1-5e09-8c9c-679b571afc25/) | horizon-length, patch-scope, python, regression-surface, release-evolution, specification-length |
| [`b9876d0d-3754-5ed2-8e50-e40688f31fca`](b9876d0d-3754-5ed2-8e50-e40688f31fca/) | horizon-length, patch-scope, python, regression-surface, release-evolution, specification-length |

```
<uuid>/
├── task.toml         runner manifest
├── instruction.md    objective the agent reads
├── environment/      sandbox image, pinned at the base revision
├── tests/            verifier, hidden from the agent
├── solution/         reference solution
└── trials/
    └── opus-5.5/     claude-opus-5-5 at reasoning effort max
        ├── config.json, lock.json, result.json
        ├── agent/
        ├── artifacts/
        └── verifier/
```

## Reproduction

Each task directory is a complete Harbor task: `task.toml` is the runner manifest, `instruction.md` the objective, `environment/` the sandbox image pinned at the base revision, `tests/` the verifier, and `solution/` the reference solution. The trials above were produced with:

```bash
harbor run -p <uuid> -a claude-code -m claude-opus-5-5
```

The verifier's LLM-judged rubric reads `OPENAI_API_KEY` and `OPENAI_BASE_URL` to reach `openai/gpt-5.6-sol`.

## Cite

```bibtex
@misc{scout2026,
  title        = {scout: measured terminal tasks for long-horizon software evolution},
  author       = {{Ethara.AI}},
  year         = {2026},
  howpublished = {\url{https://github.com/Ethara-Ai}},
  note         = {Method published; no performance claim made at this revision.}
}
```

## Contact

scout is built by [Ethara.AI](https://github.com/Ethara-Ai). For questions about the benchmark or dataset, contact [research@ethara.ai](mailto:research@ethara.ai).

Copyright (c) 2026 Green Rider Technology LLP (Ethara AI). All rights reserved.
