"""Linux executable-file mapping closure: bootstrap inventory + periodic refusal.
Not kernel/root/native-memory protection. Non-file kernel mappings stay OS trust.
"""
from pathlib import Path


def executable_file_maps():
    result=set()
    for line in Path('/proc/self/maps').read_text().splitlines():
        fields=line.split(maxsplit=5)
        if len(fields)<6 or 'x'not in fields[1]or not fields[5].startswith('/'):continue
        name=fields[5]
        if name.endswith(' (deleted)'):raise RuntimeError('Deleted executable mapping; no trusted file identity')
        p=Path(name)
        if not p.is_file():raise RuntimeError('Unknown nonregular executable mapping')
        result.add(str(p))
    if not result:raise RuntimeError('Unknown/empty executable file mapping closure')
    return frozenset(result)
