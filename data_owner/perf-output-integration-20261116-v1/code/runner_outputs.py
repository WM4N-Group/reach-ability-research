"""Data-owned small report/qualification PNG IO for a NEW runner, no native calls."""
import json
import os
from pathlib import Path


def write_json(budget, destination, value):
    """Controlled temp+replace: both files count until atomic replace completes."""
    destination=budget._path(destination)
    temporary=destination.with_name(destination.name+'.pending')
    with budget.open(temporary,'x',encoding='utf-8')as stream:
        json.dump(value,stream,ensure_ascii=False,indent=2,allow_nan=False)
        stream.write('\n');stream.flush();os.fsync(stream.fileno())
    budget.replace(temporary,destination)


def write_png(budget, destination, image):
    # Passing a BudgetPath filename to Pillow would bypass the counter.
    with budget.open(destination,'xb')as stream:
        image.save(stream,format='PNG')
