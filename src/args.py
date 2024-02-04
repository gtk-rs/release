import getopt

# local imports
from utils import write_error, write_msg
import consts


def write_help():
    write_msg("release.py accepts the following options:")
    write_msg("")
    write_msg(" * -h | --help                  : display this message")
    write_msg(" * -t <token> | --token=<token> : give the github token")


class Arguments:
    def __init__(self):
        self.token = None

    @staticmethod
    def parse_arguments(argv):
        try:
            opts = getopt.getopt(argv, "ht:m:c:", ["help", "token="])[
                0
            ]  # second argument is "args"
        except getopt.GetoptError:
            write_help()
            return None

        instance = Arguments()

        for opt, arg in opts:
            if opt in ("-h", "--help"):
                write_help()
                return None
            if opt in ("-t", "--token"):
                instance.token = arg
            else:
                write_msg(f'"{opt}": unknown option')
                write_msg('Use "-h" or "--help" to see help')
                return None
        if instance.token is None:
            # In this case, I guess it's not an issue to not have a github token...
            write_error("Missing token argument.")
            return None

        return instance
