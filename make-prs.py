"""This script helps to make pull requests for the tutorial.

It does the following:

- Get the diff from a PR;
- find out which chapter that PR is about;
- create branches (in your forked repo), merge the diff into all following chapters, commit, and push;
- create PRs to the upstream.

Read the CONTRIBUTING.md file for more details.
"""

import argparse
import logging
import os
import re
import shutil
import subprocess
import typing

import github
import requests

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

WORKING_DIR = "./tmp"
DIFF_FILE = "./diff.patch"

if "GITHUB_TOKEN" not in os.environ:
    logger.critical("Environment variable GITHUB_TOKEN not set.")
    exit(1)

auth = github.Auth.Token(os.getenv("GITHUB_TOKEN"))
gh_client = github.Github(auth=auth)


def get_diff_as_patch(repo: str, pull_request_number: int):
    logger.info("Getting diff from PR ...")

    pr_diff_url = gh_client.get_repo(repo).get_pull(pull_request_number).diff_url

    res = requests.get(pr_diff_url)
    res.raise_for_status()

    with open(DIFF_FILE, "w") as f:
        f.write(res.text)


def clone(repo: str):
    logger.info("Cloning repository ...")

    shutil.rmtree(WORKING_DIR, ignore_errors=True)

    clone_url = f"git@github.com:{repo}.git"
    command = ["git", "clone", "--depth=1", "--no-single-branch", clone_url, WORKING_DIR]

    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        logger.critical(f"Error cloning repo {repo}: {result.stderr}")
        exit(1)


def create_new_branch_based_on(base: str) -> str:
    logger.info("Creating branch ...")

    head = f"{base}-update"

    command = [
        "git",
        "checkout",
        "-b",
        head,
        f"origin/{base}",
    ]
    result = subprocess.run(command, cwd=WORKING_DIR, capture_output=True, text=True)
    if result.returncode != 0:
        logger.critical(f"Error creating new branch {head}: {result.stderr}")
        exit(1)

    return head


def apply_patch() -> bool:
    logger.info("Applying patch ...")

    command = [
        "git",
        "apply",
        "--3way",
        "../diff.patch",
    ]
    result = subprocess.run(command, cwd=WORKING_DIR, capture_output=True, text=True)
    if result.returncode != 0:
        if "conflicts" in result.stderr:
            return True
        else:
            logger.critical(f"Error applying diff: {result.stderr}")
            exit(1)


def commit_diff(head: str):
    logger.info("Pushing changes ...")

    add = ["git", "add", "."]
    subprocess.run(add, cwd=WORKING_DIR, capture_output=True, text=True)

    commit = ["git", "commit", "-m", "chore: merging diff"]
    subprocess.run(commit, cwd=WORKING_DIR, capture_output=True, text=True)

    push = ["git", "push", "-f", "origin", head]
    result = subprocess.run(push, cwd=WORKING_DIR, capture_output=True, text=True)

    if result.returncode != 0:
        logger.critical(f"Error pushing changes to branch {head}: {result.stderr}")
        exit(1)


def create_pr(repo: str, base: str, head: str, conflict: bool, original_pr: str):
    logger.info("Creating PR ...")

    title = f"chore: merging diff from PR #{original_pr} into branch {base}"
    body = f"Automated change: merging diff from PR #{original_pr} into branch {base}"

    if conflict:
        title = f"{title} CONFLICTS!"
        body = f"**Conflicts! Need human intervention!**\n\n{body}"

    repo = gh_client.get_repo(repo)
    pr = repo.create_pull(base=base, head=head, title=title, body=body, draft=conflict)
    logger.info(f"PR {pr.number} created: {pr.url}")


def get_all_chapters_branches(repo: str) -> typing.List[str]:
    branches = gh_client.get_repo(repo).get_branches()
    return sorted(b.name for b in branches if re.search(r"\d+_", b.name))


def get_pr_base_branch(repo: str, pull_request_number: int) -> str:
    return gh_client.get_repo(repo).get_pull(pull_request_number).base.ref


def apply_diff_to_branch_and_create_pr(repo: str, base: str, owner: str, ignore_conflicts: bool, original_pr: str):
    logger.info(f"=== Working on branch {base} ===")

    head_branch = create_new_branch_based_on(base)

    conflict = apply_patch()
    if conflict and not ignore_conflicts:
        return True

    commit_diff(head_branch)

    create_pr(repo, base, f"{owner}:{head_branch}", conflict, original_pr)


def cleanup():
    logger.info("Cleaning up ...")

    if os.path.exists(DIFF_FILE):
        os.remove(DIFF_FILE)

    shutil.rmtree(WORKING_DIR, ignore_errors=True)


def main(
    upstream_owner,
    upstream_repo_name,
    fork_owner,
    fork_repo_name,
    pull_request_number,
    ignore_conflicts,
    keep_tmp,
):
    upstream_repo = f"{upstream_owner}/{upstream_repo_name}"
    fork_repo = f"{fork_owner}/{fork_repo_name}"

    get_diff_as_patch(upstream_repo, pull_request_number)
    clone(fork_repo)

    pr_base = get_pr_base_branch(upstream_repo, pull_request_number)
    target_branches = [b for b in get_all_chapters_branches(upstream_repo) if b > pr_base]

    for branch in target_branches:
        has_conflict = apply_diff_to_branch_and_create_pr(
            upstream_repo, branch, fork_owner, ignore_conflicts, pull_request_number
        )

        if has_conflict and not ignore_conflicts:
            logger.error(
                f"Conflict merging diff into branch {branch}, aborting this PR and following PRs."
            )
            break

    if not keep_tmp:
        cleanup()

    logger.info("Done!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "-u",
        "--upstream-owner",
        type=str,
        default="canonical",
        help="The upstream owner of the repository, defaults to `canonical`.",
    )
    parser.add_argument(
        "-f",
        "--fork-owner",
        type=str,
        required=True,
        help="The forked repo's owner, mandatory. Normally, it should be your own GitHub user name.",
    )
    parser.add_argument(
        "-ur",
        "--upstream-repo-name",
        type=str,
        default="juju-sdk-tutorial-k8s",
        help="The repository name in the upstream, defaults to `juju-sdk-tutorial-k8s`.",
    )
    parser.add_argument(
        "-fr",
        "--fork-repo-name",
        type=str,
        default="juju-sdk-tutorial-k8s",
        help="The repository name of the forked repo, defaults to `juju-sdk-tutorial-k8s`.",
    )
    parser.add_argument(
        "-p",
        "--pull-request-number",
        required=True,
        type=int,
        help="The PR number from which you want to merge the diff into other branches.",
    )
    parser.add_argument(
        "-i",
        "--ignore-conflicts",
        action="store_true",
        help="Still create the PR (and following PRs) when conflicts occur in the current branch.",
    )
    parser.add_argument(
        "--keep-tmp",
        action="store_true",
        help="Keep tmp dir and diff file for debugging.",
    )

    args = parser.parse_args()

    main(
        args.upstream_owner,
        args.upstream_repo_name,
        args.fork_owner,
        args.fork_repo_name,
        args.pull_request_number,
        args.ignore_conflicts,
        args.keep_tmp,
    )
