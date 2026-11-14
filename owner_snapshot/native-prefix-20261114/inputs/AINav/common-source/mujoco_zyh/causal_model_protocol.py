from pathlib import Path
import json
SCHEMA='piper-causal-task-model-full1-transfer-v1'
def validate(p):
    profiles=json.loads(Path(__file__).with_name('causal_model_profiles.json').read_text())
    if p not in profiles.values():raise ValueError('Exact fresh model task profile required')
    from .integrated_course import protocol,validate_protocol
    base=protocol(p['integrated_case']);validate_protocol(base)
    extra={'causal_model_policy','public_control_proprio_hz'}
    if set(p)!=(set(base)|extra):raise ValueError('Native/base model profile key set differs')
    changed={'schema','source_id','episode_id','source_group','purpose','role','WM_control','seed'}
    for key in base:
        if key not in changed and p[key]!=base[key]:raise ValueError('Native resource/physical/safety contract changed: '+key)
    if p['seed']!=4301 or p['role']!='development' or p['training_allowed'] or p['training_runs']!=0 or not p['WM_control'] or p['public_control_proprio_hz']!=50:raise ValueError('Inference-only original seen full1 transfer required')
    m=p['causal_model_policy']
    if m['method'] not in ('dino','dreamer') or m['candidate_dx_m']!=[-.02,0.,.02] or m['response_timeout_s']!=60:raise ValueError('Registered causal choice envelope differs')
    return p
