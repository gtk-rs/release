from os.path import join
import subprocess
import sys

# local import
import consts


def write_error(error_msg):
    sys.stderr.write(f"{error_msg}\n")


def write_msg(msg):
    sys.stdout.write(f"{msg}\n")


def convert_to_string(content):
    if content.__class__.__name__ == "bytes":
        return content.decode("utf-8")
    return content


def exec_command(command, timeout=None, show_output=False, cwd=None):
    if show_output:
        write_msg(f"Executing command {command} with cwd: {cwd}")
    child = subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=cwd
    )
    if timeout is not None:
        stdout, stderr = child.communicate(timeout=timeout)
    else:
        stdout, stderr = child.communicate()
    if show_output:
        write_msg(f"== STDOUT == {stdout}")
        write_msg(f"== STDERR == {stderr}")
    stdout = convert_to_string(stdout)
    stderr = convert_to_string(stderr)
    return (child.returncode == 0, stdout, stderr)


def exec_command_and_print_error(command, timeout=None, cwd=None):
    ret, stdout, stderr = exec_command(command, timeout=timeout, cwd=cwd)
    if not ret:
        full_command = " ".join(command)
        write_error(f'Command "{full_command}" failed:')
        if len(stdout) > 0:
            write_error(f"=== STDOUT ===\n{stdout}\n")
        if len(stderr) > 0:
            write_error(f"=== STDERR ===\n{stderr}\n")
    return ret


def clone_repo(repo_name, temp_dir, depth=None):
    repo_url = f"{consts.GIT_URL}/{consts.ORGANIZATION}/{repo_name}.git"
    target_dir = join(temp_dir, repo_name)
    try:
        write_msg(f'=> Cloning "{repo_name}" from "{repo_url}"')
        command = ["git", "clone", repo_url, target_dir]
        if depth is not None:
            command = ["git", "clone", "--depth", str(depth), repo_url, target_dir]
        ret, stdout, stderr = exec_command(command, timeout=300)
        if not ret:
            full_command = " ".join(command)
            write_error(
                f'command "{full_command}" failed: ===STDOUT===\n{stdout}\n===STDERR===\n{stderr}'
            )
            return False
        command = ["git", "submodule", "update", "--init"]
        if not exec_command_and_print_error(command, cwd=target_dir):
            input("Failed to init submodule... Press ENTER to continue")
        return True
    except subprocess.TimeoutExpired:
        full_command = " ".join(command)
        write_error(f"command timed out: {full_command}")
    except Exception as err:
        full_command = " ".join(command)
        write_error(f'command "{full_command}" got an exception: {err}')
    return False


def commit(repo_name, temp_dir, commit_msg):
    repo_path = join(temp_dir, repo_name)
    command = ["git", "commit", ".", "-m", commit_msg]
    if not exec_command_and_print_error(command, cwd=repo_path):
        input("Fix the error and then press ENTER")


def add_to_commit(repo_name, temp_dir, files_to_add):
    repo_path = join(temp_dir, repo_name)
    command = ["git", "add"]
    for file in files_to_add:
        command.append(file)
    if not exec_command_and_print_error(command, cwd=repo_path):
        input("Fix the error and then press ENTER")


def get_last_commit_hash(repo_path):
    success, out, _ = exec_command(["git", "rev-parse", "HEAD"], cwd=repo_path)
    if success is True:
        return out.strip()
    return ""


def get_repo_last_commit_hash(repo_url):
    success, out, _ = exec_command(
        ["git", "ls-remote", repo_url, "HEAD"], show_output=True
    )
    if success is True:
        out = out.split("\n", maxsplit=1)[0].strip()
        return out.split("\t", maxsplit=1)[0].split(" ", maxsplit=1)[0]
    return "<unknown>"


def check_if_up_to_date():
    write_msg("Checking if up-to-date...")
    remote_repo = "git@github.com:gtk-rs/release.git"
    last_commit = get_last_commit_hash(".")
    remote_last_commit = get_repo_last_commit_hash(remote_repo)
    if last_commit != remote_last_commit:
        write_msg(
            f"Remote repository `{remote_repo}` has a different last commit than local: `"
            f"{remote_last_commit}` != `{last_commit}`"
        )
        text = input("Do you want to continue anyway? [y/N] ").strip().lower()
        if len(text) == 0 or text != "y":
            write_msg("Ok, leaving then. Don't forget to update!")
            return False
    return True
