from os.path import join
import json
import subprocess
import sys
import time
# pip3 install requests
import requests
# local import
import consts
from globals import PULL_REQUESTS
from my_toml import TomlHandler


def write_error(error_msg):
    sys.stderr.write(f'{error_msg}\n')


def write_msg(msg):
    sys.stdout.write(f'{msg}\n')


def convert_to_string(content):
    if content.__class__.__name__ == 'bytes':
        return content.decode('utf-8')
    return content


def get_file_content(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    except Exception as err:
        write_error(f'get_file_content failed: "{file_path}": {err}')
    return None


def write_into_file(file_path, content):
    try:
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(content)
            return True
    except Exception as err:
        write_error(f'write_into_file failed: "{file_path}": {err}')
    return False


def exec_command(command, timeout=None):
    # pylint: disable=consider-using-with
    child = subprocess.Popen(command, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
    stdout, stderr = child.communicate(timeout=timeout)
    return (child.returncode == 0,
            convert_to_string(stdout),
            convert_to_string(stderr))


def exec_command_and_print_error(command, timeout=None):
    ret, stdout, stderr = exec_command(command, timeout=timeout)
    if not ret:
        full_command = ' '.join(command)
        write_error(f'Command "{full_command}" failed:')
        if len(stdout) > 0:
            write_error(f'=== STDOUT ===\n{stdout}\n')
        if len(stderr) > 0:
            write_error(f'=== STDERR ===\n{stderr}\n')
    return ret


def clone_repo(repo_name, temp_dir, depth=None):
    repo_url = f'{consts.GIT_URL}/{consts.ORGANIZATION}/{repo_name}.git'
    target_dir = join(temp_dir, repo_name)
    try:
        write_msg(f'=> Cloning "{repo_name}" from "{repo_url}"')
        command = ['git', 'clone', repo_url, target_dir]
        if depth is not None:
            command = ['git', 'clone', '--depth', str(depth), repo_url, target_dir]
        ret, stdout, stderr = exec_command(command, timeout=300)
        if not ret:
            full_command = ' '.join(command)
            write_error(
                f'command "{full_command}" failed: ===STDOUT===\n{stdout}\n===STDERR===\n{stderr}')
            return False
        command = ['bash', '-c', f'cd {target_dir} && git submodule update --init']
        if not exec_command_and_print_error(command):
            input('Failed to init submodule... Press ENTER to continue')
        return True
    except subprocess.TimeoutExpired:
        full_command = ' '.join(command)
        write_error(f'command timed out: {full_command}')
    except Exception as err:
        full_command = ' '.join(command)
        write_error(f'command "{full_command}" got an exception: {err}')
    return False


def create_headers(token):
    headers = {
        'User-Agent': 'gtk-rs',
        'Accept': 'application/vnd.github.v3+json',
    }
    if token is not None:
        # Authentication to github.
        headers['Authorization'] = f'token {token}'
    return headers


def post_content(url, token, details, method='post', header_extras=None):
    if header_extras is None:
        header_extras = {}
    headers = create_headers(token)
    for extra in header_extras:
        headers[extra] = header_extras[extra]
    try:
        req = None
        if method == 'post':
            req = requests.post(url, data=json.dumps(details), headers=headers)
        else:
            req = requests.put(url, data=json.dumps(details), headers=headers)
        try:
            req.raise_for_status()
        except Exception:
            write_msg(f'Sent by bithub api: {req.json()}')
            req.raise_for_status()
        return req.json()
    except Exception as err:
        write_error(f'post_content: An error occurred: {err}')
    return None


def get_highest_feature_version(v1_feature, v2_feature):
    t_v1 = v1_feature[1:].split('_')
    t_v2 = v2_feature[1:].split('_')
    i = 0
    while i < len(t_v1) and i < len(t_v2):
        try:
            x1_version = int(t_v1[i])
            x2_version = int(t_v2[i])
            if x1_version > x2_version:
                return v1_feature
            if x1_version < x2_version:
                return v2_feature
            i += 1
        except Exception:
            write_error(f'get_highest_feature_version int conversion error: int("{t_v1[i]}") vs '
                        f'int("{t_v2[i]}") from "{v1_feature}" and "{v2_feature}"')
            break
    return v1_feature


# This function does two things:
#
# 1. Check if dox feature is present or try getting the highest version feature
# 2. Getting all the other features (for cairo it's very important)
def get_features(path):
    # pylint: disable=too-many-branches
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


# def compare_versions(v1, v2):
#     v1 = v1.split('.')
#     v2 = v2.split('.')
#
#     for x in range(0, min(len(v1), len(v2))):
#         try:
#             entry1 = int(v1)
#             entry2 = int(v2)
#         except Exception:
#             # If it cannot be converted into a number, better just compare strings then.
#             entry1 = v1
#             entry2 = v2
#         if entry1 > entry2:
#             return 1
#         if entry1 < entry2:
#             return -1
#     # In here, "3.2" is considered littler than "3.2.0". That's how life goes.
#     return len(v1) - len(v2)


def commit_and_push(repo_name, temp_dir, commit_msg, target_branch):
    commit(repo_name, temp_dir, commit_msg)
    push(repo_name, temp_dir, target_branch)


def commit(repo_name, temp_dir, commit_msg):
    repo_path = join(temp_dir, repo_name)
    command = ['bash', '-c', f'cd {repo_path} && git commit . -m "{commit_msg}"']
    if not exec_command_and_print_error(command):
        input("Fix the error and then press ENTER")


def push(repo_name, temp_dir, target_branch):
    repo_path = join(temp_dir, repo_name)
    command = ['bash', '-c', f'cd {repo_path} && git push origin HEAD:{target_branch}']
    if not exec_command_and_print_error(command):
        input("Fix the error and then press ENTER")


def add_to_commit(repo_name, temp_dir, files_to_add):
    repo_path = join(temp_dir, repo_name)
    files = ' '.join([f'"{f}"' for f in files_to_add])
    command = ['bash', '-c', f'cd {repo_path} && git add {files}']
    if not exec_command_and_print_error(command):
        input("Fix the error and then press ENTER")


def revert_changes(repo_name, temp_dir, files):
    repo_path = join(temp_dir, repo_name)
    files = ' '.join([f'"{f}"' for f in files])
    command = ['bash', '-c', f'cd {repo_path} && git rm -f {files} && git checkout -- {files}']
    if not exec_command_and_print_error(command):
        input("Fix the error and then press ENTER")


def checkout_target_branch(repo_name, temp_dir, target_branch):
    repo_path = join(temp_dir, repo_name)
    command = ['bash', '-c', f'cd {repo_path} && git checkout {target_branch}']
    if not exec_command_and_print_error(command):
        input("Fix the error and then press ENTER")


def checkout_to_new_branch(repo_name, temp_dir, target_branch):
    repo_path = join(temp_dir, repo_name)
    command = ['bash', '-c', f'cd {repo_path} && git checkout -b {target_branch}']
    if not exec_command_and_print_error(command):
        input("Fix the error and then press ENTER")


def get_last_commit_date(repo_name, temp_dir):
    repo_path = join(temp_dir, repo_name)
    success, out, err = exec_command(
        ['bash', '-c', f'cd {repo_path} && git log --format=%at --no-merges -n 1'])
    return (success, out, err)


def get_last_commit_hash(repo_path):
    success, out, _ = exec_command(
        ['bash', '-c', f'cd {repo_path} && git rev-parse HEAD'])
    if success is True:
        return out.strip()
    return ''


def get_repo_last_commit_hash(repo_url):
    success, out, _ = exec_command(
        ['bash', '-c', f'git ls-remote {repo_url} HEAD'])
    if success is True:
        out = out.split('\n', maxsplit=1)[0].strip()
        return out.split('\t', maxsplit=1)[0].split(' ', maxsplit=1)[0]
    return '<unknown>'


def merging_branches(repo_name, temp_dir, merge_branch):
    repo_path = join(temp_dir, repo_name)
    command = ['bash', '-c', f'cd {repo_path} && git merge "origin/{merge_branch}"']
    if not exec_command_and_print_error(command):
        input("Fix the error and then press ENTER")


def publish_crate(repository, crate_dir_path, temp_dir, crate_name):
    # pylint: disable=too-many-locals
    write_msg(f'=> publishing crate {crate_name}')
    path = join(join(temp_dir, repository), crate_dir_path)
    # In case we needed to fix bugs, we checkout to crate branch before publishing crate.
    command = [
        'bash',
        '-c',
        f'cd {path} && cargo publish --no-verify']
    retry = 3
    error_messages = []
    final_success = False
    wait_time = 30
    while retry > 0:
        ret, stdout, stderr = exec_command(command)
        if not ret:
            full_command = ' '.join(command)
            error_messages.append(f'Command "{full_command}" failed:')
            if len(stdout) > 0:
                error_messages[len(error_messages) - 1] += f'\n=== STDOUT ===\n{stdout}\n'
            if len(stderr) > 0:
                error_messages[len(error_messages) - 1] += f'\n=== STDERR ===\n{stderr}\n'
            retry -= 1
            if retry > 0:
                extra = 'ies' if retry > 0 else 'y'
                write_msg(
                    f"Let's sleep for {wait_time} seconds before retrying, {retry + 1} "
                    f"retr{extra} remaining...")
                time.sleep(wait_time)
        else:
            final_success = True
            break
    if final_success is False:
        errors = set(error_messages)
        errors = '====\n'.join(errors)
        write_msg(f'== ERRORS ==\n{errors}')
        input("Something bad happened! Try to fix it and then press ENTER to continue...")
    write_msg(f'> crate {crate_name} has been published')


def create_tag_and_push(tag_name, repository, temp_dir):
    path = join(temp_dir, repository)
    command = ['bash', '-c', f'cd {path} && git tag "{tag_name}" && git push origin "{tag_name}"']
    if not exec_command_and_print_error(command):
        input("Something bad happened! Try to fix it and then press ENTER to continue...")


def create_pull_request(repo_name, from_branch, target_branch, token, add_to_list=True):
    req = post_content(f'{consts.GH_API_URL}/repos/{consts.ORGANIZATION}/{repo_name}/pulls',
                       token,
                       {'title': f'[release] merging {from_branch} into {target_branch}',
                        'body': 'cc @GuillaumeGomez @sdroege @bilelmoussaoui',
                        'base': target_branch,
                        'head': from_branch,
                        'maintainer_can_modify': True})
    if req is None:
        write_error(f"Pull request from {repo_name}/{from_branch} to {repo_name}/{target_branch} "
                    "couldn't be created. You need to do it yourself... (url provided at the end)")
        input("Press ENTER once done to continue...")
        PULL_REQUESTS.append(
            f'|=> "{consts.GITHUB_URL}/{consts.ORGANIZATION}/{repo_name}'
            f'/compare/{target_branch}...{from_branch}?expand=1"')
    else:
        write_msg(f"===> Pull request created: {req['html_url']}")
        if add_to_list is True:
            PULL_REQUESTS.append(f'> {req["html_url"]}')


def check_if_up_to_date():
    remote_repo = "git://github.com/gtk-rs/release.git"
    last_commit = get_last_commit_hash(".")
    remote_last_commit = get_repo_last_commit_hash(remote_repo)
    if last_commit != remote_last_commit:
        write_msg(
            f"Remote repository `{remote_repo}` has a different last commit than local: `"
            f"{remote_last_commit}` != `{last_commit}`")
        text = input("Do you want to continue anyway? [y/N] ").strip().lower()
        if len(text) == 0 or text != 'y':
            write_msg("Ok, leaving then. Don't forget to update!")
            return False
    return True
