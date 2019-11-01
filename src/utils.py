from os.path import join
from my_toml import TomlHandler
import json
import subprocess
import sys
import time
# pip3 install requests
import requests
# local i;port
import consts


def write_error(error_msg):
    sys.stderr.write('{}\n'.format(error_msg))


def write_msg(msg):
    sys.stdout.write('{}\n'.format(msg))


def convert_to_string(s):
    if s.__class__.__name__ == 'bytes':
        return s.decode('utf-8')
    return s


def get_file_content(file_path):
    try:
        with open(file_path, 'r') as fd:
            return fd.read()
    except Exception as e:
        write_error('get_file_content failed: "{}": {}'.format(file_path, e))
    return None


def write_into_file(file_path, content):
    try:
        with open(file_path, 'w') as fd:
            fd.write(content)
            return True
    except Exception as e:
        write_error('write_into_file failed: "{}": {}'.format(file_path, e))
    return False


def exec_command(command, timeout=None):
    child = subprocess.Popen(command, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
    stdout, stderr = child.communicate(timeout=timeout)
    return (child.returncode == 0,
            convert_to_string(stdout),
            convert_to_string(stderr))


def exec_command_and_print_error(command, timeout=None):
    ret, stdout, stderr = exec_command(command, timeout=timeout)
    if not ret:
        write_error('Command "{}" failed:'.format(' '.join(command)))
        if len(stdout) > 0:
            write_error('=== STDOUT ===\n{}\n'.format(stdout))
        if len(stderr) > 0:
            write_error('=== STDERR ===\n{}\n'.format(stderr))
    return ret


def clone_repo(repo_name, temp_dir, depth=None):
    repo_url = '{}/{}/{}'.format(consts.GITHUB_URL, consts.ORGANIZATION, repo_name)
    target_dir = join(temp_dir, repo_name)
    try:
        write_msg('=> Cloning "{}" from "{}"'.format(repo_name, repo_url))
        command = ['git', 'clone', repo_url, target_dir]
        if depth is not None:
            command = ['git', 'clone', '--depth', '{}'.format(depth), repo_url, target_dir]
        ret, stdout, stderr = exec_command(command, timeout=300)
        if not ret:
            write_error('command "{}" failed: {}'.format(' '.join(command), stderr))
            return False
        return True
    except subprocess.TimeoutExpired:
        write_error('command timed out: {}'.format(' '.join(command)))
    except Exception as ex:
        write_error('command "{}" got an exception: {}'.format(' '.join(command), ex))
    return False


def create_headers(token):
    headers = {
        'User-Agent': 'gtk-rs',
        'Accept': 'application/vnd.github.v3+json',
    }
    if token is not None:
        # Authentication to github.
        headers['Authorization'] = 'token {}'.format(token)
    return headers


def post_content(url, token, details, method='post', header_extras={}):
    headers = create_headers(token)
    for extra in header_extras:
        headers[extra] = header_extras[extra]
    try:
        r = None
        if method == 'post':
            r = requests.post(url, data=json.dumps(details), headers=headers)
        else:
            r = requests.put(url, data=json.dumps(details), headers=headers)
        try:
            r.raise_for_status()
        except Exception:
            write_msg('Sent by bithub api: {}'.format(r.json()))
            r.raise_for_status()
        return r.json()
    except Exception as e:
        write_error('post_content: An error occurred: {}'.format(e))
    return None


def get_highest_feature_version(v1, v2):
    t_v1 = v1[1:].split('_')
    t_v2 = v2[1:].split('_')
    i = 0
    while i < len(t_v1) and i < len(t_v2):
        try:
            x1 = int(t_v1[i])
            x2 = int(t_v2[i])
            if x1 > x2:
                return v1
            elif x1 < x2:
                return v2
            i += 1
        except Exception:
            write_error('get_highest_feature_version int conversion error: int("{}") vs int("{}")'
                        ' from "{}" and "{}"'.format(t_v1[i], t_v2[i], v1, v2))
            break
    return v1


# This function does two things:
#
# 1. Check if dox feature is present or try getting the highest version feature
# 2. Getting all the other features (for cairo it's very important)
def get_features(path):
    features = []
    highest_version = None
    content = get_file_content(path)
    if content is None:
        return ''
    toml = TomlHandler(content)
    dox_present = False
    for section in toml.sections:
        if section.name == 'features':
            for entry in section.entries:
                if entry['key'] in ['purge-lgpl-docs', 'default']:
                    continue
                if entry['key'] == 'dox':
                    dox_present = True
                if entry['key'].startswith('v'):
                    if highest_version is None:
                        highest_version = entry['key']
                    else:
                        highest_version = get_highest_feature_version(highest_version, entry['key'])
                else:
                    features.append(entry['key'])
    if dox_present is True:
        if 'dox' not in features:
            features.append('dox')
    elif highest_version is not None:
        write_msg("/!\\ Seems there is no dox feature so let's just use the highest version "
                  "instead...")
        features.append(highest_version)
    else:
        write_msg("/!\\ That's weird: no dox or version feature. Is everything fine with this one?")
    return ' '.join(features)


def compare_versions(v1, v2):
    v1 = v1.split('.')
    v2 = v2.split('.')

    for x in range(0, min(len(v1), len(v2))):
        try:
            entry1 = int(v1)
            entry2 = int(v2)
        except Exception:
            # If it cannot be converted into a number, better just compare strings then.
            entry1 = v1
            entry2 = v2
        if entry1 > entry2:
            return 1
        if entry1 < entry2:
            return -1
    # In here, "3.2" is considered littler than "3.2.0". That's how life goes.
    return len(v1) - len(v2)


def commit_and_push(repo_name, temp_dir, commit_msg, target_branch):
    commit(repo_name, temp_dir, commit_msg)
    push(repo_name, temp_dir, target_branch)


def commit(repo_name, temp_dir, commit_msg):
    repo_path = join(temp_dir, repo_name)
    command = ['bash', '-c', 'cd {} && git commit . -m "{}"'.format(repo_path, commit_msg)]
    if not exec_command_and_print_error(command):
        input("Fix the error and then press ENTER")


def push(repo_name, temp_dir, target_branch):
    repo_path = join(temp_dir, repo_name)
    command = ['bash', '-c', 'cd {} && git push origin HEAD:{}'.format(repo_path, target_branch)]
    if not exec_command_and_print_error(command):
        input("Fix the error and then press ENTER")


def add_to_commit(repo_name, temp_dir, files_to_add):
    repo_path = join(temp_dir, repo_name)
    command = ['bash', '-c', 'cd {} && git add {}'
               .format(repo_path, ' '.join(['"{}"'.format(f) for f in files_to_add]))]
    if not exec_command_and_print_error(command):
        input("Fix the error and then press ENTER")


def revert_changes(repo_name, temp_dir, files):
    repo_path = join(temp_dir, repo_name)
    command = ['bash', '-c',
               'cd {} && git checkout -- {}'.format(repo_path,
                                                    ' '.join(['"{}"'.format(f) for f in files]))]
    if not exec_command_and_print_error(command):
        input("Fix the error and then press ENTER")


def checkout_target_branch(repo_name, temp_dir, target_branch):
    repo_path = join(temp_dir, repo_name)
    command = ['bash', '-c', 'cd {} && git checkout {}'.format(repo_path, target_branch)]
    if not exec_command_and_print_error(command):
        input("Fix the error and then press ENTER")


def get_last_commit_date(repo_name, temp_dir):
    repo_path = join(temp_dir, repo_name)
    success, out, err = exec_command(['bash', '-c',
                                      'cd {} && git log --format=%at --no-merges -n 1'.format(
                                          repo_path)
                                      ])
    return (success, out, err)


def merging_branches(repo_name, temp_dir, merge_branch):
    repo_path = join(temp_dir, repo_name)
    command = ['bash', '-c', 'cd {} && git merge "origin/{}"'.format(repo_path, merge_branch)]
    if not exec_command_and_print_error(command):
        input("Fix the error and then press ENTER")


def publish_crate(repository, crate_dir_path, temp_dir, crate_name, checkout_branch='crate'):
    write_msg('=> publishing crate {}'.format(crate_name))
    path = join(join(temp_dir, repository), crate_dir_path)
    # In case we needed to fix bugs, we checkout to crate branch before publishing crate.
    command = ['bash', '-c', 'cd {} && git checkout {} && cargo publish'.format(path,
                                                                                checkout_branch)]
    retry = 3
    error_messages = []
    final_success = False
    wait_time = 30
    while retry > 0:
        ret, stdout, stderr = exec_command(command)
        if not ret:
            error_messages.append('Command "{}" failed:'.format(' '.join(command)))
            if len(stdout) > 0:
                error_messages[len(error_messages) - 1] += '\n=== STDOUT ===\n{}\n'.format(stdout)
            if len(stderr) > 0:
                error_messages[len(error_messages) - 1] += '\n=== STDERR ===\n{}\n'.format(stderr)
            retry -= 1
            if retry > 0:
                write_msg("Let's sleep for {} seconds before retrying, {} retr{} remaining..."
                          .format(wait_time, retry + 1, 'ies' if retry > 0 else 'y'))
                time.sleep(wait_time)
        else:
            final_success = True
            break
        if final_success is False:
            errors = set(error_messages)
            write_msg('== ERRORS ==\n{}'.format('====\n'.join(errors)))
            input("Something bad happened! Try to fix it and then press ENTER to continue...")
    write_msg('> crate {} has been published'.format(crate_name))


def create_tag_and_push(tag_name, repository, temp_dir):
    path = join(temp_dir, repository)
    command = ['bash', '-c', 'cd {0} && git tag "{1}" && git push origin "{1}"'
               .format(path, tag_name)]
    if not exec_command_and_print_error(command):
        input("Something bad happened! Try to fix it and then press ENTER to continue...")
