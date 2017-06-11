#!/bin/python3

from contextlib import contextmanager
from os.path import join
from my_toml import TomlHandler
from utils import clone_repo, exec_command, get_file_content, post_content, write_error
from utils import write_into_file, write_msg
import consts
import errno
import getopt
import shutil
import subprocess
import sys
import tempfile
# pip3 install toml
import toml


CRATES_VERSION = {}


class UpdateType:
    MAJOR = 0
    MEDIUM = 1
    MINOR = 2

    def create_from_string(s):
        s = s.lower()
        if s == 'major':
            return UpdateType.MAJOR
        elif s == 'medium':
            return UpdateType.MEDIUM
        elif s == 'minor':
            return UpdateType.MINOR
        return None


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


def find_crate(crate_name):
    for entry in consts.CRATE_LIST:
        if entry['crate'] == crate_name:
            return True
    return False


def update_crate_version(repo_name, crate_name, crate_dir_path, temp_dir, update_type):
    file = join(join(join(temp_dir, repo_name), crate_dir_path), "Cargo.toml")
    output = file.replace(temp_dir, "")
    if output.startswith('/'):
        output = output[1:]
    write_msg('=> Updating versions for {}'.format(file))
    content = get_file_content(file)
    if content is None:
        return False
    toml = TomlHandler(content)
    versions_update = []
    for section in toml.sections:
        if (section.name == 'package' or
                (section.name.startswith('dependencies.') and find_crate(section.name[13:]))):
            version = sections.entries.get('version', None)
            if version is None:
                continue
            new_version = update_version(version, update_type, section.name)
            if new_version is None:
                return False
            # Print the status directly if it's the crate's version.
            if section.name == 'package':
                write_msg('{}: {} => {}'.format(output.split('/')[-2], version, new_version))
                CRATES_VERSION[crate_name] = new_version
            else:  # Otherwise add it to the list to print later.
                versions_update.append({'dependency_name': section.name[13:],
                                        'old_version': version,
                                        'new_version': new_version})
            section.entries['version'] = new_version
        elif section_name == 'dependencies':
            for entry in section.entries:
                if find_crate(entry):
                    new_version = check_and_update_version(section.entries[entry],
                                                           update_type,
                                                           entry)
                    section.entries[entry] = new_version
    for up in versions_update:
        write_msg('\t{}: {} => {}'.format(up['dependency_name'], up['old_version'],
                                          up['new_version']))
    result = write_into_file(file, "{}".format(toml))
    write_msg('=> {}: {}'.format(output.split('/')[-2],
                                 'Failure' if result is False else 'Success'))
    return result


def commit_and_push(repo_name, tmp_dir, commit_msg, target_branch):
    repo_path = join(temp_dir, repo_name)
    command = ['bash', '-c', 'cd {} && git commit . -m "{}"'.format(repo_path, commit_msg)]
    if not exec_command_and_print_error(command):
        input("Fix the error and then press ENTER")
    command = ['bash', '-c', 'cd {} && git push -f {}'.format(repo_path, target_branch)]
    if not exec_command_and_print_error(command):
        input("Fix the error and then press ENTER")


def checkout_target_branch(repo_name, tmp_dir, target_branch):
    repo_path = join(temp_dir, repo_name)
    command = ['bash', '-c', 'cd {} && git checkout "{}"'.format(repo_path, target_branch)]
    if not exec_command_and_print_error(command):
        input("Fix the error and then press ENTER")


def merging_branches(repo_name, tmp_dir, merge_branch):
    repo_path = join(temp_dir, repo_name)
    command = ['bash', '-c', 'cd {} && git merge "origin/{}"'.format(repo_path, merge_branch)]
    if not exec_command_and_print_error(command):
        input("Fix the error and then press ENTER")


def publish_crate(repository, crate_dir_path, temp_dir):
    path = join(join(temp_dir, repository), crate_dir_path)
    command = ['bash', '-c', 'cd {} && cargo publish'.format(path)]
    if not exec_command_and_print_error(command):
        input("Smething bad happened! Try to fix it and then press ENTER to continue...")


def create_pull_request(repo_name, from_branch, target_branch, token):
    r = post_content('{}/repos/{}/{}/pulls'.format(consts.GH_API_URL, consts.ORGANIZATION,
                                                   repo_name),
                     token,
                     {'title': '[release] merging {} into {}'.format(from_branch, target_branch),
                      'body': 'cc @GuillaumeGomez @EPashkin',
                      'base': target_branch,
                      'head': from_branch,
                      'maintainer_can_modify': 'true'})
    if r is None:
        write_error("Pull request from {repo}/{from_b} to {repo}/{target} couldn't be created. You "
                    "need to do it yourself...".format(repo=repo_name, from_b=from_branch,
                                            target=target_branch))
        input("Press ENTER once done to continue...")
    else:
        write_msg("Pull request created: {}".format(r['html_url']))


def update_badges(repo_name, temp_dir):
    path = join(join(temp_dir, repo_name), "_data/crates.json")
    content = get_file_content(path)
    current = None
    out = []
    for line in content.split("\n"):
        if line.strip().startswith('"name": "'):
            current = line.split('"name": "')[-1].replace('",', '')
        elif line.strip.startswith('"max_version": "') and current is not None:
            version = line.split('"max_version": "')[-1].replace('",', '')
            out.append(line.replace('": "{}",'.format(version),
                                    '": "{}",'.format(CRATES_VERSION[current])) + '\n')
            current = None
            continue
        out.append(line + '\n')
    return write_into_file(path, ''.join(out))


def start(update_type, token):
    write_msg('Creating temporary directory...')
    with TemporaryDirectory() as temp_dir:
        write_msg('Cloning the repositories...')
        repositories = []
        for crate in consts.CRATE_LIST:
            if crate["repository"] not in repositories:
                repositories.append(crate["repository"])
            if clone_repo(crate["repository"], temp_dir) is False:
                write_error('Cannot clone the "{}" repository...'.format(crate["repository"]))
                return
        write_msg('Done!')
        write_msg('Updating crates version...')
        for crate in consts.CRATE_LIST:
            if update_crate_version(crate["repository"], crate["name"], crate["path"], temp_dir,
                                    update_type) is False:
                write_error('The update for the "{}" repository failed...'.format(crate["name"]))
                return
        write_msg('Done!')
        write_msg('Committing and pushing to the "{}" branch...'.format(consts.MASTER_TMP_BRANCH))
        for repo in repositories:
            commit_and_push(repo, temp_dir, "Update versions", consts.MASTER_TMP_BRANCH)
        write_msg('Done!')
        for repo in repositories:
            create_pull_request(repo, consts.MASTER_TMP_BRANCH, "master")
        write_msg('Checking out "crate" branches')
        for repo in repositories:
            checkout_target_branch(repo, temp_dir, "crate")
        write_msg('Done!')
        write_msg('Merging "master" branches into "crate" branches...')
        for crate in repositories:
            merging_branches(repo, temp_dir, "master")
        write_msg('Done!')
        write_msg('Committing and pushing to the "{}" branch...'.format(consts.CRATE_TMP_BRANCH))
        for repo in repositories:
            commit_and_push(repo, temp_dir, "Update versions", consts.CRATE_TMP_BRANCH)
        write_msg('Done!')
        for repo in repositories:
            create_pull_request(repo, consts.CRATE_TMP_BRANCH, "crate", token)
        write_msg('+++++++++++++++')
        write_msg('++ IMPORTANT ++')
        write_msg('+++++++++++++++')
        write_msg('Almost everything has been done. Take a deep breath, check for opened pull '
                  'requests and once done, we can move forward!')
        input('Press ENTER to continue...')
        write_msg('Publishing crates...')
        for repo in consts.CRATE_LIST:
            publish_crate(crate["repository"], crate["path"], temp_dir)
        write_msg('Done!')
        # write_msg('Getting pull requests since last release to create the blog post...')
        # TODO: Get all pull requests since the last release in order to create the blog post about
        #       the release.
        # write_msg('And done!')
        write_msg('Updating docs...')
        if clone_repo(consts.DOC_REPO, temp_dir) is False:
            write_error('Cannot clone the "{}" repository...'.format(consts.DOC_REPO))
        else:
            if update_badges(consts.DOC_REPO, temp_dir) is False:
                write_error("Error when trying to update badges...")
            else:
                commit_and_push(consts.DOC_REPO, temp_dir, "Update versions",
                                consts.MASTER_TMP_BRANCH)
                create_pull_request(consts.DOC_REPO, consts.MASTER_TMP_BRANCH, "master", token)
        write_msg('Seems like most things are done! Now remains:')
        write_msg(" * Generate docs for all crates (don't forget to enable features!).")
        write_msg(" * Write blog post.")
        input('Press ENTER to leave (once done, the temporary directory "{}" will be destroyed)'
              .format(temp_dir))


def write_help():
    write_msg("release.py accepts the following options:")
    write_msg("")
    write_msg(" * -h | --help                  : display this message")
    write_msg(" * -t <token> | --token=<token> : give the github token")
    write_msg(" * -m <mode> | --mode=<mode>    : give the update type (MINOR|MEDIUM|MAJOR)")


def main(argv):
    try:
        opts, args = getopt.getopt(argv, "ht:m:", ["help", "token=", "mode="])
    except getopt.GetoptError:
        write_help()
        sys.exit(2)

    token = None
    mode = None
    for opt, arg in opts:
        if opt in ('-h', '--help'):
            write_help()
            sys.exit(0)
        elif opt in ("-t", "--token"):
            token = arg
        elif opt in ("-m", "--mode"):
            mode = UpdateType.create_from_string(arg)
            if mode is None:
                write_error('{}: Invalid update type received. Accepted values: (MINOR|MEDIUM|MAJOR)'
                            .format(opt))
                sys.exit(3)
    if token is None:
        write_error('Missing token argument.')
        sys.exit(4)
    if mode is None:
        write_error('Missing update type argument.')
        sys.exit(5)
    start(mode, token)

# Beginning of the script
if __name__ != "__main__":
    write_error('This file should be launched as main file.')
    sys.exit(1)
else:
    main(sys.argv[1:])
