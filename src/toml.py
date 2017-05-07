# Very simple Toml parser.

def create_section(content_line):
    if content_line.endswith(']'):
        return Section(content_line[1:-1])
    return Section(content_line[1:])


class Section:
    def __init__(self, name):
        self.name = name
        self.entries = {}

    def add_entry(self, entry):
        if len(entry) > 0:
            elems = entry.split('=')
            key = elems[0].strip()
            elems = '='.join(elems[1:]).strip
            self.entries[key] = elems

    def __str__(self):
        return '[{}]\n{}'.format(self.name,
                                 '\n'.join(['{} = {}'.format(x, self.entries[x])
                                            for x in self.entries]))


class TomlHandler:
    def __init__(self, content):
        self.sections = []
        for line in content.split('\n'):
            if line.startswith('['):
                self.sections.append(create_section(line))
            elif len(self.sections) > 0:
                self.sections[-1].add_entry(line)

    def __str__(self):
        return '\n\n'.join([str(x) for x in self.sections])
