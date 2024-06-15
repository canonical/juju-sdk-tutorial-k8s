# Hacking

## Helper Script

The `helper-script.py` script (only exists in the main branch) does the following:

- Get the diff from a PR;
- find out which chapter that PR is about;
- create branches (in your forked repo), merge the diff into all following chapters, commit, and push;
- create PRs to the upstream.

### Configuration

- GITHUB_TOKEN env var is set.

### Dependencies

- `git` CLI
- `tox`
- `PyGithub`, `requests` (both are already automatically managed by `tox`)

### Usage

```console
usage: helper-script.py [-h] [-u UPSTREAM_OWNER] -f FORK_OWNER [-ur UPSTREAM_REPO_NAME]
               [-fr FORK_REPO_NAME] -p PULL_REQUEST_NUMBER [-i]

options:
  -h, --help            show this help message and exit
  -u UPSTREAM_OWNER, --upstream-owner UPSTREAM_OWNER
                        The upstream owner of the repository, defaults to
                        `canonical`.
  -f FORK_OWNER, --fork-owner FORK_OWNER
                        The forked repo's owner, mandatory. Normally, it should be
                        your own GitHub user name.
  -ur UPSTREAM_REPO_NAME, --upstream-repo-name UPSTREAM_REPO_NAME
                        The repository name in the upstream, defaults to `juju-sdk-
                        tutorial-k8s`.
  -fr FORK_REPO_NAME, --fork-repo-name FORK_REPO_NAME
                        The repository name of the forked repo, defaults to `juju-
                        sdk-tutorial-k8s`.
  -p PULL_REQUEST_NUMBER, --pull-request-number PULL_REQUEST_NUMBER
                        The PR number from which you want to merge the diff into
                        other branches.
  -i, --ignore-conflicts
                        Still create the PR (and following PRs) when conflicts occur
                        in the current branch.
```

Usage examples:

- upstream org: `canonical`
- forked repo owner: `IronCore864`
- repo name: `juju-sdk-tutorial-k8s` (both upstream and forked)

Get the diff from PR No.1 in the upstream repo and merge the diff into later chapters:

```bash
$ tox -- -f IronCore864 -p 1
```

When there is a conflict in a chapter, that PR won't be created and the script exists, PRs for following chapters _won't_ be created.

To ignore conflicts and create all PRs for all following chapters anyway, add the `-i` (`--ignore-conflicts`) flag:

```bash
$ tox -- -f IronCore864 -p 1 -i
```

### Testing

For testing purposes, create an org to use it as upstream, then fork it. Example:

- upstream org: `IronCoreWorks`
- forked repo owner: `IronCore864`
- repo name: `juju-k8s-charm-tutorial` (both upstream and forked)

```bash
# when there is a conflict, stop
$ tox -- -u IronCoreWorks -f IronCore864 -ur juju-k8s-charm-tutorial -fr juju-k8s-charm-tutorial -p 1
# ignore conflicts and create all PRs for all following chapters
$ tox -- -u IronCoreWorks -f IronCore864 -ur juju-k8s-charm-tutorial -fr juju-k8s-charm-tutorial -p 1 -i
```

### Formatting

```bash
$ tox -e fmt
```

This formats the code and sorts the imports using [the Ruff formatter](https://docs.astral.sh/ruff/formatter/).
