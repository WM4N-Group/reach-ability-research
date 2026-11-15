"""Data-only V4 native asset/cold-runtime entry, default OFF; not a launcher.

Execute the exact original construction functions in a PRIVATE globals copy,
substituting only the three explicit V4 scene/asset/registry callbacks. Original
module objects/source, frozen runs, physics methods and guards are not patched.
This enables a necessary asset/camera component zero without pretending the
unqualified40cm/static-deck/five-arm main is ready.
"""
from pathlib import Path
import hashlib,importlib.util,sys,types
import v4_native_asset as v4

BASE_DIR=Path(__file__).resolve().parent.parent/'complex_dual_route_v1'
SOURCE_PINS={'native_construction.py': '6c3ee245cd54bfeeec0c64a53627ec2efbebba34775afcac7aab794a286b18cf', 'complex_scene.py': '613a18e735addf31edfe448e6f46e58ad0c130f4066c9b4393a8720d686d78c0', 'camera_abi.py': '3969490e368f47d944471f77c103e11cf369e9ff90726c2fbca9cf9dadad7617'}
REGISTRY_SHA='1d5baefee91a46d0b92f72663eff59b49eb7e7cc18754f95ef036458502566bf'

def _exact_base():
    for name,pin in SOURCE_PINS.items():
        path=BASE_DIR/name
        v4.require(not path.is_symlink()and hashlib.sha256(path.read_bytes()).hexdigest()==pin,'Exact source constructor dependency: '+name)
    sys.path.insert(0,str(BASE_DIR))
    # Private module name; no replacing globals/functions in an imported source.
    spec=importlib.util.spec_from_file_location('_ainav_v4_original_native_construction',BASE_DIR/'native_construction.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    import complex_scene
    v4.require(Path(complex_scene.__file__).resolve()==(BASE_DIR/'complex_scene.py').resolve(),'No ambient scene module')
    return module,complex_scene

def _v4_registry(scene,*,source_root):
    import importlib
    root=Path(source_root).resolve(strict=True);path=root/'ainav/native/scene_registry.py'
    v4.require(not path.is_symlink()and hashlib.sha256(path.read_bytes()).hexdigest()==REGISTRY_SHA,'Exact original registry API')
    sys.path.insert(0,str(root));api=importlib.import_module('ainav.native.scene_registry')
    v4.require(Path(api.__file__).resolve()==path,'No ambient registry API')
    return v4.registry(scene,api)

def _v4_construct(sim,*,scene=None,main_steps):
    _,base=_exact_base()
    import mujoco
    return v4.construct_into_native_spec(sim,scene=v4.load_scene()if scene is None else scene,
        main_steps=main_steps,base_module=base,expected_base_sha256=SOURCE_PINS['complex_scene.py'],mujoco_api=mujoco)

def _bound_original(name):
    original,_=_exact_base();function=getattr(original,name)
    namespace=dict(vars(original));namespace.update(__file__=str(Path(__file__).resolve()),
        load_scene=v4.load_scene,construct_into_native_spec=_v4_construct,registry=_v4_registry)
    bound=types.FunctionType(function.__code__,namespace,function.__name__,function.__defaults__,function.__closure__)
    bound.__kwdefaults__=dict(function.__kwdefaults__ or {})
    return bound

def compile_static_asset(*,enabled=False,**owner_kwargs):
    if type(enabled)is not bool:raise ValueError('Explicit owner opt-in only')
    if not enabled:return None
    result=_bound_original('compile_static_asset')(enabled=True,**owner_kwargs)
    result['V4_scene_asset_registry_callback_only']=True
    result['V4_whole_chain_or_method_admission']=False
    return result

def construct_cold_components(*,enabled=False,**owner_kwargs):
    if type(enabled)is not bool:raise ValueError('Explicit owner opt-in only')
    if not enabled:return None
    result=_bound_original('construct_cold_components')(enabled=True,**owner_kwargs)
    v4.require(result['registry'].goal.surface_ref=='goal_deck'and result['registry'].surfaces['goal_deck'].top_z_m==.6,'Actual elevated V4 registry, never ground-only fallback')
    result['V4_whole_chain_or_method_admission']=False
    return result
