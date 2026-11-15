"""Call Reach's pinned PUBLIC source-bound entry, never its private native input.

No direct-planner bypass of complete ordered IntentBatch catalogue validation.
This wrapper pins the original source files and public assets; it grants no
native/program/lease authority. All actual selection is Reach's implementation.
"""
from pathlib import Path
import hashlib,importlib,sys,json
from complex_scene import public_task,finite_placements,need
METHOD_MODULES=('complex_public_model','complex_intent_planner','finite_multistep_planner','complex_source_adapter')

def make_public_planner(scene,*,reach_source_root,expected_module_hashes,method,journal,limits=None,
                        public_task_path=None,finite_placements_path=None):
    root=Path(reach_source_root).resolve(strict=True);prefix='research.task_conditioned_reachability.execution_preparation.'
    need(set(expected_module_hashes)==set(METHOD_MODULES),'Actual same A/B FOUR method sources must be frozen')
    need(limits is None or limits==dict(max_depth=4,max_transitions=256,max_wall_s=.25),
         'Original source-bound common ceilings cannot be overridden')
    modules={}
    for name in METHOD_MODULES:
        p=root/'research/task_conditioned_reachability/execution_preparation'/(name+'.py')
        need(not p.is_symlink()and hashlib.sha256(p.read_bytes()).hexdigest()==expected_module_hashes[name],
             'Frozen Reach source mismatch: '+name)
    sys.path.insert(0,str(root))
    for name in METHOD_MODULES:
        module=importlib.import_module(prefix+name);p=root/'research/task_conditioned_reachability/execution_preparation'/(name+'.py')
        need(Path(module.__file__).resolve()==p,'No other method checkout/module cache');modules[name]=module
    own=Path(__file__).parent
    selection=json.loads((own/'SOURCE_SELECTION_V2.json').read_bytes())
    need(scene['scene_id']==selection['selected_scene_id'],'This new source-bound wrapper is v2 only; no silent v1 adaptation')
    task=own/selection['public_task_file']if public_task_path is None else Path(public_task_path).resolve(strict=True)
    placements=own/selection['finite_placements_file']if finite_placements_path is None else Path(finite_placements_path).resolve(strict=True)
    for path,key,value in [(task,'public_task_sha256',public_task(scene)),(placements,'finite_placements_sha256',finite_placements(scene))]:
        raw=path.read_bytes()
        need(hashlib.sha256(raw).hexdigest()==selection[key]and json.loads(raw)==json.loads(json.dumps(value)),
             'Exact public assets must equal the actual source scene projection')
    planner=modules['complex_source_adapter'].build_source_bound_planner(
        public_task_path=task,expected_task_sha256=selection['public_task_sha256'],
        finite_placements_path=placements,expected_placements_sha256=selection['finite_placements_sha256'],
        method=method,journal=journal,terminal_target_ref='cx-goal')
    # Only declares this host's explicit no-VLM/no-API path. Never changes method.
    planner.decision_source='reach_finite_public_algorithm';return planner
