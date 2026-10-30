<!-- Release notes generated using configuration in .github/release.yml at main -->

## What's Changed
### Behavioral Changes (CLI)
* In `dvc status --cloud`, `target` now supports specifying path to a dataset. Previously, specifying a directory as the target caused DVC to search for `.dvc` and `dvc.yaml` files inside it, from which the datasets specified in those files were then checked for cloud/remote status, rather than considering the directory itself as a dataset.
While this is technically a breaking change, we consider the previous behavior a bug and inconsistent with other DVC commands, including _plain_ `dvc status`. To restore the previous behavior, add the `--recursive` option.

  Fixes https://github.com/iterative/dvc/issues/9336.

### 🚀 New Features and Enhancements
* add `--remote` option to `dvc data status --not-in-remote` for checking files against a specified remote (instead of a default one) by @skshetry in https://github.com/iterative/dvc/pull/10843

	```console
	# Check against the 'my-s3' remote instead of the default
	$ dvc data status --not-in-remote --remote my-s3
	```

* `exp show` accepts multiple `--keep` and `--drop` arguments in https://github.com/iterative/dvc/pull/10857

	```console
    $ dvc exp show --keep 'featurize' --keep 'avg_prec' --drop '.*train' --drop '.*split'
	```

* `dvc init` supports initializing DVC repository in an arbitrary directory in https://github.com/iterative/dvc/pull/10861

	```console
    $ dvc init /path/to/dvc/repo/that/I/want/to/initialize
	```

* `checkout` and `pull` reports granular summary of changes in https://github.com/iterative/dvc/pull/10842

	Before, DVC would report statistics only about datasets affected during `checkout` phase.

	```console
    $ dvc pull dataset/train/4
	A       dataset/
	1 file added and 5843 files fetched
	```
	
	Now, it will report granular number of files affected by the operation.
	```console
    $ dvc pull dataset/train/4
	A       dataset/
	5842 files added and 5843 files fetched
	```

* `data status` now detects file moves/renames by default in https://github.com/iterative/dvc/pull/10846

	```console
    $ dvc move foo bar
    $ dvc data status
	DVC committed changes:
	  (git commit the corresponding dvc files to update the repo)
	        renamed: foo -> bar
    ```

* `dvcignore`: share implementation between `check-ignore` and internal API used by DVC, improve support for unignores (eg: `!data/**` rules) in https://github.com/iterative/dvc/pull/10856 (Fixes https://github.com/iterative/dvc/issues/10722 and https://github.com/iterative/dvc/issues/10122)

* support completing remote name in zsh/bash in https://github.com/iterative/dvc/pull/10858

	```console
	$ dvc push --remote <TAB>
	local my-s3
	```


### ⚡ Optimizations
* load only a stage/.dvc file if the target is an address to that particular stage in https://github.com/iterative/dvc/pull/10838 (Fixes https://github.com/iterative/dvc/issues/8768)
* batch dump stages in `commit`, do not re-read on save from the workspace in https://github.com/iterative/dvc/pull/10839 (Fixes https://github.com/iterative/dvc/issues/10629)

### 🐛 Bug Fixes
* do not show missing cache entries on `dvc diff` result in https://github.com/iterative/dvc/pull/10845 (Fixes https://github.com/iterative/dvc/pull/7661)
* handle missing DVC repo at Git HEAD in `dvc data status` in https://github.com/iterative/dvc/pull/10862
* show entry in "Not in cache" if dir entry is missing in `dvc diff` in https://github.com/iterative/dvc/pull/10844 (Fixes https://github.com/iterative/dvc/issues/7661)
* fix `dvc.yaml` filepath in error message when reading from git revisions in https://github.com/iterative/dvc/pull/10847

### 🔨 Maintenance
* fix some, suppress some issues from ty check in https://github.com/iterative/dvc/pull/10841




**Full Changelog**: https://github.com/iterative/dvc/compare/3.62.0...3.63.0