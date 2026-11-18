"""First qualification of a single, newly registered TRAIN rollout."""
import hashlib
import json
from pathlib import Path
from random import Random
from types import FunctionType
import standard_runtime
from terminal_action import BrakeAction

PURPOSE='PUSH_TERMINAL_ONLINE_TRAIN_ONLY'
SRC='f4f05e117486a7b00583cf5cc1eacf0d14a612544bfb91a5984279db34bb9d22'

def need(x, why):
    if not x:raise ValueError(why)

def read_registry(c):
    p=Path(c['train_enrollment_path']);raw=p.read_bytes();need(not p.is_symlink() and hashlib.sha256(raw).hexdigest()==c['train_enrollment_SHA256'],'Exact preregistered TRAIN input')
    e=json.loads(raw);need(e['purpose']==PURPOSE and e['scope']==c['scope_id'] and e['seed']==c['seed']==7341 and e['delay_ms']==c['delay_ms']==15,'New actual original seed and delay, no DEV labels')
    need(e['max_own_zero']==e['max_main']==e['max_updates']==1 and c['training_allowed'] is True and e['actor_frozen'] is True and e['may_launch_second_GPU_automatically'] is False,'Finite first update only')
    need(e['initial_logits']==[0.,0.] and e['action_order']==[dict(index=0,lead_m=0.),dict(index=1,lead_m=.20)],'Frozen initial distribution')
    index=Random(e['selection_seed']).choices(range(2),weights=(.5,.5),k=1)[0]
    need(c['terminal_connector_DEV_action']==e['action_order'][index], 'Sample exactly once from preregistered seed, no selection by results')
    e['chosen']=e['action_order'][index]
    fingerprint=hashlib.sha256(json.dumps((tuple(e['initial_logits']),0),separators=(',',':'),allow_nan=False).encode()).hexdigest()
    e['behavior_policy_sha256']=fingerprint
    return e

def bind_constructor(c):
    e=read_registry(c);fn=standard_runtime.assemble;p=Path(fn.__code__.co_filename)
    need(p==Path(standard_runtime.__file__) and not p.is_symlink() and hashlib.sha256(p.read_bytes()).hexdigest()==SRC,'Exact existing original Runtime parent')
    baseline=standard_runtime.CONFIG;need(baseline['seed']==3701 and baseline['delay_ms']==20,'Original source default, never mutated')
    config=dict(baseline,seed=e['seed'],delay_ms=e['delay_ms']);need({k for k in baseline if baseline[k]!=config[k]}=={'seed','delay_ms'},'Only original constructor inputs change, not geometry or source')
    private=dict(fn.__globals__);private['CONFIG']=config
    local=FunctionType(fn.__code__,private,fn.__name__,fn.__defaults__,fn.__closure__);local.__kwdefaults__=fn.__kwdefaults__
    need(local.__code__ is fn.__code__ and standard_runtime.CONFIG is baseline,'No global aliases, restart, or old state')
    return local,e
