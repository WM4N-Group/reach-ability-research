"""Load Reach's actual common-domain methods using PUBLIC source projection only.

No private qualifier/route is imported; no native modules, data or world calls.
This is constructor wiring, not a new policy or a replayed hypothetical outcome.
"""
from pathlib import Path
import hashlib,importlib,sys
from complex_scene import public_task,finite_placements,need
from scene_driver import nav_declarations
METHOD_MODULES=('complex_public_model','complex_intent_planner','finite_multistep_planner')

def make_public_planner(scene,*,reach_source_root,expected_module_hashes,method,journal,limits=None):
    root=Path(reach_source_root).resolve(strict=True);prefix='research.task_conditioned_reachability.execution_preparation.'
    need(set(expected_module_hashes)==set(METHOD_MODULES),'Actual same A/B method sources must be frozen')
    modules={}
    for name in METHOD_MODULES:
        p=root/'research/task_conditioned_reachability/execution_preparation'/(name+'.py')
        need(not p.is_symlink()and hashlib.sha256(p.read_bytes()).hexdigest()==expected_module_hashes[name],'Frozen Reach source mismatch: '+name)
    sys.path.insert(0,str(root))
    for name in METHOD_MODULES:
        module=importlib.import_module(prefix+name);p=root/'research/task_conditioned_reachability/execution_preparation'/(name+'.py')
        need(Path(module.__file__).resolve()==p,'No other method checkout/module cache');modules[name]=module
    pub=public_task(scene);candidates=finite_placements(scene)
    model=modules['complex_public_model'].PublicSceneModel(pub,candidates,declared_initial_reference_xy_m=tuple(scene['robot_initial_xy_m']),nominal_envelope_radius_m=.45)
    limits=dict(max_depth=4,max_transitions=256,max_wall_s=.25)if limits is None else dict(limits)
    need(set(limits)=={'max_depth','max_transitions','max_wall_s'},'Exactly shared pre-outcome method ceilings')
    planner=modules['complex_intent_planner'].ComplexIntentPlanner(model,method=method,journal=journal,terminal_target_ref='cx-goal',
        nav_ref_by_xy={n['xy']:n['target_ref']for n in nav_declarations(scene)},**limits)
    planner.decision_source='reach_finite_public_algorithm';return planner
