#!/bin/python3

from contextlib import contextmanager
import datetime
import errno
import time
import shutil
import sys
import tempfile
from os.path import join

# local imports
import consts
from args import Arguments
from github import Github
from utils import add_to_commit, clone_repo
from utils import checkout_target_branch, write_error
from utils import commit, write_msg
from utils import get_last_commit_date
from utils import check_if_up_to_date, revert_git_history


@contextmanager
def temporary_directory():
    name = tempfile.mkdtemp()
    try:
        yield name
    finally:
        try:
            shutil.rmtree(name)
        except OSError as err:
            # if the directory has already been removed, no need to raise an error
            if err.errno != errno.ENOENT:
                raise


def write_merged_prs(merged_prs, contributors, repo_url):
    content = ""
    for merged_pr in reversed(merged_prs):
        if merged_pr.title.startswith("[release] "):
            continue
        if merged_pr.author not in contributors:
            contributors.append(merged_pr.author)
        md_content = (
            merged_pr.title.replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace("[", "\\[")
            .replace("]", "\\]")
            .replace("*", "\\*")
            .replace("_", "\\_")
        )
        content += f" * [{md_content}]({repo_url}/pull/{merged_pr.number})\n"
    return content + "\n"


def checkout_to_previous_release_branch(repo_name, temp_dir):
    for crate in consts.CRATE_LIST:
        if not crate["crate"].endswith("-sys") and crate["repository"] == repo_name:
            original_version = crate["current"]
            # In this case, we keep all three version digits because we want the previous major
            # tag.
            version = crate["previous"]
            write_msg(
                f"For repository `{repo_name}`, the previous major release tag was guessed as "
                f"`{version}`, (from `{original_version}`) let's try to checkout to it..."
            )
            if not checkout_target_branch(
                repo_name, temp_dir, version, ask_input=False
            ):
                input("Failed to checkout to this branch... Press ENTER to continue")
                return False
            return True
    write_error(f"No crate matches the repository `{repo_name}` apparently...")
    return False


def build_blog_post(repositories, temp_dir, token):
    write_msg("=> Building blog post...")

    author = input("Enter author name: ")
    title = input("Enter title: ")
    blog_post_date = time.strftime("%Y-%m-%d %H:00:00 +0000")
    content = f"""---
layout: post
author: {author}
title: {title}
categories: [front, crates]
date: {blog_post_date}
---

* Write intro here *

### Changes

For the interested ones, here is the list of the merged pull requests:

"""
    contributors = []
    git = Github(token)
    oldest_date = None

    for repo in repositories:
        need_revert = checkout_to_previous_release_branch(repo, temp_dir)
        success, out, err = get_last_commit_date(repo, temp_dir)
        if not success:
            write_msg(f"Couldn't get PRs for '{repo}': {err}")
        else:
            max_date = datetime.date.fromtimestamp(int(out))
            if oldest_date is None or max_date < oldest_date:
                oldest_date = max_date
            write_msg(f"Gettings merged PRs from {repo}...")
            merged_prs = git.get_pulls(
                repo, consts.ORGANIZATION, "closed", max_date, only_merged=True
            )
            write_msg(f"=> Got {len(merged_prs)} merged PRs")
            if len(merged_prs) > 0:
                repo_url = f"{consts.GITHUB_URL}/{consts.ORGANIZATION}/{repo}"
                content += f"[{repo}]({repo_url}):\n\n"
                content += write_merged_prs(merged_prs, contributors, repo_url)
        if need_revert:
            # If we switched back to the tag, we need to cancel this to come back to the previous
            # repository state.
            revert_git_history(repo, temp_dir, 1)

    write_msg("Gettings merged PRs from gir...")
    merged_prs = git.get_pulls(
        "gir", consts.ORGANIZATION, "closed", oldest_date, only_merged=True
    )
    write_msg(f"=> Got {len(merged_prs)} merged PRs")
    if len(merged_prs) > 0:
        repo_url = f"{consts.GITHUB_URL}/{consts.ORGANIZATION}/gir"
        content += f"All this was possible thanks to the [gtk-rs/gir]({repo_url}) project as well:"
        content += "\n\n"
        content += write_merged_prs(merged_prs, contributors, repo_url)

    content += "Thanks to all of our contributors for their (awesome!) work on this release:\n\n"
    # Sort contributors list alphabetically with case insensitive.
    contributors = sorted(contributors, key=lambda s: s.casefold())
    content += "\n".join(
        [
            f" * [@{contributor}]({consts.GITHUB_URL}/{contributor})"
            for contributor in contributors
        ]
    )
    content += "\n"

    current_date = time.strftime("%Y-%m-%d")
    file_name = join(
        join(temp_dir, consts.BLOG_REPO), f"_posts/{current_date}-new-release.md"
    )
    try:
        with open(file_name, "w", encoding="utf-8") as outfile:
            outfile.write(content)
            write_msg(f'New blog post written into "{file_name}".')
        add_to_commit(consts.BLOG_REPO, temp_dir, [file_name])
        commit(consts.BLOG_REPO, temp_dir, "Add new blog post")
    except Exception as err:
        write_error(f"build_blog_post failed: {err}")
        write_msg(f"\n=> Here is the blog post content:\n{content}\n<=")
    write_msg("Done!")


def clone_repositories(args, temp_dir):
    write_msg("=> Cloning the repositories...")
    repositories = []
    for crate in args.crates:
        if crate["repository"] not in repositories:
            repositories.append(crate["repository"])
            if clone_repo(crate["repository"], temp_dir) is False:
                write_error(f'Cannot clone the "{crate["repository"]}" repository...')
                return []
    if len(repositories) < 1:
        write_msg("No crate found. Aborting...")
        return []
    if clone_repo(consts.BLOG_REPO, temp_dir, depth=1) is False:
        write_error(f'Cannot clone the "{consts.BLOG_REPO}" repository...')
        return []
    write_msg("Done!")
    return repositories


def start(args, temp_dir):
    repositories = clone_repositories(args, temp_dir)
    if len(repositories) < 1:
        return
    build_blog_post(repositories, temp_dir, args.token)
    input(
        "Blog post generated, press ENTER to quit (it'll remove the tmp folder and "
        "its content!)"
    )


def main(argv):
    args = Arguments.parse_arguments(argv)
    if args is None:
        sys.exit(1)
    if check_if_up_to_date() is False:
        return
    write_msg("=> Creating temporary directory...")
    with temporary_directory() as temp_dir:
        write_msg(f'Temporary directory created in "{temp_dir}"')
        start(args, temp_dir)


# Beginning of the script
if __name__ == "__main__":
    main(sys.argv[1:])
