# release-evolution: evolve a data-versioning tool across a feature release

A solver receives a real Python source tree pinned at the commit that closed a patch release,
plus the full prose specification of the next feature release. It must make the release's
behaviour true of the tree without regressing the suite that already passes.

| Property | Value |
| --- | --- |
| Archetype | release-evolution |
| Delivery format | Harbor 0.25.0 |
| Language | Python |
| Network | agent: host-bridge allowlist; verifier: host-bridge allowlist for the judge |
| Required-to-pass nodes | 111 |
| Must-keep-passing nodes | 2880 |
| Measuring groups | 15 across 14 touched test files, the largest carrying 32 of 111 |
| Resolution | binary: all required pass and nothing regresses |
| Fix rate | repaired fraction of the required set, zeroed by any regression |

## Why it resists a shortcut

The specification names the outcome, never the change list. No failing test is handed over, so
localisation is part of the work: the solver derives which of 53 package files must move from
prose alone. The must-keep-passing set is twenty-six times the size of the required set, so
passing the required behaviour by special-casing its inputs breaks something that already worked
and scores zero on both measures.

The required set is spread across fifteen equally weighted measuring groups, the largest holding
32 of 111 nodes, or 29 percent. A solver that solves one objective well therefore cannot reach
most of the reward, which is the property a single dominant group would destroy. The groups
outnumber the 14 touched test files because `tests/func/test_data_cloud` contributes two, one at
module level and one for its `TestRemote` class.

Both `tests/unit` and `tests/func` are graded. The release span touches four unit and ten
functional test files, so grading unit alone would measure four of those fourteen files, four of
the fifteen graded groups, and leave most of the release unobserved.

## Layout

| Path | Class | Contents |
| --- | --- | --- |
| `instruction.md` | agent-visible | the release specification |
| `environment/` | agent-visible | container recipe; fetches the base revision, then destroys its git metadata |
| `tests/` | verifier-only | the authoritative unit and functional trees, the predeclared node-id sets, and the grader |
| `solution/` | oracle-only | the reference patch, its rationale, the judge driver, and provenance |

The environment keeps no git history, no tags and no remote, so the upstream answer is not
recoverable from inside the task even if a network appeared.

## The test-infrastructure vector, and how it closes

Seventeen graded test files import fixtures from `dvc/testing/`, which is part of the release's
own package change. Shipping those three files to the solver would let it edit fixtures instead of
implementing the release. Five options were measured and four of them zero the oracle:

| option | measured result |
| --- | --- |
| bound the reference patch, no restore | two must-keep nodes regress; oracle **not** 1.0 |
| restore `dvc/testing` from the base revision | undoes the oracle's own three files |
| exclude it from the artifacts allowlist | the oracle's edits never reach the verifier |
| extend the test-edit digest over it | the oracle trips its own red line |
| **restore from the target revision** | **111 of 111, 2880 of 2880, oracle 1.0** |

The verifier therefore restores `dvc/testing` from the target revision in `test.sh` step 2, before
any test runs, exactly as it already owns the test trees. Two must-keep nodes that inherit from
`dvc/testing/remote_tests.py` are recovered by that restore, which is why bounding alone fails.
The cost is three of fifty-three files given rather than derived.

## Determinism

`pathspec` is pinned to `0.12.1` in both hash-locked manifests. `dvc/ignore.py` imports
`_DIR_MARK` from `pathspec.patterns.gitwildmatch` at module scope, and later `pathspec` releases
dropped that name: resolving it freely yields 649 collection errors against this revision, and
pinning it yields zero. The target revision additionally bounds `pytest-rerunfailures` below
`16.0`, which the manifests honour at `15.1`.

One node, `tests.func.test_checkout::test_checkout_stats[False-expected_lines1]`, is excluded from
both sets. It reported failed, failed, then passed across three baseline runs on the pinned image,
and an unstable node cannot carry a regression claim.

## Harness contract

**Target:** stock Harbor `0.25.0` with Harbor Reward Kit. `rewardkit` is the verifier. This bundle
does **not** target a vendored or patched Harbor, and it does not carry a `levi_verifier` kit — a
consumer preflighting a five-artifact sealed-kit contract will refuse it, and that refusal is a
contract mismatch rather than a defect in either side.

Run and gate it with:

```sh
rewardkit /tests --workspace /app --output /logs/verifier/reward.json   # inside the verifier
harbor lint <bundle>
```

**The judged channel needs a credential at invocation.** `tests/judge.toml` ships inside the
verifier at `/tests`, where `forge/outputs.md` item 34 requires it, and `rewardkit` scores it in
the same invocation as the deterministic criteria. Harbor resolves the key from the runner's own
environment, so nothing is sealed:

```
harbor run <bundle> --ve 'ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}'
```

**This flag is required, not optional.** `tests/judge.toml` sits in `/tests` because
`forge/outputs.md` item 34 requires it there, so Reward Kit scores both channels in one
invocation and they share a single `asyncio.TaskGroup` with no exception guard. A judge that
cannot reach its model raises, the group is cancelled, and `rewardkit` writes **no reward at
all** — the deterministic score is lost with it. This is a property of `harbor-rewardkit`
0.2.4, not a choice in this bundle. The verifier's `allowed_hosts`
covers two private host-gateway ranges, so a judge model behind a local bridge is reachable and
a hosted endpoint is not — widen `allowed_hosts` if your judge model is hosted.

**Known `harbor lint` warnings, accepted:** `instruction_following_state`, `interface_spec`,
`span_provenance` and `upstream_provenance` are reported as unknown top-level fields. Harbor
ignores unknown top-level keys, so they are inert. They are kept at top level because they are
authoring contract, not Harbor configuration, and are recorded here so nobody has to re-derive
that the warnings are harmless.

**Agent: the agent phase reaches the host model bridge and nothing else.** Baking the agent CLI
into the environment image is still the supported path, but it is an install-time convenience and
never the reason the task is closed:

| plane | network | uid | setuid |
| --- | --- | --- | --- |
| environment | `no-network` | `10001:10001` | cleared |
| agent | `allowlist`: `192.168.65.0/24`, `172.16.0.0/12` | `10001:10001` | cleared |
| verifier | `allowlist`: `192.168.65.0/24`, `172.16.0.0/12` | `10002:10002` | cleared |

`RL-NO-NETWORK` is one of the task's red lines and it is **scoped to the verifier**, which is the
phase where outside influence would corrupt a grade. The verifier reaches no network at all, so
the deterministic reward is computed from the bundle's own bytes; the judged reward adds one model's reading of them, reached over the verifier's host-bridge allowlist.

The agent phase cannot be closed the same way. An agent is driven by a model, and it resolves that
model's endpoint at trial time; `no-network` denies that exactly as it denies an installer, which
makes the task unrunnable by any solver rather than hard for one. The allowlist therefore carries
only the host-gateway ranges a local model bridge listens on. The container is given no provider
credential, and the ranges are private, so the public internet stays unreachable: the upstream
answer cannot be fetched even though a route to a model exists.

Pre-baking the CLI removes the install-time network need and leaves the run-time one untouched.
An earlier revision of this file claimed the bundle was agent-agnostic *because* the agent was
pre-baked; that claim is withdrawn as unsound, and `environment/` still carries no agent, so a
consumer baking its own in at build time remains the supported route.

## The judged channel

`tests/judge.toml` carries nine judged criteria and is the sole rubric carrier;
`trinity/tools/judge_layout.py` refuses a legacy `rubrics.json` layout, so no second file exists.
It is **re-admitted** by `tests/.dockerignore` so Reward Kit scores it inside the verifier. The
consequence is load-bearing: Reward Kit turns any `*.toml` under `tests/` carrying a
`[[criterion]]` table into a live LLM judge, runs it in the same `asyncio.TaskGroup` as the
deterministic criteria with no exception guard, and writes **no reward at all** if that judge
cannot reach its model. The credential is therefore required, not optional.

Its consumer is `solution/judge/`, which runs at the grading stage rather than inside the
verifier as the author's own check, and without `JUDGE_MODEL` and `JUDGE_API_KEY` it reports
`state: skipped` and exits 0. The **delivered** judged channel is the Reward Kit judge inside the
verifier, pinned to `openai/gpt-5.6-sol` rather than left to a library default that could move a
client's scores between releases.

It carries 10 percent of the reward and the deterministic channel decides the other 90, but its
contribution is **thresholded rather than averaged in continuously**: `tests/judge.toml` sets
`aggregation = "threshold"` at Reward Kit's default bar of `0.5`, so the rubric score becomes
`1.0` or `0.0` before it reaches the mean. A judge returns an opinion that moves run to run on
identical bytes — the reference fix has scored between `0.7419` and `0.8065`, an empty diff
between `0.0323` and `0.2903` — so a continuous contribution would make the reward
irreproducible and put the reference fix permanently below `1.0`. Thresholded, the reference
fix scores exactly `1.0` and an empty submission exactly `0.0`, measured over three consecutive
oracle runs, while residue that drops the rubric under the bar still forfeits the full 10
percent.

The channel is weighted rather than recorded-only because the deterministic channel provably
cannot see slop: a diff that is the oracle plus dead code, plus a stray `print`, plus a left-in
`breakpoint()` scores exactly 1.0 against the node sets, because every graded node still passes.
`Q4` is the criterion that charges for exactly that residue, at weight 1 of the judged set. An
earlier revision of this file recorded `alpha = 0`, which was true while the rubric was
uncalibrated and is now false; the operator has since run the agreement pass. `alpha` lives in
`solution/judge/compose.py` and nowhere else, and `SCORE_ALPHA` overrides it at run time.
