import consts
from os.path import join
from my_toml import TomlHandler
import json
import subprocess
import sys
# pip3 install requests
import requests


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
        ret, stdout, stderr = exec_command(command, timeout=30)
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
        except:
            print('Sent by bithub api: {}'.format(r.json()))
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
        except:
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
        features.append('dox')
    elif highest_version is not None:
        print("/!\\ Seems there is no dox feature so let's just use the highest version instead...")
        features.append(highest_version)
    else:
        print("/!\\ That's weird: no dox or version feature. Is everything fine with this one?")
    return ' '.join(features)

def compare_versions(v1, v2):
    v1 = v1.split('.')
    v2 = v2.split('.')

    for x in range(0, min(len(v1), len(v2))):
        try:
            entry1 = int(v1)
            entry2 = int(v2)
        except:
            # If it cannot be converted into a number, better just compare strings then.
            entry1 = v1
            entry2 = v2
        if entry1 > entry2:
            return 1
        if entry1 < entry2:
            return -1
    # In here, "3.2" is considered littler than "3.2.0". That's how life goes.
    return len(v1) - len(v2)
