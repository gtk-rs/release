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
from os.path import join

# local imports
import consts
from args import Arguments, UpdateType
from github import Github
from globals import CRATES_VERSION, PULL_REQUESTS
from my_toml import TomlHandler
from utils import add_to_commit, clone_repo
from utils import checkout_target_branch, get_file_content, write_error, write_into_file
from utils import commit, commit_and_push, create_pull_request, push, write_msg
from utils import create_tag_and_push, publish_crate#, get_last_commit_date
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
        write_error('Invalid version in {} "{}": {}'.format(place_type, section_name, version))
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
    return '"{}"'.format('.'.join(version_split))


def check_and_update_version(entry, update_type, dependency_name, versions_update):
    if entry.startswith('"') or entry.startswith("'"):
        return update_version(entry, update_type, dependency_name, place_type="dependency")
    # get version and update it
    entry = [e.strip() for e in entry.split(',')]
    dic = {}
    for part in entry:
        if part.startswith('{'):
            part = part[1:].strip()
        if part.endswith('}'):
            part = part[:-1].strip()
        part = [p.strip() for p in part.split('=')]
        dic[part[0]] = part[1]
        if part[0] == 'version':
            old_version = part[1]
            new_version = update_version(old_version, update_type, dependency_name,
                                         place_type="dependency")
            if new_version is None:
                return None
            # Mostly for debugging, not really useful otherwise...
            versions_update.append({'dependency_name': dependency_name,
                                    'old_version': old_version,
                                    'new_version': new_version})
            dic[part[0]] = '"{}"'.format(new_version)
    return '{{{}}}'.format(', '.join(['{} = {}'.format(entry, dic[entry]) for entry in dic]))


def find_crate(crate_name):
    for entry in consts.CRATE_LIST:
        if entry['crate'] == crate_name:
            return True
    return False


def update_crate_version(repo_name, crate_name, crate_dir_path, temp_dir, specified_crate):
    file_path = join(join(join(temp_dir, repo_name), crate_dir_path), "Cargo.toml")
    output = file_path.replace(temp_dir, "")
    if output.startswith('/'):
        output = output[1:]
    write_msg('=> Updating crate versions for {}'.format(file_path))
    content = get_file_content(file_path)
    if content is None:
        return False
    toml = TomlHandler(content)
    for section in toml.sections:
        if section.name == 'package':
            section.set('version', CRATES_VERSION[crate_name])
        elif specified_crate is not None:
            continue
        elif section.name.startswith('dependencies.') and find_crate(section.name[13:]):
            if specified_crate is None and section.name[13:] not in CRATES_VERSION:
                input('"{}" dependency not found in versions for crate "{}"...'
                      .format(section.name[13:], crate_name))
                continue
            section.set('version', CRATES_VERSION[section.name[13:]])
        elif section.name == 'dependencies':
            for entry in section.entries:
                if find_crate(entry['key']):
                    section.set(entry['key'], CRATES_VERSION[entry['key']])
    result = write_into_file(file_path, str(toml))
    write_msg('=> {}: {}'.format(output.split(os_sep)[-2],
                                 'Failure' if result is False else 'Success'))
    return result


def get_all_versions(args, temp_dir):
    write_msg('=> Getting crates version...')
    for crate in args.crates:
        crate = crate['crate']
        if args.specified_crate is not None and crate['crate'] != args.specified_crate:
            continue
        if not get_crate_version(crate["repository"], crate["crate"], crate["path"], temp_dir):
            input("Couldn't find version for in `{}`...".format(join(temp_dir, crate['path'])))
    write_msg('Done!')


def get_crate_version(repo_name, crate_name, crate_dir_path, temp_dir):
    file_path = join(join(join(temp_dir, repo_name), crate_dir_path), "Cargo.toml")
    output = file_path.replace(temp_dir, "")
    if output.startswith('/'):
        output = output[1:]
    write_msg('=> Updating versions for {}'.format(file_path))
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


def update_crates_cargo_file(args, temp_dir):
    for crate in args.crates:
        crate = crate['crate']
        update_crate_cargo_file(crate["repository"], crate["path"], temp_dir)


def update_crate_cargo_file(repo_name, crate_dir_path, temp_dir):
    file_path = join(join(join(temp_dir, repo_name), crate_dir_path), "Cargo.toml")
    output = file_path.replace(temp_dir, "")
    if output.startswith('/'):
        output = output[1:]
    write_msg('=> Updating versions for {}'.format(file_path))
    content = get_file_content(file_path)
    if content is None:
        return False
    toml = TomlHandler(content)
    for section in toml.sections:
        if section.name.startswith('dependencies.') and find_crate(section.name[13:]):
            section.clear()
            section.set('version', CRATES_VERSION[section.name[13:]])
        elif section.name == 'dependencies':
            for entry in section.entries:
                if find_crate(entry):
                    section.set(entry, CRATES_VERSION[entry])
    out = str(toml)
    if not out.endswith("\n"):
        out += '\n'
    result = True
    result = write_into_file(file_path, out)
    write_msg('=> {}: {}'.format(
        output.split(os_sep)[-2],
        'Failure' if result is False else 'Success'))
    return result


def update_repo_version(repo_name, crate_name, crate_dir_path, temp_dir, update_type, no_update):
    # pylint: disable=too-many-branches,too-many-locals
    file_path = join(join(join(temp_dir, repo_name), crate_dir_path), "Cargo.toml")
    output = file_path.replace(temp_dir, "")
    if output.startswith('/'):
        output = output[1:]
    write_msg('=> Updating versions for {}'.format(file_path))
    content = get_file_content(file_path)
    if content is None:
        return False
    toml = TomlHandler(content)
    versions_update = []
    for section in toml.sections:
        if (section.name == 'package' or
                (section.name.startswith('dependencies.') and find_crate(section.name[13:]))):
            version = section.get('version', None)
            if version is None:
                continue
            new_version = None
            if no_update is False:
                new_version = update_version(version, update_type, section.name)
            else:
                new_version = version
            if new_version is None:
                return False
            # Print the status directly if it's the crate's version.
            if section.name == 'package':
                write_msg('\t{}: {} => {}'.format(output.split(os_sep)[-2], version, new_version))
                CRATES_VERSION[crate_name] = new_version
            else:  # Otherwise add it to the list to print later.
                versions_update.append({'dependency_name': section.name[13:],
                                        'old_version': version,
                                        'new_version': new_version})
            section.set('version', new_version)
        elif section.name == 'dependencies':
            for entry in section.entries:
                if find_crate(entry):
                    new_version = check_and_update_version(section.entries[entry],
                                                           update_type,
                                                           entry,
                                                           [])
                    section.set(entry, new_version)
    for update in versions_update:
        write_msg('\t{}: {} => {}'.format(update['dependency_name'],
                                          update['old_version'],
                                          update['new_version']))
    out = str(toml)
    if not out.endswith("\n"):
        out += '\n'
    result = True
    if no_update is False:
        # We only write into the file if we're not just getting the crates version.
        result = write_into_file(file_path, out)
        write_msg('=> {}: {}'.format(output.split(os_sep)[-2],
                                     'Failure' if result is False else 'Success'))
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
        content += ' * [{}]({}/pull/{})\n'.format(md_content, repo_url, merged_pr.number)
    return content + '\n'


def build_blog_post(repositories, temp_dir, token, args):
    # pylint: disable=too-many-locals,too-many-statements
    write_msg('=> Building blog post...')

    content = '''---
layout: post
author: {}
title: {}
categories: [front, crates]
date: {}
---

* Write intro here *

### Changes

For the interested ones, here is the list of the merged pull requests:

'''.format(input('Enter author name: '), input('Enter title: '),
           time.strftime("%Y-%m-%d %H:00:00 +0000"))
    contributors = []
    git = Github(token)
    # oldest_date = None
    # pylint: disable=fixme
    # TODO: To be removed once this release is done.
    oldest_date = datetime.datetime(2020, 8, 26)

    for repo in repositories:
        # checkout_target_branch(repo, temp_dir, "crate")
        # success, out, err = get_last_commit_date(repo, temp_dir)
        # if not success:
        #     write_msg("Couldn't get PRs for '{}': {}".format(repo, err))
        #     continue
        # max_date = datetime.date.fromtimestamp(int(out))
        # if oldest_date is None or max_date < oldest_date:
        #     oldest_date = max_date
        # pylint: disable=fixme
        max_date = oldest_date # TODO: To be removed once this release is done.
        write_msg("Gettings merged PRs from {}...".format(repo))
        merged_prs = git.get_pulls(repo, consts.ORGANIZATION, 'closed', max_date, only_merged=True)
        write_msg("=> Got {} merged PRs".format(len(merged_prs)))
        if len(merged_prs) < 1:
            continue
        repo_url = '{}/{}/{}'.format(consts.GITHUB_URL, consts.ORGANIZATION, repo)
        content += '[{}]({}):\n\n'.format(repo, repo_url)
        content += write_merged_prs(merged_prs, contributors, repo_url)

    # pylint: disable=fixme
    # TODO: To be removed after this release
    for repo in consts.OLD_REPO:
        write_msg("Gettings merged PRs from {}...".format(repo))
        merged_prs = git.get_pulls(repo, consts.ORGANIZATION, 'closed', max_date, only_merged=True)
        write_msg("=> Got {} merged PRs".format(len(merged_prs)))
        if len(merged_prs) < 1:
            continue
        for crate in args.crates:
            crate = crate['crate']
            if crate['crate'] == crate:
                repo_url = '{}/{}/{}'.format(
                    consts.GITHUB_URL,
                    consts.ORGANIZATION,
                    crate['repository'])
                content += '[{}]({}):\n\n'.format(repo, repo_url)
                content += write_merged_prs(merged_prs, contributors, repo_url)

    write_msg("Gettings merged PRs from gir...")
    merged_prs = git.get_pulls('gir', consts.ORGANIZATION, 'closed', oldest_date, only_merged=True)
    write_msg("=> Got {} merged PRs".format(len(merged_prs)))
    if len(merged_prs) > 0:
        repo_url = '{}/{}/{}'.format(consts.GITHUB_URL, consts.ORGANIZATION, 'gir')
        content += ('All this was possible thanks to the [gtk-rs/gir]({}) project as well:\n\n'
                    .format(repo_url))
        content += write_merged_prs(merged_prs, contributors, repo_url)

    content += 'Thanks to all of our contributors for their (awesome!) work on this release:\n\n'
    # Sort contributors list alphabetically with case insensitive.
    contributors = sorted(contributors, key=lambda s: s.casefold())
    content += '\n'.join([' * [@{0}]({1}/{0})'.format(contributor, consts.GITHUB_URL)
                          for contributor in contributors])
    content += '\n'

    file_name = join(join(temp_dir, consts.BLOG_REPO),
                     '_posts/{}-new-release.md'.format(time.strftime("%Y-%m-%d")))
    try:
        with open(file_name, 'w') as outfile:
            outfile.write(content)
            write_msg('New blog post written into "{}".'.format(file_name))
        add_to_commit(consts.BLOG_REPO, temp_dir, [file_name])
        commit(consts.BLOG_REPO, temp_dir, "Add new blog post")
        if not args.no_push:
            branch_name = "release-{}".format(time.strftime("%Y-%m-%d"))
            push(consts.BLOG_REPO, temp_dir, branch_name)
            create_pull_request(consts.BLOG_REPO, branch_name, "master", token)
    except Exception as err:
        write_error('build_blog_post failed: {}'.format(err))
        write_msg('\n=> Here is the blog post content:\n{}\n<='.format(content))
    write_msg('Done!')


def generate_new_tag(repository, temp_dir, specified_crate, args):
    # We make a new tag for every crate:
    #
    # * If it is a "sys" crate, then we add its name to the tag
    # * If not, then we just keep its version number
    for crate in args.crates:
        crate = crate['crate']
        if crate['repository'] == repository:
            if specified_crate is not None and crate['crate'] != specified_crate:
                continue
            tag_name = CRATES_VERSION[crate['crate']]
            if crate['crate'].endswith('-sys') or crate['crate'].endswith('-sys-rs'):
                tag_name = '{}-{}'.format(crate['crate'], tag_name)
            write_msg('==> Creating new tag "{}" for repository "{}"...'.format(tag_name,
                                                                                repository))
            create_tag_and_push(tag_name, repository, temp_dir)


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
            write_msg('==> Creating new branch "{}" for repository "{}"...'.format(branch_name,
                                                                                   repository))
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
                write_error('Cannot clone the "{}" repository...'.format(crate["repository"]))
                return []
    if len(repositories) < 1:
        write_msg('No crate "{}" found. Aborting...'.format(args.specified_crate))
        return []
    if clone_repo(consts.BLOG_REPO, temp_dir, depth=1) is False:
        write_error('Cannot clone the "{}" repository...'.format(consts.BLOG_REPO))
        return []
    write_msg('Done!')
    return repositories


def update_crates_versions(args, temp_dir, repositories):
    write_msg('=> Updating [master] crates version...')
    for repository in repositories:
        checkout_target_branch(repository, temp_dir, 'master')
    for crate in args.crates:
        update_type = crate['up-type']
        crate = crate['crate']
        if args.specified_crate is not None and crate['crate'] != args.specified_crate:
            continue
        if update_repo_version(crate["repository"], crate["crate"], crate["path"],
                               temp_dir, update_type,
                               args.tags_only) is False:
            write_error('The update for the "{}" crate failed...'.format(crate["crate"]))
            return False
    write_msg('Done!')
    if args.tags_only is False:
        write_msg('=> Committing{} to the "{}" branch...'
                  .format(" and pushing" if args.no_push is False else "",
                          consts.MASTER_TMP_BRANCH))
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
    return True


def publish_crates(args, temp_dir):
    write_msg('+++++++++++++++')
    write_msg('++ IMPORTANT ++')
    write_msg('+++++++++++++++')
    write_msg('Almost everything has been done.')
    write_msg('=> Publishing crates...')
    for crate in args.crates:
        crate = crate['crate']
        if args.specified_crate is not None and crate['crate'] != args.specified_crate:
            continue
        publish_crate(crate["repository"], crate["path"], temp_dir, crate['crate'])
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
            if crate['repository'] == repository:
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

    if update_crates_versions(args, temp_dir, repositories) is False:
        return

    write_msg("Everything is almost done now. Just need to merge the remaining pull requests...")
    write_msg("\n{}\n".format('\n'.join(PULL_REQUESTS)))

    write_msg('Seems like most things are done! Now remains:')
    input('Press ENTER to leave (once done, the temporary directory "{}" will be destroyed)'
          .format(temp_dir))


def main(argv):
    args = Arguments.parse_arguments(argv)
    if args is None:
        sys.exit(1)
    if check_if_up_to_date() is False:
        return
    write_msg('=> Creating temporary directory...')
    with temporary_directory() as temp_dir:
        write_msg('Temporary directory created in "{}"'.format(temp_dir))
        start(args, temp_dir)


# Beginning of the script
if __name__ == "__main__":
    main(sys.argv[1:])
