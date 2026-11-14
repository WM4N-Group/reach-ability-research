"""Exclusive, hash-chained evidence; never append to a previous experiment."""
import json
import os
from pathlib import Path
from .contracts import canonical, sha


class Journal:
    def __init__(self, path):
        self.path = Path(path)
        self.stream = self.path.open('x', encoding='utf-8')
        self.previous = '0' * 64
        self.count = 0

    def __call__(self, row):
        if not isinstance(row, dict) or not isinstance(row.get('event'), str):
            raise ValueError('Typed event evidence required')
        envelope = dict(sequence=self.count, previous_sha256=self.previous, payload=json.loads(canonical(row)))
        digest = sha(envelope)
        self.stream.write(canonical(dict(envelope, sha256=digest))+'\n')
        self.stream.flush()
        self.previous = digest
        self.count += 1
        return str(self.path)+'#'+str(self.count)

    def close(self):
        if not self.stream.closed:
            self.stream.flush()
            os.fsync(self.stream.fileno())
            self.stream.close()


def verify(path):
    previous, count = '0'*64, 0
    for line in Path(path).read_text().splitlines():
        record = json.loads(line)
        digest = record.pop('sha256')
        if record['sequence'] != count or record['previous_sha256'] != previous or sha(record) != digest:
            raise ValueError('Evidence chain altered or reordered')
        previous, count = digest, count+1
    return dict(rows=count, last_sha256=previous, valid=True)
