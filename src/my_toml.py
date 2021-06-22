# Very simple Toml parser.

def create_section(content_line):
    if content_line.endswith(']'):
        return Section(content_line[1:-1])
    return Section(content_line[1:])


class Section:
    def __init__(self, name):
        self.name = name
        self.entries = []

    def add_entry(self, entry):
        if len(entry) > 0:
            elems = entry.split('=')
            key = elems[0].strip()
            elems = '='.join(elems[1:]).strip()
            self.set(key, elems)

    def set(self, key, value):
        for entry in self.entries:
            if entry['key'] == key:
                entry['value'] = value
                return
        self.entries.append({'key': key, 'value': value})

    def clear(self):
        self.entries = []

    def get(self, key, default_value):
        for entry in self.entries:
            if entry['key'] == key:
                return entry['value']
        return default_value

    def __str__(self):
        return '[{}]\n{}'.format(self.name,
                                 '\n'.join(['{} = {}'.format(x['key'], x['value'])
                                            for x in self.entries]))


class TomlHandler:
    def __init__(self, content):
        self.sections = []
        filler = []
        multilines = {
            '[': ']',
            '"""': '"""',
            '{': '}',
        }
        stop_str = None
        for line in content.split('\n'):
            if len(filler) > 0:
                filler.append(line)
                if line.endswith(stop_str):
                    self.sections[-1].add_entry('\n'.join(filler))
                    filler = []
            elif line.startswith('['):
                self.sections.append(create_section(line))
            elif len(self.sections) > 0:
                add_entry = True
                for key, end_str in multilines.items():
                    if line.endswith(key):
                        stop_str = end_str
                        filler.append(line)
                        add_entry = False
                        break
                if add_entry is True:
                    self.sections[-1].add_entry(line)
                    continue


    def __str__(self):
        return '\n\n'.join([str(x) for x in self.sections]) + '\n'
