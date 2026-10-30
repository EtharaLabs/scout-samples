# Final score

Reward **0.4372** on the sealed verifier `sha256:68b249138417a113`, the same image
`solution/gate.json` recorded when it measured the oracle at 1.0 and the no-op at 0.0.

| channel | weight | score |
|---|---|---|
| deterministic `test_output` | 0.9 | 0.3747 |
| judged rubric | 0.1 | 1.0 (raw 0.9032, thresholded at 0.5) |
| composed | | **0.4372** |

## Graded sets

- required to pass: **56 of 111** resolved
- must keep passing: **2880**, regressed **0**
- pre-existing tests modified: **0**; test files added: 2 (permitted by RL-NO-TEST-EDIT and discarded before scoring)
- collection errors: **0**
- failure kinds: AssertionError 35, AttributeError 5, TypeError 16, subprocess.CalledProcessError 2

Every failure is a genuine logic error raised by the solver's own code. No module failed to import
and no failure is an environment or harness artifact.

## Run

`claude-opus-5-5` at effort `max` under claude-code 2.1.312: 528 turns, 222 tool calls,
27 suite runs, 75.9 minutes, $27.44, result `success`.
Web tools were withheld, no CLAUDE.md was in scope, and the tree was a fresh copy of the sealed
environment image with 0 files differing at launch.

## Cohort position

| model | effort | required | deterministic | reward |
|---|---|---|---|---|
| claude-opus-5 | default | 27/111 | 0.2811 | 0.3530 |
| claude-opus-5-5 | xhigh | 58/111 | 0.4428 | 0.4985 |
| claude-opus-5-5 | max | 56/111 | 0.3747 | 0.4372 |

Raising effort from xhigh to max moved nothing: 56 required against 58, inside run-to-run noise.
Three independent rollouts land between 0.35 and 0.50, so the bundle sits near its half-credit
target rather than at a ceiling or a floor.

## How the deterministic score is composed

The deterministic channel is not a raw node fraction. `test_output.py` composes
`gates * outcome * regression_factor`, where `outcome = 0.70*depth + 0.30*breadth` over the fifteen
feature groups of `group_map.json`, each weighted equally at 1/15. Grouping is per measuring test
file by design, so one group holding dozens of parametrisations of a single helper cannot outweigh
several whole features.

| group | required nodes passed | completion | |
|---|---|---|---|
| `tests.func.test_commit` | 1/1 | 100.0% | complete |
| `tests.func.test_diff` | 1/1 | 100.0% | complete |
| `tests.func.test_repo_index` | 19/19 | 100.0% | complete |
| `tests.unit.command.test_data_status` | 7/7 | 100.0% | complete |
| `tests.unit.test_dvcfile` | 2/2 | 100.0% | complete |
| `tests.func.test_checkout` | 23/32 | 71.9% |  |
| `tests.func.test_data_status` | 3/18 | 16.7% |  |
| `tests.func.test_check_ignore` | 0/1 | 0.0% |  |
| `tests.func.test_data_cloud` | 0/22 | 0.0% |  |
| `tests.func.test_data_cloud.TestRemote` | 0/2 | 0.0% |  |
| `tests.func.test_run_cache` | 0/1 | 0.0% |  |
| `tests.func.test_virtual_directory` | 0/1 | 0.0% |  |
| `tests.func.utils.test_strict_yaml` | 0/1 | 0.0% |  |
| `tests.unit.command.test_help` | 0/1 | 0.0% |  |
| `tests.unit.test_ignore` | 0/2 | 0.0% |  |

- depth, weighted completion across groups: **0.392361**
- breadth, weight of groups finished outright: **0.333333** (5 of 15)
- outcome: 0.70 x 0.392361 + 0.30 x 0.333333 = **0.374653**
- regression factor: 1 - 0/29 = **1.0**
- gates: **1.0**, no gate reason recorded
- composed: **0.3747**, the `deterministic` value in `result.json`

This is why 56 of 111 nodes does not read as 0.50. The solver finished five groups outright and
never reached seven, so breadth carries only a third of its weight. The per-group table is the
diagnosable signal: it names which features landed and which were never attempted.

## Void first grade

The first grade of this rollout is not recorded as a score. `docker cp` of a directory onto an
existing destination nests it, so the solver tree landed at `/app/dvc/dvc` while `/app/dvc` stayed
pristine base. That graded base code and returned 0 of 111 required, 2880 of 2880 must-keep, one
`ImportError` collection error for `index_from_targets`, and reward 0.1, which is the no-op control
score. The transfer was corrected to clear the destination first and the grade re-run. This record
is that second, valid grade.
