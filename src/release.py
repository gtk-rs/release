#!/bin/python3

from contextlib import contextmanager
from os.path import join
from toml import TomlHandler
from utils import exec_command, get_file_content, write_error, write_into_file, write_msg
import errno
import shutil
import subprocess
import sys
import tempfile
import toml


ORGANIZATION = "gtk-rs"
REPOSITORY_LIST = ["sys", "glib", "gio", "cairo", "pango", "gdk-pixbuf", "gdk", "gtk"]
GITHUB_URL = "https://github.com"
CRATE_LIST = ["cairo-rs", "cairo-sys-rs", "gdk", "gdk-sys", "gdk-pixbuf", "gdk-pixbuf-sys", "gio",
              "gio-sys", "glib", "glib-sys", "gobject-sys", "gtk", "gtk-sys", "pango", "pango-sys"]
MASTER_TMP_BRANCH = "master-release-update"
CRATE_TMP_BRANCH = "crate-release-update"


class UpdateType:
    MAJOR = 0
    MEDIUM = 1
    MINOR = 2


@contextmanager
def TemporaryDirectory():
    name = tempfile.mkdtemp()
    try:
        yield name
    finally:
        try:
            shutil.rmtree(name)
        except OSError as e:
            # if the directory has already been removed, no need to raise an error
            if e.errno != errno.ENOENT:
                raise


def update_version(version, update_type, section_name, place_type="section"):
    version_split = version.split('.')
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
        done = False
        for pos in version_split[update_type]:
            try:
                int(version_split[update_type][pos])
            except Exception:
                continue
            version_split[update_type] = '{}{}'.format(version_split[update_type][:pos],
                                                       int(version_split[update_type]) + 1)
            version_split[UpdateType.MEDIUM] = '0'
            version_split[UpdateType.MINOR] = '0'
            done = True
            break
        if done is False:
            write_error('Invalid version in {} "{}": {}'.format(place_type, section_name, version))
            return None
    return '.'.join(version_split)


def check_and_update_version(entry, update_type, dependency_name, versions_update):
    if entry.startswith('"') or entry.startswith("'"):
        return update_version(entry, update_type, dependency_name, place_type="dependency")
    # get version and update it
    dic = {}
    try:
        dic = toml.loads('{} = {}\n'.format(dependency_name, entry))
    except Exception as e:
        write_error('Invalid toml for "{}": "{}". Got error: {}'.format(dependency_name, entry, e))
        return None
    for entry in dic:
        if entry == 'version':
            old_version = dic[entry]
            new_version = update_version(old_version, update_type, dependency_name,
                                         place_type="dependency")
            if new_version is None:
                return None
            versions_update.append({'dependency_name': dependency_name,
                                    'old_version': old_version,
                                    'new_version': new_version})
            dic[entry] = new_version
            break
    return '{{{}}}'.format(', '.join(['{} = {}'.format(entry, dic[entry]) for entry in dic]))



def update_crate_version(repo_name, temp_dir, update_type):
    files = get_all_files('Cargo.toml', join(repo_name, temp_dir))
    result = True
    for file in files:
        output = file.replace(join(repo_name, temp_dir), '')
        if output.startswith('/'):
            output = output[1:]
        write_msg('=> Updating versions for {}'.format(output))
        content = get_file_content(output)
        if content is None:
            return False
        toml = TomlHandler(content)
        versions_update = []
        for section in toml.sections:
            if section.name == 'package' or
               (section.name.startswith('dependencies.') and section.name[13:] in CRATE_LIST):
                version = sections.entries.get('version', None)
                if version is None:
                    continue
                new_version = update_version(version, update_type, section.name)
                if new_version is None:
                    return False
                # Print the status directly if it's the crate's version.
                if section.name == 'package':
                    write_msg('{}: {} => {}'.format(output.split('/')[-2], version, new_version))
                else:  # Otherwise add it to the list to print later.
                    versions_update.append({'dependency_name': section.name[13:],
                                            'old_version': version,
                                            'new_version': new_version})
                section.entries['version'] = new_version
            elif section_name == 'dependencies':
                for entry in section.entries:
                    if entry in CRATE_LIST:
                        new_version = check_and_update_version(section.entries[entry],
                                                               update_type,
                                                               entry)
                        section.entries[entry] = new_version
        for up in versions_update:
            write_msg('\t{}: {} => {}'.format(up['dependency_name'], up['old_version'],
                                              up['new_version']))
        tmp_result = write_into_file(output, "{}".format(toml))
        write_msg('=> {}: {}'.format(output.split('/')[-2],
                                     'Failure' if tmp_result is False else 'Success'))
        result = result and tmp_result
    return result


def commit_and_push(repo_name, tmp_dir, commit_msg, target_branch):
    repo_path = join(repo_name, temp_dir)
    command = ['bash', '-c', 'cd {} && git commit . -m "{}"'.format(repo_path, commit_msg)]
    if not exec_command_and_print_error(command):
        input("Fix the error and then press ENTER")
    command = ['bash', '-c', 'cd {} && git push -f {}'.format(repo_path, target_branch)]
    if not exec_command_and_print_error(command):
        input("Fix the error and then press ENTER")


def checkout_target_branch(repo_name, tmp_dir, target_branch):
    repo_path = join(repo_name, temp_dir)
    command = ['bash', '-c', 'cd {} && git checkout "{}"'.format(repo_path, target_branch)]
    if not exec_command_and_print_error(command):
        input("Fix the error and then press ENTER")


def merging_branches(repo_name, tmp_dir, merge_branch):
    repo_path = join(repo_name, temp_dir)
    command = ['bash', '-c', 'cd {} && git merge "origin/{}"'.format(repo_path, merge_branch)]
    if not exec_command_and_print_error(command):
        input("Fix the error and then press ENTER")


def start(update_type):
    write_msg('Creating temporary directory...')
    with TemporaryDirectory() as temp_dir:
        write_msg('Cloning the repositories...')
        for repo in REPOSITORY_LIST:
            if clone_repo(repo, temp_dir) is False:
                write_error('Cannot clone the "{}" repository...'.format(repo))
                return
        write_msg('Done!')
        write_msg('Updating crates version...')
        for repo in REPOSITORY_LIST:
            if update_crate_version(repo, temp_dir, update_type) is False:
                write_error('The update for the "{}" repository failed...'.format(repo))
                return
        write_msg('Done!')
        write_msg('Committing and pushing to the "{}" branch...'.format(MASTER_TMP_BRANCH))
        for repo in REPOSITORY_LIST:
            commit_and_push(repo, temp_dir, "Update versions", MASTER_TMP_BRANCH)
        write_msg('Done!')
        # TODO: create pull request in here from the branch to master!
        write_msg('Checking out "crate" branches')
        for repo in REPOSITORY_LIST:
            checkout_target_branch(repo, temp_dir, "crate")
        write_msg('Done!')
        write_msg('Merging "master" branches into "crate" branches...')
        for crate in REPOSITORY_LIST:
            merging_branches(repo, temp_dir, "master")
        write_msg('Done!')
        write_msg('Committing and pushing to the "{}" branch...'.format(CRATE_TMP_BRANCH))
        for repo in REPOSITORY_LIST:
            commit_and_push(repo, temp_dir, "Update versions", CRATE_TMP_BRANCH)
        # TODO: create pull request in here from the branch to crate!
        write_msg('+++++++++++++++')
        write_msg('++ IMPORTANT ++')
        write_msg('+++++++++++++++')
        write_msg('Almost everything has been done. Take a deep breath, check for opened pull '
                  'requests and once done, we can move forward!')
        input('Press ENTER to continue...')
        write_msg('Publishing crates...')
        for repo in REPOSITORY_LIST:
            # TODO: in here, we can't do it however we want. I need to write a dependency tree!
            publish_crate(repo, temp_dir)
        write_msg('Done!')
        write_msg('Getting pull requests since last release to create the blog post...')
        # TODO: Get all pull requests since the last release in order to create the blog post about
        #       the release.
        write_msg('And done!')
        input('Press ENTER to leave (once done, the temporary directory "{}" will be destroyed)'
              .format(temp_dir))


if __name__ != "__main__":
    write_error('This file should be launched as main file.')
    sys.exit(1)
# Add update type: minor, medium, major
start(UpdateType.MINOR)
