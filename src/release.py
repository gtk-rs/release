#!/bin/python3

from contextlib import contextmanager
from os.path import join
from toml import TomlHandler
from utils import exec_command, get_file_content, write_error, write_msg
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


def check_and_update_version(entry, update_type, dependency_name):
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
            tmp = update_version(dic[entry], update_type, dependency_name, place_type="dependency")
            if tmp is None:
                return None
            dic[entry] = tmp
            break
    return '{{{}}}'.format(', '.join(['{} = {}'.format(entry, dic[entry]) for entry in dic]))



def update_crate_version(crate_name, temp_dir, update_type):
    files = get_all_files('Cargo.toml', join(crate_name, temp_dir))
    for file in files:
        output = file.replace(join(crate_name, temp_dir), '')
        if output.startswith('/'):
            output = output[1:]
        write_msg('=> Updating versions for {}'.format(output))
        content = get_file_content(file)
        if content is None:
            return False
        toml = TomlHandler(content)
        for section in toml.sections:
            if section.name == 'package' or
               (section.name.startswith('dependencies.') and section.name[13:] in CRATE_LIST):
                version = sections.entries.get('version', None)
                if version is None:
                    continue
                version = update_version(version, update_type, section.name)
                if version is None:
                    return False
            elif section_name == 'dependencies':
                for entry in section.entries:
                    if entry in CRATE_LIST:
                        section.entries[entry] = check_and_update_version(section.entries[entry],
                                                                          update_type,
                                                                          entry)


def start(update_type):
    write_msg('Creating temporary directory...')
    with TemporaryDirectory() as temp_dir:
        write_msg('Cloning the repositories...')
        for crate in REPOSITORY_LIST:
            if clone_repo(crate, temp_dir) is False:
                return
        write_msg('Done!')
        write_msg('Updating crates version...')
        for crate in REPOSITORY_LIST:
            if update_crate_version(crate, temp_dir, update_type) is False:
                return


if __name__ != "__main__":
    write_error('This file should be launched as main file.')
    sys.exit(1)
# Add update type: minor, medium, major
start(UpdateType.MINOR)
