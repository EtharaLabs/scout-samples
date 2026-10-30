# VERDICT-dvc-release-evolution.md

## Scope

One bundle, one rollout:

| uuid | task | shape |
|---|---|---|
| `17d39867-3881-5faa-9b39-6108263c4ed6` | `scout/release-evolution-dvc`, `iterative/dvc` 3.62.0 → 3.63.0, base `225bfa6a` target `75c5d17d` | python, 111 required / 2880 must-keep / 15 groups, 1 model × 1 run |

Name-list digest `621717f97faa222a28b4a6fe6358c5e1895692498c5615421eea8208361613c7` over 336 files, content digest `a0c45fdd411fa8acce820cff58292474995a46b3d63b052ffa8186980fc52529`. The rollout is `claude-opus-5-5` at effort `max`, run 1, under claude-code 2.1.312: 528 turns, 222 tool calls, 27 suite runs, 75.9 minutes, reward `0.4372`.

Findings carry an attribution tag: **[task]** the bundle as authored, **[pack]** what was packaged into it, **[harness]** the run/score/record pipeline, **[spec]** the binding inputs, **[agent]** the model under test.

## Executive summary

🟡 **HOLD:PILOT_REQUIRED.** The bundle is sound and the rollout is a genuine measurement. The reward reproduces to four decimals from the committed scorer inputs, every recorded failure is a real logic error raised by the solver's own code, zero must-keep regressions are confirmed independently of the scorer, the test tree was not touched, and the trajectory carries no retrieval attempt. The oracle scores 1.0 and the empty submission 0.0 on the sealed verifier image. What holds the bundle is what has not yet been done around it: one rollout is an observation, not a pilot, so no pass@k and no difficulty tier can be stated; the source attestation is unsigned and the screening atoms are two short of six, both of which the provenance carrier itself caps at `HOLD:PILOT_REQUIRED`; and the judged channel, which carries ten percent of the reward, cannot be reproduced from the bundle and judged from evidence that was wider than the solver's own work.

## Disposition

| | |
|---|---|
| **Bundle** | HOLD |

The substate is the one the bundle's own provenance carrier records, twice, and names the cause precisely: the pilot and its second audit have not run.

## Findings

- ✅ **[task] The reward arithmetic reproduces from committed bytes.** Depth `0.392361`, breadth `5/15 = 0.333333`, outcome `0.70×0.392361 + 0.30×0.333333 = 0.374653`, regression factor `1 − 0/29 = 1.0`, gates `1.0`, deterministic `0.3747`, composed `0.9×0.374653 + 0.1×1.0 = 0.4372`. The 56 resolved nodes are `1+1+19+7+2+23+3` across the seven groups with any pass. `result.json`, `grading.json`, `reward.json` and `final_score.md` all agree.
- ✅ **[task] The graded sets are internally consistent.** The required set equals the union of group nodes exactly; required and must-keep are disjoint; the fifteen weights sum to 1.0; the baseline manifest records every required node as failed (91) or absent (20) at base and every must-keep node as passed; the one excluded node is a three-run flapper and sits in neither set.
- ✅ **[harness] The rollout reconciles against its own pytest log.** 58 `FAILED` lines: 54 on required nodes, four ungraded and matching the oracle-failure note in `gate.json`. No must-keep node appears, so `must_keep_regressed = 0` is confirmed independently of the scorer. Failure kinds are 35 `AssertionError`, 16 `TypeError`, 5 `AttributeError`, 2 `CalledProcessError`, with zero collection errors. `tests_modified=0`, `added_test_files=2`, and the agent patch names no test path.
- ✅ **[agent] No retrieval, and the red lines held.** The only web-tool strings in the stream are the disallow flag. Every `github.com` string is a fixture URL read from the test tree. All 24 git-bearing commands are `git init` in scratch directories for the agent's own experiments. No `curl`, `wget` or `pip install` was issued.
- ✅ **[task] Sanitization and image hygiene hold.** The instruction carries no link, version string, pull-request number or sha against a release note that carries 14 pull-request links. Both images fetch one commit and destroy `.git` in the same layer, run multi-stage, create fixed non-root uids, clear setuid bits, hash-lock requirements and pin a dated Debian snapshot. The agent image reports the base release, never the target.
- ✅ **[task] The scorer fails closed where it must.** An unreadable report fails every criterion; a modified test tree gates the reward to zero; a regression count at or above 29 gates to zero; the graded tree is a verifier-owned copy with explicit restore assertions that refuse to grade on a nested or missing tree.
- ✅ **[harness] The void first grade was disclosed rather than hidden.** A directory copy nested the agent tree, the base tree was graded, and `result.json` records the void grade and the corrected re-run in plain terms.
- ⚠️ **[pack] Provenance is unsigned and screening is two atoms short.** `source_attestation` is `unsigned`: the two commit shas verify against the public repository, but no signed envelope binds them to this bundle. Four of six screening atoms carry a digest; near-duplicate screening waits on a calibrated root that is not yet published, and the freeze-holdout atom does not apply to a span that predates the run. The binding block is absent because no trust root publishes a signer to verify against. Each of these is recorded in the carrier rather than worked around.
- ⚠️ **[spec] One rollout, no pilot, no tier.** The bundle ships one run of one model. The cohort table in `final_score.md` cites two further runs that are not in the bundle, so those rows are uncorroborated. No qualification spec publishes `k` or a model set, so no pass@k is computable and no difficulty tier is assignable.
- ⚠️ **[harness] The judged channel is not reproducible from the bundle.** The judge model is reached through an author-side bridge that ships nowhere in the bundle, outside the verifier's declared host allowlist. The judge receives only the final diff, never the specification, yet criterion `Q2` asks whether each hunk is required by the specification. In this run `Q2` fired on ignore matching, batched stage dumping, commit refactoring, rename reporting, diff cache handling, YAML error paths and remote completion, which are objectives 7, 10, 6, 11, 13, 14 and 8 of the instruction. The raw rubric `0.9032` still cleared the `0.5` bar, so the reward did not move.
- ⚠️ **[harness] The judge's evidence is wider than the solver's work.** The final diff lists 32 files; the agent patch lists 28. The four extra are a generated version file produced at install time and the three `dvc/testing` files the verifier restores from the target revision before grading. The judge saw reference bytes as solver output.
- ⛔ **[harness] One of 111 node verdicts is not derivable from shipped artifacts.** `tests.unit.command.test_help::test_help[data]` is recorded unresolved, yet no `FAILED` or `ERROR` line names it. The suite ran quietly, which lists no passes, and the junit report is not shipped. Its id is built from the CLI parser's registered commands, which the solver edits. 54 of the 55 unresolved nodes are confirmed failures; this is the 55th.
- ⚠️ **[pack] Prose and bytes disagree on a few counts.** `solve.sh` says 107 required nodes against 111 in `sets.json`; the grounding's revalidation note says 2877 passed and 87 failed against its own observed 2880 and 96; the README and `TRUTH.md` say a regression zeroes the score while the scorer applies a graduated `1 − R/29`; one scorer comment cites a sibling bundle's suite size. The bytes are right and the prose is behind.
- ⚠️ **[task] Statement wording.** The instruction says the environment has no network while the agent plane runs an allowlist for its model bridge. `TRUTH.md` names four feasibility controls; only the no-op control is evidenced, in `gate.json`.
- ⚠️ **[pack] Objective coverage is declared unestablished.** Fourteen objectives, fifteen groups, and no mapping, by the author's own record. Which objectives no graded node measures is unknown.
- ⚠️ **[agent] The closing summary overclaims.** The agent's final message states all fourteen objectives are implemented; the grade is five of fifteen groups complete. Nothing in the rubric scores the claim, and `instruction_following_state` is declared `deferred`.

## HOLD

1. ⚠️ **Pilot required.** One rollout, no `k`, no model set. The substate is carried in the provenance carrier and stands until the pilot and its second audit run.
2. ⚠️ **No trust root.** No external signature root, no detached signature, no canary issued. `SHIP` is unreachable until one exists.
3. ⚠️ **Screening roots absent.** Exclusion list, freeze-date table and near-duplicate index are not recorded, so contamination screening cannot complete.

## Known defects in this run

1. ⚠️ No image was rebuilt and no oracle, no-op or judge half was replayed. `oracle 1.0` and `nop 0.0` are accepted from `gate.json` with their arithmetic checked, not re-executed.
2. ⚠️ `recompute.py --check` was not run for want of PyYAML, so identical regeneration of `TRUTH.md`, `sets.json` and the scorer from the grounding is unverified.

## Escalations

- `run-the-pilot` **[spec]** — publish `k` and the model set, run the pilot, then re-audit the same digest.
- `give-the-judge-agent-authored-bytes-and-the-spec` **[harness]** — strip the generated version file and the restored `dvc/testing` files from the judged diff, and supply the specification `Q2` grades against.
- `ship-the-junit-report` **[harness]** — one required node's outcome is unrecoverable without it.
- `reconcile-the-counts` **[pack]** — 107/111, 2877/2880, 87/96, and the regression rule wording.
- `ship-or-drop-the-cohort-table` **[pack]** — two rows cite rollouts the bundle does not carry.
- `record-screening-roots-and-a-trust-root` **[spec]** — prerequisite to any `SHIP`.

## How to reproduce

Stdlib-only recomputation over the bundle's committed bytes and the rollout's shipped logs:

```
# sets.json, group_map.json, baseline_manifest.json: equality, disjointness, weights, base status
# verifier/group-completion.json: depth, breadth, outcome, composed
# verifier/test-stdout.txt: FAILED lines attributed to required, must-keep and ungraded nodes per group
# artifacts/final.diff versus artifacts/agent.patch: file lists
# agent/stream.jsonl: tool names, git and network commands
```

## Flag legend

✅ pass. ⚠️ coverage gap, stale claim, or unverified claim. ⛔ critical or blocking defect.
🟢 SHIP. 🟡 HOLD. 🔴 BLOCK. Attribution: **[task]** authored bundle, **[pack]** packaging, **[harness]** run/score/record pipeline, **[spec]** binding input, **[agent]** model under test. Keep YAML and evidence emoji-free.
