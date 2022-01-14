#!/bin/python3

from contextlib import contextmanager
# pip3 install datetime
import datetime
import errno
import time
import shutil
import sys
import tempfile
from os import sep as os_sep
from os import listdir
from os.path import isdir, join

# local imports
import consts
from args import Arguments, UpdateType
from github import Github
from globals import CRATES_VERSION, PULL_REQUESTS
from my_toml import TomlHandler
from utils import add_to_commit, clone_repo
from utils import checkout_target_branch, get_file_content, write_error, write_into_file
from utils import commit, commit_and_push, create_pull_request, push, write_msg
from utils import create_tag_and_push, publish_crate, get_last_commit_date
from utils import check_if_up_to_date, checkout_to_new_branch


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


# Doesn't handle version number containing something else than numbers and '.'!
def update_version(version, update_type, section_name, place_type="section"):
    version_split = version.replace('"', '').split('.')
    if len(version_split) != 3:
        # houston, we've got a problem!
        write_error(f'Invalid version in {place_type} "{section_name}": {version}')
        return None
    if update_type == UpdateType.MINOR:
        version_split[update_type] = str(int(version_split[update_type]) + 1)
    elif update_type == UpdateType.MEDIUM:
        version_split[update_type] = str(int(version_split[update_type]) + 1)
        version_split[UpdateType.MINOR] = '0'
    else:
        version_split[update_type] = str(int(version_split[update_type]) + 1)
        version_split[UpdateType.MEDIUM] = '0'
        version_split[UpdateType.MINOR] = '0'
    new_version = '.'.join(version_split)
    return f'"{new_version}"'


def update_crate_version(repo_name, crate_dir_path, temp_dir, update_type):
    file_path = join(join(join(temp_dir, repo_name), crate_dir_path), "Cargo.toml")
    output = file_path.replace(temp_dir, "")
    if output.startswith('/'):
        output = output[1:]
    write_msg(f'=> Updating crate versions for {file_path}')
    content = get_file_content(file_path)
    if content is None:
        return False
    toml = TomlHandler(content)
    for section in toml.sections:
        if section.name == 'package':
            new_version = update_version(
                section.get('version', '0.0.0'),
                update_type,
                'version',
                place_type="package")
            if new_version is None:
                return False
            section.set('version', new_version)
            break
    result = write_into_file(file_path, str(toml))
    res = output.split(os_sep)[-2]
    status = 'Failure' if result is False else 'Success'
    write_msg(f'=> {res}: {status}')
    return result


def get_all_versions(args, temp_dir):
    write_msg('=> Getting crates version...')
    for crate in args.crates:
        crate = crate['crate']
        if args.specified_crate is not None and crate['crate'] != args.specified_crate:
            continue
        if not get_crate_version(crate["repository"], crate["crate"], crate["path"], temp_dir):
            folder = join(temp_dir, crate['path'])
            input(f"Couldn't find version for in `{folder}`...")
    write_msg('Done!')


def get_crate_version(repo_name, crate_name, crate_dir_path, temp_dir):
    file_path = join(join(join(temp_dir, repo_name), crate_dir_path), "Cargo.toml")
    output = file_path.replace(temp_dir, "")
    if output.startswith('/'):
        output = output[1:]
    write_msg(f'=> Updating versions for {file_path}')
    content = get_file_content(file_path)
    if content is None:
        return False
    toml = TomlHandler(content)
    for section in toml.sections:
        if (section.name == 'package' or
                (section.name.startswith('dependencies.') and find_crate(section.name[13:]))):
            version = section.get('version', None)
            if version is None:
                continue
            CRATES_VERSION[crate_name] = version
            return True
    return False


def update_examples(path, temp_dir):
    for entry in listdir(path):
        if entry == "Cargo.toml":
            update_crate_cargo_file(path, temp_dir)
            continue
        full_path = join(path, entry)
        if isdir(full_path):
            update_examples(full_path, temp_dir)


def update_crates_cargo_file(args, temp_dir):
    write_msg('==> Updating versions in crates...')
    for crate in args.crates:
        crate = crate['crate']
        update_crate_cargo_file(join(join(temp_dir, crate['repository']), crate['path']), temp_dir)
    write_msg('Done!')
    write_msg('==> Now updating versions in examples...')
    for example in consts.EXAMPLES:
        update_examples(join(join(temp_dir, example['repository']), example['path']), temp_dir)
    write_msg('Done!')


def get_crate(crate_name):
    for entry in consts.CRATE_LIST:
        if entry['crate'] == crate_name:
            return crate_name
    return None


def find_crate(crate_name):
    return get_crate(crate_name) is not None


def get_crate_in_package(value):
    if not value.strip().startswith('{'):
        return None
    parts = [y.strip() for y in value[1:-1].split('",')]
    for part in parts:
        if part.split('=')[0].strip() == 'package':
            return get_crate(part.split('=')[1].replace('"', '').strip())
    return None


def update_crate_cargo_file(path, temp_dir):
    # pylint: disable=too-many-branches,too-many-locals,too-many-nested-blocks
    file_path = join(path, "Cargo.toml")
    output = file_path.replace(temp_dir, "")
    if output.startswith('/'):
        output = output[1:]
    write_msg(f'=> Updating versions for {file_path}')
    content = get_file_content(file_path)
    if content is None:
        return False
    toml = TomlHandler(content)
    for section in toml.sections:
        if section.name.startswith('dependencies.'):
            real = section.get('package', None)
            if real is None:
                real = section.name[13:]
            real = real.replace('"', '')
            if find_crate(real):
                section.remove("git")
                section.set('version', CRATES_VERSION[real])
        elif section.name == 'dependencies':
            for entry in section.entries:
                info = entry['value'].strip()
                crate_name = get_crate_in_package(info)
                if crate_name is None:
                    crate_name = get_crate(entry['key'])
                if crate_name is not None:
                    if info.strip().startswith('{'):
                        parts = [y.strip() for y in info[1:-1].split(',')]
                        parts = [y for y in parts
                                 if not y.startswith("git ") and not y.startswith("git=")]
                        version = CRATES_VERSION[crate_name]
                        parts.append(f'version = {version}')
                        if len(parts) > 1:
                            joined = ', '.join(parts)
                            entry['value'] = f'{{{joined}}}'
                        else:
                            entry['value'] = CRATES_VERSION[entry['key']]
                    else:
                        entry['value'] = CRATES_VERSION[entry]
    out = str(toml)
    if not out.endswith("\n"):
        out += '\n'
    result = True
    result = write_into_file(file_path, out)
    res = output.split(os_sep)[-2]
    status = 'Failure' if result is False else 'Success'
    write_msg(f'=> {res}: {status}')
    return result


def write_merged_prs(merged_prs, contributors, repo_url):
    content = ''
    for merged_pr in reversed(merged_prs):
        if merged_pr.title.startswith('[release] '):
            continue
        if merged_pr.author not in contributors:
            contributors.append(merged_pr.author)
        md_content = (merged_pr.title.replace('<', '&lt;')
                      .replace('>', '&gt;')
                      .replace('[', '\\[')
                      .replace(']', '\\]')
                      .replace('*', '\\*')
                      .replace('_', '\\_'))
        content += f' * [{md_content}]({repo_url}/pull/{merged_pr.number})\n'
    return content + '\n'


def downgrade_version(version):
    # We need to remove the '"' from the version number.
    parts = version.replace('"', '').split(".")
    while len(parts) < 3:
        parts.append('0')
    for pos, part in enumerate(parts):
        tmp = int(part)
        if tmp > 0:
            tmp -= 1
            parts[pos] = str(tmp)
            pos += 1
            while pos < len(parts):
                parts[pos] = '0'
                pos += 1
            break
    return '.'.join(parts)


def checkout_to_last_release_branch(repo_name, temp_dir):
    for crate in consts.CRATE_LIST:
        if not crate['crate'].endswith('-sys') and crate['repository'] == repo_name:
            original_version = CRATES_VERSION[crate['crate']]
            # In this case, we keep all three version digits because we want the previous major
            # tag.
            version = downgrade_version(original_version)
            write_msg(
                f'For repository `{repo_name}`, the previous major release tag was guessed as '
                f'`{version}`, (from `{original_version}`) let\'s try to checkout to it...')
            if not checkout_target_branch(repo_name, temp_dir, version, ask_input=False):
                input("Failed to checkout to this branch... Press ENTER to continue")
            return
    write_error(f'No crate matches the repository `{repo_name}` apparently...')


def build_blog_post(repositories, temp_dir, token, args):
    # pylint: disable=too-many-locals,too-many-statements
    write_msg('=> Building blog post...')

    author = input('Enter author name: ')
    title = input('Enter title: ')
    blog_post_date = time.strftime("%Y-%m-%d %H:00:00 +0000")
    content = f'''---
layout: post
author: {author}
title: {title}
categories: [front, crates]
date: {blog_post_date}
---

* Write intro here *

### Changes

For the interested ones, here is the list of the merged pull requests:

'''
    contributors = []
    git = Github(token)
    oldest_date = None

    for repo in repositories:
        checkout_to_last_release_branch(repo, temp_dir)
        success, out, err = get_last_commit_date(repo, temp_dir)
        if not success:
            write_msg(f"Couldn't get PRs for '{repo}': {err}")
            continue
        max_date = datetime.date.fromtimestamp(int(out))
        if oldest_date is None or max_date < oldest_date:
            oldest_date = max_date
        write_msg(f"Gettings merged PRs from {repo}...")
        merged_prs = git.get_pulls(repo, consts.ORGANIZATION, 'closed', max_date, only_merged=True)
        write_msg(f"=> Got {len(merged_prs)} merged PRs")
        if len(merged_prs) < 1:
            continue
        repo_url = f'{consts.GITHUB_URL}/{consts.ORGANIZATION}/{repo}'
        content += f'[{repo}]({repo_url}):\n\n'
        content += write_merged_prs(merged_prs, contributors, repo_url)

    write_msg("Gettings merged PRs from gir...")
    merged_prs = git.get_pulls('gir', consts.ORGANIZATION, 'closed', oldest_date, only_merged=True)
    write_msg(f"=> Got {len(merged_prs)} merged PRs")
    if len(merged_prs) > 0:
        repo_url = f'{consts.GITHUB_URL}/{consts.ORGANIZATION}/gir'
        content += f'All this was possible thanks to the [gtk-rs/gir]({repo_url}) project as well:'
        content += '\n\n'
        content += write_merged_prs(merged_prs, contributors, repo_url)

    content += 'Thanks to all of our contributors for their (awesome!) work on this release:\n\n'
    # Sort contributors list alphabetically with case insensitive.
    contributors = sorted(contributors, key=lambda s: s.casefold())
    content += '\n'.join([f' * [@{contributor}]({consts.GITHUB_URL}/{contributor})'
                          for contributor in contributors])
    content += '\n'

    current_date = time.strftime("%Y-%m-%d")
    file_name = join(join(temp_dir, consts.BLOG_REPO), f'_posts/{current_date}-new-release.md')
    try:
        with open(file_name, 'w', encoding='utf-8') as outfile:
            outfile.write(content)
            write_msg(f'New blog post written into "{file_name}".')
        add_to_commit(consts.BLOG_REPO, temp_dir, [file_name])
        commit(consts.BLOG_REPO, temp_dir, "Add new blog post")
        if not args.no_push:
            branch_name = f"release-{current_date}"
            push(consts.BLOG_REPO, temp_dir, branch_name)
            create_pull_request(consts.BLOG_REPO, branch_name, "master", token)
    except Exception as err:
        write_error(f'build_blog_post failed: {err}')
        write_msg(f'\n=> Here is the blog post content:\n{content}\n<=')
    write_msg('Done!')


def shorter_version(version):
    return '.'.join(version.split('.')[:2]).replace('"', '')


def generate_new_branches(repository, temp_dir, specified_crate, args):
    # We make a new branch for every crate based on the current "crate" branch:
    #
    # * If it is a "sys" crate or a "macro" crate, then we ignore it.
    # * If not, then we create a new branch
    for crate in args.crates:
        crate = crate['crate']
        if crate['repository'] == repository:
            if specified_crate is not None and crate['crate'] != specified_crate:
                continue
            if (crate['crate'].endswith('-sys') or
                    crate['crate'].endswith('-sys-rs') or
                    "-macro" in crate['crate']):
                continue
            # We only keep major and medium version numbers, so "0.9.0" becomes "0.9".
            branch_name = shorter_version(CRATES_VERSION[crate['crate']])
            write_msg(f'==> Creating new branch "{branch_name}" for repository "{repository}"...')
            checkout_to_new_branch(repository, temp_dir, branch_name)
            return


def clone_repositories(args, temp_dir):
    write_msg('=> Cloning the repositories...')
    repositories = []
    for crate in args.crates:
        crate = crate['crate']
        if args.specified_crate is not None and crate['crate'] != args.specified_crate:
            continue
        if crate["repository"] not in repositories:
            repositories.append(crate["repository"])
            if clone_repo(crate["repository"], temp_dir) is False:
                write_error(f'Cannot clone the "{crate["repository"]}" repository...')
                return []
    if len(repositories) < 1:
        write_msg(f'No crate "{args.specified_crate}" found. Aborting...')
        return []
    if clone_repo(consts.BLOG_REPO, temp_dir, depth=1) is False:
        write_error(f'Cannot clone the "{consts.BLOG_REPO}" repository...')
        return []
    write_msg('Done!')
    return repositories


def update_crates_versions(args, temp_dir, repositories):
    if args.tags_only:
        return
    write_msg('=> Updating [master] crates version...')
    for repository in repositories:
        checkout_target_branch(repository, temp_dir, 'master')
    for crate in args.crates:
        update_type = crate['up-type']
        crate = crate['crate']
        if args.specified_crate is not None and crate['crate'] != args.specified_crate:
            continue
        if update_crate_version(crate["repository"], crate["path"], temp_dir, update_type) is False:
            write_error(f'The update for the "{crate["crate"]}" crate failed...')
            input('Press ENTER to continue...')
    write_msg('Done!')
    extra = " and pushing" if args.no_push is False else ""
    write_msg(f'=> Committing{extra} to the "{consts.MASTER_TMP_BRANCH}" branch...')
    for repo in repositories:
        commit(repo, temp_dir, "Update versions for next release [ci skip]")
        if args.no_push is False:
            push(repo, temp_dir, consts.MASTER_TMP_BRANCH)
    write_msg('Done!')

    if args.no_push is False:
        write_msg('=> Creating PRs on master branch...')
        for repo in repositories:
            create_pull_request(repo, consts.MASTER_TMP_BRANCH, "master", args.token)
        write_msg('Done!')


def publish_crates(args, temp_dir):
    write_msg('+++++++++++++++')
    write_msg('++ IMPORTANT ++')
    write_msg('+++++++++++++++')
    write_msg('Almost everything has been done.')
    input('Check the generated branches then press ENTER to continue...')
    write_msg('=> Publishing crates...')
    for crate in args.crates:
        crate = crate['crate']
        if args.specified_crate is not None and crate['crate'] != args.specified_crate:
            continue
        if not crate.get('ignore', False):
            publish_crate(crate['repository'], crate['path'], temp_dir, crate['crate'])
    write_msg('Done!')


def generate_version_branches(args, temp_dir, repositories):
    write_msg("=> Generating branches...")
    for repo in repositories:
        generate_new_branches(repo, temp_dir, args.specified_crate, args)
    write_msg('Done!')


def push_new_version_branches_and_tags(args, temp_dir, repositories):
    for repository in repositories:
        for crate in args.crates:
            crate = crate['crate']
            if (crate['repository'] != repository or
                crate['crate'].endswith('-sys') or
                crate['crate'].endswith('-sys-rs')):
                continue
            if args.tags_only is False:
                commit_and_push(
                    repository,
                    temp_dir,
                    'Update Cargo.toml format for release',
                    shorter_version(CRATES_VERSION[crate['crate']]))
            create_tag_and_push(
                CRATES_VERSION[crate['crate']],
                repository,
                temp_dir)
            break


def start(args, temp_dir):
    repositories = clone_repositories(args, temp_dir)
    if len(repositories) < 1:
        return
    get_all_versions(args, temp_dir)
    generate_version_branches(args, temp_dir, repositories)
    update_crates_cargo_file(args, temp_dir)
    if args.no_push is False:
        push_new_version_branches_and_tags(args, temp_dir, repositories)

    if args.tags_only is False:
        build_blog_post(repositories, temp_dir, args.token, args)
    if args.blog_only:
        input("Blog post generated, press ENTER to quit (it'll remove the tmp folder and "
              "its content!)")
        return

    if args.tags_only is False and args.no_push is False:
        publish_crates(args, temp_dir)

    update_crates_versions(args, temp_dir, repositories)

    write_msg("Everything is almost done now. Just need to merge the remaining pull requests...")
    pr_list = '\n'.join(PULL_REQUESTS)
    write_msg(f"\n{pr_list}\n")

    write_msg('Seems like most things are done! Now remains:')
    input(
        f'Press ENTER to leave (once done, the temporary directory "{temp_dir}" will be destroyed)')


def main(argv):
    args = Arguments.parse_arguments(argv)
    if args is None:
        sys.exit(1)
    if check_if_up_to_date() is False:
        return
    write_msg('=> Creating temporary directory...')
    with temporary_directory() as temp_dir:
        write_msg(f'Temporary directory created in "{temp_dir}"')
        start(args, temp_dir)


# Beginning of the script
if __name__ == "__main__":
    main(sys.argv[1:])
