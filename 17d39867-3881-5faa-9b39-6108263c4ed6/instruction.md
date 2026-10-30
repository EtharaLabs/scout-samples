# Release specification

You are working in the source tree of `dvc`, a data and ML experiment versioning tool, checked
out at the commit that closed the previous patch release. Your job is to evolve this tree so that
it implements the **next feature release** of the project, described in full below.

This is the complete release specification. It is the only description of the work you get. No
issue text, no failing-test name, and no file list is supplied: deriving the change list, locating
every file that must move, and coordinating the edits across the tree is the task.

## What is required

Implement the behaviour described by every objective below. The project's own test suite is the
definition of done:

- Behaviour named in this specification must become true of this tree.
- Everything the suite already verifies must keep working. A change that makes a new behaviour
  pass while breaking existing behaviour loses reward in proportion to the damage, and enough
  breakage scores zero outright.

Credit is awarded per feature, not per test. Finishing one objective completely is worth more than
touching several partially, and an objective measured by many near-identical cases is worth no
more than an objective measured by one.

## Paths the verifier owns

The following are the verifier's and are restored from pristine bytes before a single test runs.
Modifying or deleting any pre-existing file under them is rejected outright and the whole session
scores zero:

- `tests/**` — every test file that already exists in this tree.
- `dvc/testing/**` — the test-support package the suite imports. It ships inside the package tree
  rather than the test tree, so it is called out explicitly: edits to it are discarded and cannot
  move your score.

**Adding a new test file under `tests/` is permitted and expected.** Writing tests for behaviour
you implement is good practice and is not penalised. Added files are discarded before grading, so
they neither help nor harm your score. Only modification or deletion of a file that already exists
is the violation.

## Working instructions

- Enumerate the objectives below and count them before you begin. Every numbered objective is
  part of the work; work through them deliberately rather than stopping at the first that yields a
  passing test.
- You **must not** modify, delete, skip, or `xfail` any pre-existing test, helper, fixture, fake,
  stub, or mock.
- Do not clone, fetch, or pull. Do not read git history, tags, stashes, branches, or remotes, and
  do not attempt to retrieve the upstream release, its tag, its diff, its pull requests, or its
  commits from any source. **A solution derived from a retrieved reference is invalid and will not
  be scored.** Derive the change from this specification alone.
- Do not install or download any package. The environment has no network and needs none.
- Prefer the smallest change that makes the behaviour true. Unrelated churn, dead code, and debug
  residue count against the submission.
- Follow the conventions already present in the file you are editing.

## Objectives

### Objective 1

In `dvc status --cloud`, `target` now supports specifying a path to a dataset. Previously,
specifying a directory as the target caused DVC to search for `.dvc` and `dvc.yaml` files inside
it, from which the datasets specified in those files were then checked for cloud/remote status,
rather than considering the directory itself as a dataset.

### Objective 2

Add a `--remote` option to `dvc data status --not-in-remote`, for checking files against a
specified remote instead of the default one.

### Objective 3

`exp show` accepts multiple `--keep` and `--drop` arguments.

### Objective 4

`dvc init` supports initializing a DVC repository in an arbitrary directory.

### Objective 5

`checkout` and `pull` report a granular summary of changes.

### Objective 6

`data status` detects file moves and renames by default.

### Objective 7

`dvcignore`: share the implementation between `check-ignore` and the internal API DVC itself uses,
and improve support for unignore rules such as `!data/**`.

### Objective 8

Support completing a remote name in zsh and bash.

### Objective 9

Load only a stage or `.dvc` file when the target is an address to that particular stage.

### Objective 10

Batch dump stages in `commit`, and do not re-read on save from the workspace.

### Objective 11

Do not show missing cache entries in the `dvc diff` result.

### Objective 12

Handle a missing DVC repository at Git `HEAD` in `dvc data status`.

### Objective 13

Show an entry under "Not in cache" when a directory entry is missing in `dvc diff`.

### Objective 14

Fix the `dvc.yaml` filepath in the error message when reading from git revisions.

## Public interface

These are the symbols the graded tests reach for the objectives whose contract prose cannot carry
them, with the signature each one carries at the release boundary. They are given rather than left
to be inferred: a change that implements the right behaviour behind a different name, arity or
return shape fails tests it has functionally satisfied, and that is a measure of guessing rather
than of engineering. The option contracts matter as much as the names, because
append-versus-overwrite is not derivable from prose.

This table is not exhaustive. Objectives absent from it require the interface to be derived.

| Module | Symbol | Parameters | Returns |
| --- | --- | --- | --- |
| `dvc.repo.status` | `_cloud_status` | self, targets, jobs, remote, all_branches, with_deps, all_tags, recursive, all_commits | the cloud status mapping. status() dispatches here when cloud is set and to _local_status otherwise, so the target must be resolved as a path to a dataset rather than searched for beneath a directory. |
| `dvc.commands.data` | `CmdDataStatus` | the data status parser gains -r / --remote with metavar <name> | no return; the option is declared on data_status_parser with completion.REMOTE and is only applicable alongside --not-in-remote. Accepting the flag without threading it to remote selection does not satisfy the objective. |
| `dvc.commands.experiments.show` | `add_parser` | experiments_show_parser --keep and --drop | no return; both options carry action append with an empty-list default, so every occurrence accumulates. Zero occurrences leaves the list empty and the filter is then not applied at all: an empty `--keep` protects nothing, and must not be read as protecting everything. Accumulated patterns are joined into one alternation and matched against each column name from the start of the name, not searched anywhere within it. An implementation that overwrites on repeat, or that uses nargs, does not satisfy the objective. |
| `dvc.repo.init` | `init` | root_dir=os.curdir, no_scm=False, force=False, subdir=False | a Repo constructed on root_dir. Every path the initialisation writes derives from that argument; changing the process working directory instead leaves the rest of the command observing a directory the caller did not name. |
| `dvc.repo.checkout` | `checkout` | self, targets, with_deps, force, relink, recursive, allow_missing | a dict, the collected changes merged with a stats key, as changes combined with a single stats entry. The reported figures come from the statistics the operation itself collected, not from a count recomputed by re-walking the tree afterwards. |
| `dvc.repo.index` | `index_from_targets` | a module-level function, not a method on `Index`: repo, targets, stage_filter, outs_filter, max_size, types, with_deps, recursive, and the remaining keyword arguments `Index.targets_view` accepts | the view `Index.targets_view` returns for those targets. Reaching the same behaviour through a method on `Index` leaves the module-level name the graded tests import undefined. |

## Where to work

Edits are collected from `dvc/` and `tests/` and from nowhere else, so keep your changes inside
them. The project's tests live under `tests/unit/` and `tests/func/`. Run them the way the project
does:

```sh
python -m pytest tests/unit -q
python -m pytest tests/func -q
```
