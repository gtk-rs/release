from os import listdir
from os.path import isdir, isfile, join
import subprocess
import sys


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


def exec_command(command, timeout=30):
    child = subprocess.Popen(command, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
    stdout, stderr = child.communicate(timeout=timeout)
    return (child.returncode == 0,
            convert_to_string(stdout),
            convert_to_string(stderr))


def get_all_files(file_name, dir_path):
    entries = [f for f in listdir(dir_path)]
    ret = []
    for entry in entries:
        full_entry = join(dir_path, entry)
        if isfile(full_entry) and entry == file_name:
            ret.append(full_entry)
        elif isdir(full_entry) and not entry.startswith('.'):
            ret.extend(get_all_files(file_name, full_entry))
    return ret


def clone_repo(repo_name, temp_dir):
    repo_url = '{}/{}/{}'.format(GITHUB_URL, ORGANIZATION, crate)
    target_dir = join(temp_dir, repo_name)
    try:
        write_msg('=> Cloning "{}" from "{}"'.format(repo_name, repo_url))
        command = ['git', 'clone', repo_url, target_dir]
        ret, stdout, stderr = exec_command(command)
        if not ret:
            write_error('command failed: {}'.format(' '.join(command)))
            return False
    except subprocess.TimeoutExpired:
        write_error('command timed out: {}'.format(' '.join(command)))
        return False
    except Exception as ex:
        write_error('command got an exception: {}'.format(' '.join(command)))
        return False
    return True