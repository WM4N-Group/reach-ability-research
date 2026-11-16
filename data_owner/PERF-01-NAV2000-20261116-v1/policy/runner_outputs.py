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


def finish_accounting(budget,destination):
    """Final exact logical totals INCLUDING this last report, then reconcile.
    Caller may not write anything after this function. Not allocated/provider or
    unknown-out-of-band peak accounting. No native resume, even on prior failure.
    """
    with budget.lock:
        if not budget.finalizing or not budget.state.sealed or budget.active:
            raise ValueError('Seal native and close ALL writers before exact final ledger')
        destination=budget._path(destination)
        if destination.exists():raise ValueError('No final-ledger overwrite/reopen')
        base=budget.used;high=budget.highwater;value=dict(
            schema='Data-exact-final-controlled-logical-output-v1',
            final_controlled_logical_bytes=base,controlled_logical_highwater_bytes=high,
            file_count_including_this_report=len(budget.nodes)+1,
            native_sealed=True,not_filesystem_allocated_or_external_writer_peak=True)
        for _ in range(16):
            size=len((json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode())
            total=base+size;peak=max(high,total)
            if (value['final_controlled_logical_bytes'],value['controlled_logical_highwater_bytes'])==(total,peak):break
            value.update(final_controlled_logical_bytes=total,controlled_logical_highwater_bytes=peak)
        else:raise ValueError('Final report size did not converge')
        write_json(budget,destination,value)
        if budget.reconcile()!=total or budget.highwater!=peak:
            budget.state.fail('Final exact report/counter mismatch')
        return value
