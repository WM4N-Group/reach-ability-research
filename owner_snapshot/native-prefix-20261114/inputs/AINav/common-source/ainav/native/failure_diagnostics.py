"""Bounded private controller-reference snapshot, never model input/control."""
import math
import traceback

_FIELDS=('phase','kind','index','reference','velocity','compact_goal','unload_target',
         'reference_start','segment_start','segment_origin','segment_duration',
         'started','metrics','com_goal','base_goal','goal','reference_receipts')
_CHILDREN=('native_machine','native','stow','preparation')


def _plain(value):
    if hasattr(value,'tolist'):value=value.tolist()
    if value is None or type(value) in (str,int,bool):return value
    if type(value) is float:return value if math.isfinite(value) else None
    if isinstance(value,(list,tuple)):return [_plain(v) for v in value]
    if isinstance(value,dict):return {str(k):_plain(v) for k,v in value.items()}
    raise TypeError('Not a diagnostic scalar/array')


def terminal_snapshot(host,error):
    session=getattr(getattr(host,'executor',None),'session',None)
    root=getattr(session,'machine',None);nodes=[];seen=set()
    def visit(obj,path,depth):
        if obj is None or id(obj) in seen or depth>5 or not hasattr(obj,'__dict__'):return
        seen.add(id(obj));state=vars(obj);fields={}
        for name in _FIELDS:
            if name in state:
                try:fields[name]=_plain(state[name])
                except TypeError:continue
        nodes.append(dict(path=path,type=type(obj).__name__,fields=fields))
        for name in _CHILDREN:visit(state.get(name),path+'.'+name,depth+1)
    visit(root,'machine',0)
    return dict(event='private_terminal_controller_failure',model_input=False,
        live_state_written=False,physics_steps=0,nodes=nodes,
        traceback=[dict(file=f.filename,line=f.lineno,function=f.name)
                   for f in traceback.extract_tb(error.__traceback__)])
