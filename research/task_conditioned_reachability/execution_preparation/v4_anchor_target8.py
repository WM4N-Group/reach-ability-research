"""Original visible-plane target8 on the WM's actual 64x96 anchor, not VLM RGB.

No native target/body association or world-goal inference is performed here.
The caller must associate each public semantic candidate on THIS resized image.
Missing/ambiguous/failed planes remain None, not a fabricated valid target or
masked-zero workaround. Original model mask0 is legal but this method's existing
abstention policy remains unchanged. No WM/model/renderer/trainer is imported.
"""
import ast
import copy
import hashlib
import json
import math
from pathlib import Path
import sys
import types
from .v4_successor_choice import need

PINS = {
    'visual_box_proposals.py': '837e95ecd7bc3249154b8a53097f71fd90974a2df9fb4a35d87116d0254af304',
    'visible_surface_goal.py': 'b7ccf787db0db1e8496d2d6627e9efeb941bb6c06d7638791ce1628a81068da4',
    'geometry_vector.py': 'f02cbefb7dca72cc5b4f0b54014eb3af0aa8e5eda8faa0c9bab432f4ae9d137f',
}


_ORIGINAL_GEOMETRY_API = None

def checked_geometry_sources(root):
    root = Path(root).resolve(strict=True)
    manifest = json.loads((root/'SOURCE_INVENTORY.json').read_bytes())
    need(manifest['role'] == 'ORIGINAL_VISIBLE_RGBD_GEOMETRY_ONLY_NO_TRAINER_NATIVE_OR_WEIGHTS'
         and set(manifest['files']) == set(PINS), 'Exact inference-only geometry closure')
    sources = {}
    for name, expected in PINS.items():
        path = root/name
        need(path.is_file() and not path.is_symlink(), 'Regular original geometry source')
        raw = path.read_bytes()
        need(hashlib.sha256(raw).hexdigest() == expected == manifest['files'][name]['custody_sha256'],
             'Original geometry source pin: '+name)
        sources[name] = (path, raw)
    tree = ast.parse(sources['geometry_vector.py'][1])
    need(len(tree.body) == 1 and isinstance(tree.body[0],ast.FunctionDef)
         and tree.body[0].name == 'geometry_vector', 'Only exact vector function, no trainer import')
    return sources


def load_original_geometry(root):
    """Private namespaces: never shadow an ambient visual_box_proposals module."""
    global _ORIGINAL_GEOMETRY_API
    sources = checked_geometry_sources(root)
    if _ORIGINAL_GEOMETRY_API is not None:
        return _ORIGINAL_GEOMETRY_API
    import numpy as np
    modules = []
    def execute(name, raw, path, bindings=None, *, private_visual_import=False):
        key = '_reach_original_geometry_'+name
        need(key not in sys.modules, 'One explicit geometry closure per process, no module replacement')
        module = types.ModuleType(key); module.__file__ = str(path)
        if bindings: module.__dict__.update(bindings)
        tree = ast.parse(raw)
        if private_visual_import:
            imports = [node for node in tree.body if isinstance(node,ast.ImportFrom) and node.module == 'visual_box_proposals']
            need(len(imports) == 1 and all(alias.asname is None and alias.name in bindings
                 for alias in imports[0].names), 'Only redirect exact original visual import into private bindings')
            tree.body.remove(imports[0])  # Definitions/algorithms stay byte-identical; only import resolution is private.
        sys.modules[key] = module; modules.append(key)
        exec(compile(tree,str(path),'exec'),module.__dict__)
        return module
    try:
        path,raw = sources['visual_box_proposals.py']; visual = execute('proposals',raw,path)
        names = ('ProposalConfig','propose_visual_candidates','single_visible_hypothesis','_hsv','_components','HUE_FAMILIES')
        path,raw = sources['visible_surface_goal.py']
        goal = execute('surface',raw,path,{name:getattr(visual,name) for name in names},private_visual_import=True)
        path,raw = sources['geometry_vector.py']; vector = execute('vector',raw,path,{'np':np})
        _ORIGINAL_GEOMETRY_API = types.SimpleNamespace(describe_visible_goal=goal.describe_visible_goal,
            geometry_vector=vector.geometry_vector, visual_calibration_sha=visual.visual_calibration_sha,
            propose_visual_candidates=visual.propose_visual_candidates, source_pins=dict(PINS))
        return _ORIGINAL_GEOMETRY_API
    except Exception:
        for key in modules: sys.modules.pop(key,None)
        raise


class AnchorTarget8Provider:
    """Direct target_provider for CausalWMQueryPort. This is not a native binder."""
    def __init__(self, *, geometry_source_root=None, association_provider=None,
                 software_fixture=False, fixture_api=None):
        need(type(software_fixture) is bool, 'Explicit software-only fixture mode')
        need(association_provider is None or callable(association_provider), 'Actual source association callback')
        need(fixture_api is None or software_fixture, 'Fixture geometry cannot become production target producer')
        self.software_fixture = software_fixture
        self.api = fixture_api if fixture_api is not None else load_original_geometry(geometry_source_root)
        self.associate = association_provider

    def __call__(self, observation, options, anchor):
        if not self.software_fixture:
            from ainav.contracts import Observation
            from ainav.intents import SkillIntent
            need(type(observation) is Observation and all(type(o) is SkillIntent for o in options),
                 'Only original public semantic candidates, never private ExecutionBatch/body targets')
        need(tuple(anchor['rgb'].shape) == (64,96,3) and tuple(anchor['depth_m'].shape) == (64,96),
             'Exact original WM resized RGBD anchor, never fresh VLM/onboard pixel refs')
        need(-1e-7 <= observation.time_s-anchor['time_s'] <= .100001, 'Current original WM anchor clock')
        source_anchor = anchor
        anchor = copy.deepcopy(anchor)  # Small current pixel/calibration copy, never writable source history.
        anchor_time = anchor['time_s']
        rgb_sha = hashlib.sha256(anchor['rgb'].tobytes()).hexdigest()
        depth_sha = hashlib.sha256(anchor['depth_m'].tobytes()).hexdigest()
        calibration = self.api.visual_calibration_sha(anchor['camera_K'],anchor['T_base_optical'])
        keys = {o.sha256 for o in options}
        need(len(keys) == len(options), 'Distinct exact same-query public candidates')
        selected = {key:None for key in keys}
        if self.associate is not None:
            association = self.associate(observation,tuple(options),anchor)
            need(set(association) == {'WM_anchor_RGB_bytes_sha256','WM_anchor_time_s',
                 'WM_anchor_calibration_sha256','frame_local_ref_by_option_sha256'}, 'Public same-anchor association only')
            need(association['WM_anchor_RGB_bytes_sha256'] == rgb_sha
                 and association['WM_anchor_time_s'] == anchor['time_s']
                 and association['WM_anchor_calibration_sha256'] == calibration,
                 'No old alias, raw onboard or other off-grid image/calibration association')
            selected = association['frame_local_ref_by_option_sha256']
            need(set(selected) == keys, 'Explicit association or missing mask for every candidate')
        targets = {}; evidence = {}
        for option in options:
            row = selected[option.sha256]
            targets[option.sha256] = None
            if row is None:
                evidence[option.sha256] = dict(status='UNKNOWN', reason='NO_CURRENT_WM_ANCHOR_PUBLIC_SEMANTIC_ASSOCIATION')
                continue
            need(set(row) == {'frame_local_ref','declared_standoff_m'}
                 and type(row['frame_local_ref']) is str and bool(row['frame_local_ref'])
                 and type(row['declared_standoff_m']) in (float,int)
                 and math.isfinite(row['declared_standoff_m']) and .5 <= row['declared_standoff_m'] <= 1.5,
                 'Only same-frame visual ref and original bounded declared diagnostic standoff, not hidden world pose')
            try:
                proof = self.api.describe_visible_goal(anchor['rgb'],anchor['depth_m'],anchor['camera_K'],
                    anchor['T_base_optical'],frame_local_ref=row['frame_local_ref'],
                    current_RGB_sha256=rgb_sha,standoff_m=row['declared_standoff_m'])
            except ValueError as error:
                # Original missing/ambiguous RGBD/plane rejection does not get a valid zero target.
                evidence[option.sha256] = dict(status='UNKNOWN',reason='ORIGINAL_VISIBLE_PLANE_REFUSED',
                    original_reason=str(error))
                continue
            need(proof['RGB_sha256'] == rgb_sha and proof['calibration_sha256'] == calibration
                 and proof['frame_local_ref'] == row['frame_local_ref']
                 and proof['uses_only_current_RGBD_and_calibration'] is True
                 and proof['physical_action_admitted'] is False, 'Original current visible-only proof')
            vector = tuple(float(v) for v in self.api.geometry_vector(proof))
            need(len(vector) == 8 and all(math.isfinite(v) for v in vector) and vector[7] == 1.,
                 'Exact observed plane descriptor, never imputed target8')
            targets[option.sha256] = vector
            evidence[option.sha256] = dict(status='CURRENT_VISIBLE_PLANE_NOT_NATIVE_ASSOCIATION_OR_WORLD_POSE',
                frame_local_ref=row['frame_local_ref'],proof_sha256=hashlib.sha256(
                    json.dumps(proof,sort_keys=True,allow_nan=False).encode()).hexdigest())
        need(anchor['time_s'] == anchor_time
             and hashlib.sha256(anchor['depth_m'].tobytes()).hexdigest() == depth_sha
             and hashlib.sha256(anchor['rgb'].tobytes()).hexdigest() == rgb_sha
             and self.api.visual_calibration_sha(anchor['camera_K'],anchor['T_base_optical']) == calibration,
             'Read-only geometry callback cannot change its anchor snapshot')
        need(source_anchor['time_s'] == anchor_time
             and hashlib.sha256(source_anchor['rgb'].tobytes()).hexdigest() == rgb_sha
             and hashlib.sha256(source_anchor['depth_m'].tobytes()).hexdigest() == depth_sha
             and self.api.visual_calibration_sha(source_anchor['camera_K'],source_anchor['T_base_optical']) == calibration,
             'Actual source anchor changed during descriptor construction')
        return dict(WM_anchor_RGB_bytes_sha256=rgb_sha,WM_anchor_time_s=anchor['time_s'],
            target8_by_option_sha256=targets,target8_evidence_by_option_sha256=evidence,
            geometry_source_pins=dict(self.api.source_pins),
            source_role='EXPLICIT_SOFTWARE_FIXTURE_NOT_MODEL_TASK_INPUT' if self.software_fixture else
                        'ORIGINAL_VISIBLE_GEOMETRY_ON_CURRENT_WM_ANCHOR_NOT_NATIVE_TARGET_BINDING')
