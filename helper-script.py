import argparse
import logging
import os
import re
import shutil
import subprocess
import typing

import requests
from github import Auth, Github

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

WORKING_DIR = "./tmp"
DIFF_FILE = "./diff.patch"

auth = Auth.Token(os.getenv("GITHUB_TOKEN"))
g = Github(auth=auth)


def get_diff_as_patch(repo: str, pull_request_number: int):
    logger.info("Getting diff from PR ...")

    pr_diff_url = g.get_repo(repo).get_pull(pull_request_number).diff_url

    res = requests.get(pr_diff_url)
    if res.status_code != requests.codes.ok:
        logger.error(f"Error getting diff from PR {pull_request_number}.")
        exit(1)

    with open(DIFF_FILE, "w") as f:
        f.write(res.text)


def clone(repo: str):
    logger.info("Cloning repository ...")

    shutil.rmtree(WORKING_DIR, ignore_errors=True)

    clone_url = f"git@github.com:{repo}.git"
    command = ["git", "clone", clone_url, WORKING_DIR]

    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        logger.error(f"Error cloning reop {repo}: {result.stderr}")
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
        logger.error(f"Error creating new branch {head}: {result.stderr}")
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
            logger.error(f"Error applying diff: {result.stderr}")
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
        logger.error(f"Error pushing changes to branch {head}: {result.stderr}")
        exit(1)


def create_pr(repo: str, base: str, head: str, conflict: bool):
    logger.info("Creating PR ...")

    title = f"chore: merging diff into branch {base}"
    body = f"Automated change: merging diff into branch {base}"

    if conflict:
        title = f"{title} CONFLICTS!"
        body = f"**Conflicts! Need human intervention!**\n\n{body}"

    repo = g.get_repo(repo)
    pr = repo.create_pull(base=base, head=head, title=title, body=body)
    if not pr:
        logger.error("Error creating PR.")
        exit(1)
    logger.info(f"PR {pr.number} created.")


def get_all_chapters_branches(repo: str) -> typing.List[str]:
    return sorted(
        [b.name for b in g.get_repo(repo).get_branches() if re.search(r"\d", b.name)]
    )


def get_pr_base_branch(repo: str, pull_request_number: int) -> str:
    return g.get_repo(repo).get_pull(pull_request_number).base.ref


def apply_diff_to_branch_and_create_pr(
    repo: str, base: str, owner: str, ignore_conflicts: bool
):
    logger.info(f"=== Working on branch {base} ===")

    head_branch = create_new_branch_based_on(base)

    conflict = apply_patch()
    if conflict and not ignore_conflicts:
        return True

    commit_diff(head_branch)

    create_pr(repo, base, f"{owner}:{head_branch}", conflict)


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
):
    upstream_repo = f"{upstream_owner}/{upstream_repo_name}"
    fork_repo = f"{fork_owner}/{fork_repo_name}"

    get_diff_as_patch(upstream_repo, pull_request_number)
    clone(fork_repo)

    pr_base = get_pr_base_branch(upstream_repo, pull_request_number)
    target_branches = [
        b for b in get_all_chapters_branches(upstream_repo) if b > pr_base
    ]

    for branch in target_branches:
        conflict = apply_diff_to_branch_and_create_pr(
            upstream_repo, branch, fork_owner, ignore_conflicts
        )

        if conflict and not ignore_conflicts:
            logger.info(
                f"Conflict merging diff into branch {branch}, aborting this PR and following PRs."
            )
            break

    cleanup()  # comment this line out to keep tmp dir and diff file for debugging

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

    args = parser.parse_args()

    main(
        args.upstream_owner,
        args.upstream_repo_name,
        args.fork_owner,
        args.fork_repo_name,
        args.pull_request_number,
        args.ignore_conflicts,
    )
