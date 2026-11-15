"""Restore the exact original7a6 WM on CPU only; no forward/world/Actor/fit.

The original five-file inference closure is copied byte-for-byte, not patched or
retrained. Actual causal episode IO and native program qualification are separate.
Do not use this to revive a closed physical experiment or replay old inputs as live.
"""
import hashlib
import importlib
import json
import math
from pathlib import Path
import sys
from .v4_raw_wm_adapter import CHECKPOINT_SHA
from .v4_successor_choice import need


def file_sha(path):
    digest=hashlib.sha256()
    with Path(path).open('rb')as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):digest.update(block)
    return digest.hexdigest()


def validate_inference_closure(source_root):
    source=Path(source_root).resolve(strict=True)
    inventory=json.loads((source/'SOURCE_INVENTORY.json').read_bytes())
    expected={'visual_latent_behavior.py','visual_latent_control.py','visual_latent_highres.py',
              'visual_latent_world_model.py','visual_shadow_model.py'}
    need(inventory['checkpoint_sha256']==CHECKPOINT_SHA and set(inventory['files'])==expected,
         'Exact original inference-only closure')
    for name,row in inventory['files'].items():
        path=source/name
        need(path.is_file()and not path.is_symlink()and file_sha(path)==row['sha256'],
             'Original inference source drift: '+name)
        module=sys.modules.get(Path(name).stem)
        need(module is None or Path(module.__file__).resolve()==path,
             'No cached different world-model namespace')
    return source,inventory


def restore_original_cpu(checkpoint, *, source_root):
    """Returns frozen model/normalization and scalar provenance, never predicts."""
    source,inventory=validate_inference_closure(source_root)
    path=Path(checkpoint)
    # Historical physical roots are not opened beyond this explicit read-only weight.
    need(path.is_file()and file_sha(path)==CHECKPOINT_SHA, 'Exact existing original7a6 checkpoint')
    sys.path.insert(0,str(source))
    try:
        import torch
        torch.set_num_threads(2)
        api=importlib.import_module('visual_latent_behavior')
        need(Path(api.__file__).resolve()==source/'visual_latent_behavior.py','Exact loaded original BehaviorM module')
        saved=torch.load(path,map_location='cpu',weights_only=True)
        model=api.load_behavior_checkpoint(saved).to('cpu').eval()
        model.requires_grad_(False)
        normalization=saved['normalization']
        need(set(normalization)>={'mean','std'} and len(normalization['mean'])==len(normalization['std'])==45,
             'Exact original45D normalization, not recomputed from V4')
        need(all(type(x)in(int,float)and math.isfinite(x)for x in normalization['mean'])and
             all(type(x)in(int,float)and math.isfinite(x)and x>0 for x in normalization['std']),
             'Finite original frozen normalization')
        need(str(model.device)=='cpu'and model.training is False and
             not any(p.requires_grad for p in model.parameters()),'CPU frozen-eval inference only')
        need(file_sha(path)==CHECKPOINT_SHA,'Checkpoint unchanged while restoring')
        validate_inference_closure(source)
        model._reach_original_checkpoint_sha256=CHECKPOINT_SHA
        report=dict(checkpoint_path=str(path),checkpoint_sha256=CHECKPOINT_SHA,checkpoint_bytes=path.stat().st_size,
            actual_model_class=type(model).__name__,architecture_id=saved['architecture_id'],
            contract_sha256=saved['contract_sha256'],normalization_sha256=hashlib.sha256(json.dumps(normalization,sort_keys=True).encode()).hexdigest(),
            source_file_sha256={n:r['sha256']for n,r in inventory['files'].items()},
            device='cpu',eval_mode=True,all_gradients_disabled=True,
            parameters=sum(p.numel()for p in model.parameters()),real_checkpoint_restores=1,
            actual_WM_prediction_forwards=0,actual_native_worlds_or_Actor_forwards=0,fit_or_optimizer_steps=0,
            current_V4_causal_query_not_constructed=True,V4_policy_or_native_qualification_claimed=False)
        return model,normalization,report
    finally:
        sys.path.remove(str(source))
