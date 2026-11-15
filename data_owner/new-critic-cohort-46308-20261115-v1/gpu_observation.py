"""Read-only NVIDIA PID accounting: identical UUID/PID rows are one observation.
Unknown/conflicting initialized-PID memory is NEVER treated as zero.
"""
def own_memory_bytes(text, *, pid, uuid, initialized):
    values=set()
    for line in text.splitlines():
        if not line.strip():continue
        row=[x.strip() for x in line.split(',')]
        if len(row)!=3:raise ValueError('Unparseable GPU PID accounting')
        if row[0]==str(pid) and row[2]==uuid:
            if not row[1].isdigit():raise ValueError('Own GPU memory observation unknown')
            values.add(int(row[1])*1024**2)
    if len(values)>1:raise ValueError('Conflicting same-UUID/PID memory observations')
    if not values:
        if initialized:raise ValueError('Initialized CUDA PID missing; unknown is not zero')
        return None
    return next(iter(values))
