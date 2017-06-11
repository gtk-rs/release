import consts
from os import listdir
from os.path import isdir, isfile, join
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


def clone_repo(repo_name, temp_dir):
    repo_url = '{}/{}/{}'.format(consts.GITHUB_URL, consts.ORGANIZATION, crate)
    target_dir = join(temp_dir, repo_name)
    try:
        write_msg('=> Cloning "{}" from "{}"'.format(repo_name, repo_url))
        command = ['git', 'clone', repo_url, target_dir]
        ret, stdout, stderr = exec_command(command, timeout=30)
        if not ret:
            write_error('command failed: {}'.format(' '.join(command)))
            return False
        return True
    except subprocess.TimeoutExpired:
        write_error('command timed out: {}'.format(' '.join(command)))
    except Exception as ex:
        write_error('command got an exception: {}'.format(' '.join(command)))
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
        r.raise_for_status()
        return r.json()
    except Exception as e:
        write_error('post_content: An error occurred: {}'.format(e))
    return None
