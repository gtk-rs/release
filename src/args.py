import getopt
# local imports
from utils import write_error, write_msg
import consts


class UpdateType:
    MAJOR = 0
    MEDIUM = 1
    MINOR = 2

    @staticmethod
    def create_from_string(version_s):
        version_s = version_s.lower()
        if version_s == 'major':
            return UpdateType.MAJOR
        elif version_s == 'medium':
            return UpdateType.MEDIUM
        elif version_s == 'minor':
            return UpdateType.MINOR
        return None

    @staticmethod
    def to_str(update):
        if update == UpdateType.MAJOR:
            return "MAJOR"
        elif update == UpdateType.MEDIUM:
            return "MEDIUM"
        elif update == UpdateType.MINOR:
            return "MINOR"
        return "UNKNOWN"


def get_answer(text):
    while True:
        text = input('{} [Y/n] '.format(text)).strip().lower()
        if len(text) == 0 or text == 'y':
            return True
        if text == 'n':
            return False
        write_msg('-> Invalid answer "{}": only "Y" and "n" are expected'.format(text))


def is_sys_crate(crate):
    return crate.endswith('-sys') or crate.endswith('-sys-rs')


def get_up_type(crate, mode, pick_update_type_for_crates, default_updates):
    if mode is None and pick_update_type_for_crates is False:
        return None
    if is_sys_crate(crate) and default_updates['sys'] is not None:
        return default_updates['sys']
    elif not is_sys_crate(crate) and default_updates['non-sys'] is not None:
        return default_updates['non-sys']
    while pick_update_type_for_crates is True:
        text = input('Which kind of update do you want for "{}"? [MINOR/MEDIUM/MAJOR] '
                     .format(crate))
        text = text.strip().lower()
        mode = UpdateType.create_from_string(text)
        if mode is not None:
            if (is_sys_crate(crate) and
                    get_answer('Do you want to use this release for all other sys crates?')):
                default_updates['sys'] = mode
            elif (not is_sys_crate(crate) and
                  get_answer('Do you want to use this release for all other non-sys crates?')):
                default_updates['non-sys'] = mode
            break
        write_msg('Invalid update type received: "{}". Accepted values: (MINOR|MEDIUM|MAJOR)'
                  .format(text))
    return mode


def ask_updates_confirmation(crates):
    write_msg("Recap' of picked updates:")
    for crate in crates:
        write_msg("[{}] => {}".format(crate['crate']['crate'], UpdateType.to_str(crate['up-type'])))
    return get_answer('Do you agree with this?')


def write_help():
    write_msg("release.py accepts the following options:")
    write_msg("")
    write_msg(" * -h | --help                  : display this message")
    write_msg(" * -t <token> | --token=<token> : give the github token")
    write_msg(" * -m <mode> | --mode=<mode>    : give the update type (MINOR|MEDIUM|MAJOR)")
    write_msg(" * --no-push                    : performs all operations but doesn't push anything")
    write_msg(" * --doc-only                   : only builds documentation")
    write_msg(" * -c <crate> | --crate=<crate> : only update the given crate (for test purpose"
              " mainly)")
    write_msg(" * --badges-only                : only update the badges on the website")
    write_msg(" * --tags-only                  : only create new tags")
    write_msg(" * --pick-crates                : add an interactive way to pick crates")
    write_msg(" * --pick-update-type-for-crates: pick an update type for each crate")


class Arguments:
    def __init__(self):
        self.token = None
        self.mode = None
        self.no_push = False
        self.doc_only = False
        self.specified_crate = None
        self.badges_only = False
        self.tags_only = False
        self.crates = consts.CRATE_LIST

    @staticmethod
    def parse_arguments(argv):
        # pylint: disable=too-many-branches,too-many-return-statements
        try:
            opts = getopt.getopt(argv,
                                 "ht:m:c:",
                                 ["help", "token=", "mode=", "no-push", "doc-only", "crate",
                                  "badges-only", "tags-only", "pick-update-type-for-crates",
                                  "pick-crates"])[0] # second argument is "args"
        except getopt.GetoptError:
            write_help()
            return None

        instance = Arguments()

        pick_update_type_for_crates = False

        for opt, arg in opts:
            if opt in ('-h', '--help'):
                write_help()
                return None
            elif opt in ("-t", "--token"):
                instance.token = arg
            elif opt in ("-m", "--mode"):
                instance.mode = UpdateType.create_from_string(arg)
                if instance.mode is None:
                    write_error('{}: Invalid update type received. Accepted values: '
                                '(MINOR|MEDIUM|MAJOR)'.format(opt))
                    return None
            elif opt == "--no-push":
                instance.no_push = True
            elif opt == "--doc-only":
                instance.doc_only = True
            elif opt == "--badges-only":
                instance.badges_only = True
            elif opt in ('-c', '--crate'):
                instance.specified_crate = arg
            elif opt == '--tags-only':
                instance.tags_only = True
            elif opt == '--pick-crates':
                instance.crates = []
            elif opt == '--pick-update-type-for-crates':
                pick_update_type_for_crates = True
            else:
                write_msg('"{}": unknown option'.format(opt))
                write_msg('Use "-h" or "--help" to see help')
                return None
        if instance.token is None and instance.no_push is False:
            write_error('Missing token argument.')
            return None
        if (instance.mode is None and
                instance.doc_only is False and
                instance.badges_only is False and
                instance.tags_only is False and
                pick_update_type_for_crates is False):
            write_error('Missing update type argument.')
            return None

        default_updates = {"sys": None, "non-sys": None}
        if len(instance.crates) == 0:
            for crate in consts.CRATE_LIST:
                if get_answer('Do you want to include "{}" in this release?') is True:
                    instance.crates.append(
                        {
                            'up-type': get_up_type(crate['crate'],
                                                   instance.mode,
                                                   pick_update_type_for_crates,
                                                   default_updates),
                            'crate': crate,
                        })
            if ask_updates_confirmation(instance.crates) is False:
                write_msg('OK! Aborting then!')
                return None
        else:
            instance.crates = [
                {
                    'up-type': get_up_type(crate['crate'],
                                           instance.mode,
                                           pick_update_type_for_crates,
                                           default_updates),
                    'crate': crate,
                } for crate in instance.crates]
            if (pick_update_type_for_crates is True and
                    ask_updates_confirmation(instance.crates) is False):
                write_msg('OK! Aborting then!')
                return None
        return instance
