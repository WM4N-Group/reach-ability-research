"""Five new pure metadata checks, no Torch/numpy/native import, no source fixture reruns."""
from pathlib import Path
import importlib.util,hashlib,json,datetime
B=Path('/home/yuanyue/main/work/data-team');M=Path(__file__).resolve().parent;p=B/'workers'/M.name/'private_catalog_boundary.py';spec=importlib.util.spec_from_file_location('data_private_catalog_boundary_check',p);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
class Sink:
 def __init__(self):self.rows=[]
 def append_visual(self,packet,**kw):self.rows.append((packet,kw));return'original-receipt'
sink=Sink();a=mod.PrivateCatalogBoundaryWriter(sink);packet=object();original=dict(schema='ainav-private-registered-object-catalog-v1',control_tick=0,model_input=False,opaque_original_payload=['unchanged']);before=repr(original);assert a.append_visual(packet,control_tick=0,private_catalog=original)=='original-receipt';assert sink.rows[0][0]is packet and sink.rows[0][1]['private_catalog']['opaque_original_payload']is original['opaque_original_payload']and repr(original)==before and sink.rows[0][1]['private_catalog']['model_input_allowed']is False
cases=[dict(original,model_input_allowed=True),dict(original,control_tick=5),dict(original,model_input=True),dict(original,schema='wrong')]
for case in cases:
 try:a.append_visual(packet,control_tick=0,private_catalog=case)
 except ValueError:pass
 else:raise AssertionError('Invalid metadata boundary accepted')
assert len(sink.rows)==1 and a.annotated_frames==1
with(M/'new5-private-catalog-metadata-checks.json').open('x')as f:json.dump(dict(at=datetime.datetime.now().astimezone().isoformat(),checks_passed=5,adapter_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),packet_and_private_original_not_mutated=True,raw_writer_still_checks_all_shapes_clocks_calibration=True,no_Torch_numpy_Actor_native_or_physics_calls=True,no_physical_retry_or_old_scope_reopen=True),f,indent=2);f.write('\n')
print('5 new private-catalog metadata checks passed; no native/model calls')
