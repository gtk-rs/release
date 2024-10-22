#!/bin/python3

from contextlib import contextmanager
import errno
import time
import shutil
import sys
import tempfile
from os.path import join
import os
import requests
import getopt

REPOSITORIES = [
    {"name": "gtk4-rs", "start-at": "2023-07-23", "end-at": "2024-02-04"},
    {"name": "gtk-rs-core", "start-at": "2023-07-23", "end-at": "2024-02-04"},
]


def github_search(token, repo_name, start_date, end_date):
    query = """
query {
  
  search(query: "repo:gtk-rs/{repo_name} is:pr is:closed merged:{start_date}..{end_date} base:main sort:created-desc -author:app/dependabot", type: ISSUE, last: 100) {
    edges {
      node {
        ... on PullRequest {
          url 
          title
          mergedAt
          author {
            login
          }
        }
      }
    }
  }
}
""".replace("{repo_name}", repo_name)
    query = query.replace("{start_date}", start_date)
    query = query.replace("{end_date}", end_date)
    headers = {"Authorization": f"Bearer {token}"}
    request = requests.post(
        "https://api.github.com/graphql", json={"query": query}, headers=headers
    )
    if request.status_code == 200:
        return request.json()["data"]["search"]["edges"]
    else:
        raise Exception(
            "Query failed to run by returning code of {}. {}".format(
                request.status_code, query
            )
        )


def write_help():
    print("release.py accepts the following options:")
    print("")
    print(" * -h | --help                  : display this message")
    print(" * -t <token> | --token=<token> : give the github token")


class Arguments:
    def __init__(self):
        self.token = None

    @staticmethod
    def parse_arguments(argv):
        try:
            opts = getopt.getopt(argv, "ht:m:c:", ["help", "token="])[
                0
            ]  # second argument is "args"
        except getopt.GetoptError:
            write_help()
            return None

        instance = Arguments()

        for opt, arg in opts:
            if opt in ("-h", "--help"):
                write_help()
                return None
            if opt in ("-t", "--token"):
                instance.token = arg
            else:
                print(f'"{opt}": unknown option')
                print('Use "-h" or "--help" to see help')
                return None
        if instance.token is None:
            # In this case, I guess it's not an issue to not have a github token...
            print("Missing token argument.")
            return None

        return instance


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


def write_merged_prs(merged_prs, contributors):
    content = ""
    for merged_pr in merged_prs:
        merged_pr = merged_pr["node"]
        if merged_pr["author"]["login"] not in contributors:
            contributors.append(merged_pr["author"]["login"])
        md_content = (
            merged_pr["title"]
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace("[", "\\[")
            .replace("]", "\\]")
            .replace("*", "\\*")
            .replace("_", "\\_")
        )
        content += f" * [{md_content}]({merged_pr['url']})\n"
    return content + "\n"


def build_blog_post(temp_dir, token):
    print("=> Building blog post...")

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
    for repo in REPOSITORIES:
        repo_name = repo["name"]
        merged_prs = github_search(token, repo_name, repo["start-at"], repo["end-at"])
        print(f"=> Got {len(merged_prs)} merged PRs")
        if len(merged_prs) > 0:
            repo_url = f"https://github.com/gtk-rs/{repo_name}"
            content += f"[{repo_name}]({repo_url}):\n\n"
            content += write_merged_prs(merged_prs, contributors)

    print("Gettings merged PRs from gir...")
    merged_prs = github_search(
        token, "gir", REPOSITORIES[0]["start-at"], REPOSITORIES[0]["end-at"]
    )
    print(f"=> Got {len(merged_prs)} merged PRs")
    if len(merged_prs) > 0:
        repo_url = f"https://github.com/gtk-rs/gir"
        content += f"All this was possible thanks to the [gtk-rs/gir]({repo_url}) project as well:"
        content += "\n\n"
        content += write_merged_prs(merged_prs, contributors)

    content += "Thanks to all of our contributors for their (awesome!) work on this release:\n\n"
    # Sort contributors list alphabetically with case insensitive.
    contributors = sorted(contributors, key=lambda s: s.casefold())
    content += "\n".join(
        [
            f" * [@{contributor}](https://github.com/{contributor})"
            for contributor in contributors
        ]
    )
    content += "\n"

    current_date = time.strftime("%Y-%m-%d")
    file_name = join(
        join(temp_dir, "gtk-rs.github.io"), f"_posts/{current_date}-new-release.md"
    )
    try:
        os.makedirs(os.path.dirname(file_name))
        with open(file_name, "w", encoding="utf-8") as outfile:
            outfile.write(content)
        print(f'New blog post written into "{file_name}".')
    except Exception as err:
        print(f"build_blog_post failed: {err}")
        print(f"\n=> Here is the blog post content:\n{content}\n<=")
    print("Done!")


def start(args, temp_dir):
    build_blog_post(temp_dir, args.token)
    input(
        "Blog post generated, press ENTER to quit (it'll remove the tmp folder and "
        "its content!)"
    )


def main(argv):
    args = Arguments.parse_arguments(argv)
    if args is None:
        sys.exit(1)
    print("=> Creating temporary directory...")
    with temporary_directory() as temp_dir:
        print(f'Temporary directory created in "{temp_dir}"')
        start(args, temp_dir)


# Beginning of the script
if __name__ == "__main__":
    main(sys.argv[1:])
