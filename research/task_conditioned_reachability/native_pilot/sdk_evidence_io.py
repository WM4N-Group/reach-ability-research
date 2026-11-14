"""Durable SDK evidence BEFORE a native shutdown may terminate the process."""
import json,os
from pathlib import Path


def durable_json(path,value):
    path=Path(path);tmp=path.with_suffix(path.suffix+'.tmp')
    with tmp.open('w') as f:
        json.dump(value,f,indent=2,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())
    os.replace(tmp,path)


def persist_then_close(path,result,close):
    """close may call os._exit(0); do not put the only evidence write after it."""
    durable_json(path,result)
    print(json.dumps(result,indent=2),flush=True)
    try:
        close()
    except BaseException as exc:
        if isinstance(exc,SystemExit) and exc.code in (None,0):return
        result=dict(result,passed=False,shutdown_error_type=type(exc).__name__,shutdown_error=str(exc))
        durable_json(path,result)
        raise
