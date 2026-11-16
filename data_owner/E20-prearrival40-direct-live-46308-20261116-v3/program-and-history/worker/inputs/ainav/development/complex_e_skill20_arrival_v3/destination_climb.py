"""Private destination-height binder using the unchanged original CLIMB machine.

Public SkillIntent/BehaviorOption keeps its DESTINATION parameter and hash.
Only the private ClimbBinding derives SOURCE height from the actual support
witness/registry. Original20cm terrain/current RGBD/body/geometry checks remain.
Static deck mapping and a40cm rise are NOT enabled by this source.
"""
from pathlib import Path
import ast,hashlib,importlib,sys,textwrap,math
from v4_native_asset import require
ORIGINAL_CLIMB_SHA='fed57c56ad2c13ed5541e7af6f2c2cb31f4dcac0b5e8d8feb05383b22ad3e78a'
ORIGINAL_TERRAIN_SHA='1d5baefee91a46d0b92f72663eff59b49eb7e7cc18754f95ef036458502566bf'
ORIGINAL_EXECUTOR_SHA='8d42281aa890bd5224f7d8c0bacc2c44d1fa1bda0ba5a89fec8bffa59f701995'
OLD_HEIGHT="obj=objects[0];height=dict(option.parameters)['surface_height_m']"
NEW_HEIGHT="""obj=objects[0];destination=dict(option.parameters)['surface_height_m']
            if type(destination)not in(int,float)or not math.isfinite(destination):raise ValueError('Finite public destination required')
            if source_support_ref not in self.registry.surfaces:raise ValueError('Actual declared source support required')
            height=self.registry.surfaces[source_support_ref].top_z_m"""
OLD_GEOMETRY="geometry=terrain.climb_geometry(self.runtime.sim,obj.ref,source_surface_height_m=height)"
NEW_GEOMETRY=OLD_GEOMETRY+"\n            if abs(geometry['top']-destination)>.01:raise ValueError('Public destination differs from actual selected target top in original20cm domain')"

def _changed_bind_source(text):
    cls=next(n for n in ast.parse(text).body if isinstance(n,ast.ClassDef)and n.name=='RegisteredClimbAdapter');fn=next(n for n in cls.body if isinstance(n,ast.FunctionDef)and n.name=='bind');original=ast.get_source_segment(text,fn)
    require(original.count(OLD_HEIGHT)==original.count(OLD_GEOMETRY)==1,'Exact narrow original CLIMB source pattern')
    changed=original.replace(OLD_HEIGHT,NEW_HEIGHT,1).replace(OLD_GEOMETRY,NEW_GEOMETRY,1).replace('public SOURCE height only','public DESTINATION height only')
    inverse=changed.replace(NEW_GEOMETRY,OLD_GEOMETRY,1).replace(NEW_HEIGHT,OLD_HEIGHT,1).replace('public DESTINATION height only','public SOURCE height only')
    require(inverse==original,'Source delta must invert exactly, no deleted checks')
    return textwrap.dedent(changed),original

def adapter_class(*,source_root=None,enabled=False):
    require(type(enabled)is bool,'Explicit owner opt-in')
    if not enabled:return None
    root=Path(source_root).resolve(strict=True);pinfiles={'ainav/native/registered_climb.py':ORIGINAL_CLIMB_SHA,'ainav/native/scene_registry.py':ORIGINAL_TERRAIN_SHA,'mujoco_zyh/native_behavior_executor.py':ORIGINAL_EXECUTOR_SHA}
    for name,pin in pinfiles.items():
        p=root/name;require(not p.is_symlink()and hashlib.sha256(p.read_bytes()).hexdigest()==pin,'Exact original destination-binding dependency: '+name)
    sys.path.insert(0,str(root));module=importlib.import_module('ainav.native.registered_climb');api=importlib.import_module('mujoco_zyh.native_behavior_executor')
    require(Path(module.__file__).resolve()==root/'ainav/native/registered_climb.py'and Path(api.__file__).resolve()==root/'mujoco_zyh/native_behavior_executor.py','No ambient native source')
    changed,original=_changed_bind_source((root/'ainav/native/registered_climb.py').read_text());namespace=dict(vars(module));namespace['math']=math;exec(compile(changed,str(root/'ainav/native/registered_climb.py')+'[V4-private-source/public-destination]','exec'),namespace);bind_destination=namespace['bind']
    class DestinationClimbAdapter(module.RegisteredClimbAdapter):
        def bind(self,batch,options,source_support_ref,*,witness=None):
            require(witness is not None and callable(getattr(witness,'validate',None))and witness.support_ref==source_support_ref,'Actual matching source owner witness required')
            from ainav.intents import ExecutionBatch
            require(type(batch)is ExecutionBatch and type(options)is tuple and len(options)==1 and options==batch.options,'One original selected private ExecutionBatch only')
            require(abs(batch.observation.time_s-float(self.runtime.sim.data.time))<=1e-7,'Actual current CLIMB query clock')
            batch.observation.verify_image()
            before=api.world_snapshot(self.runtime);witness.validate(self.runtime)
            result=bind_destination(self,batch,options,source_support_ref)
            require(api.world_snapshot(self.runtime)==before,'Private CLIMB binding changed original world/FIFO')
            for option in options:
                b=result[option.sha256];geometry=dict(b.geometry)
                self.journal(dict(event='V4_CLIMB_public_destination_private_source_bound',query_sha256=batch.sha256,
                    native_option_sha256=option.sha256,public_destination_height_m=dict(option.parameters)['surface_height_m'],
                    private_source_support_ref=source_support_ref,private_source_height_m=geometry['base_height'],
                    current_target_top_m=geometry['top'],original_option_parameters_and_hash_unchanged=True,
                    original20cm_geometry_gate_retained=True,native_controller_constructed=False,model_input=False))
            return result
    DestinationClimbAdapter.source_delta_receipt=dict(original_source_sha256=ORIGINAL_CLIMB_SHA,original_terrain_sha256=ORIGINAL_TERRAIN_SHA,
        changed_method='bind only: private witnessed SOURCE separate from public DESTINATION',original_construct_inherited_unchanged=True,
        source_delta_exactly_invertible=True,original_option_and_receipt_hashes_not_rewritten=True,static_surface_or40cm_rise_not_admitted=True,
        native_runtime_or_dynamic_qualification=False)
    return DestinationClimbAdapter
