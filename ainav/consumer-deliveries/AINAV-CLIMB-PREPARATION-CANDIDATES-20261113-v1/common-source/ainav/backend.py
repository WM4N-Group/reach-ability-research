"""Explicit frozen VLM provider selection; no provider/model fallback."""
import json
import os
from pathlib import Path


def active_profile():
    configured=os.environ.get('AINAV_VLM_PROFILE')
    path=Path(configured).resolve() if configured else Path(__file__).resolve().parents[1]/'vlm_profile.json'
    if not path.exists() and configured is None:path=Path(__file__).resolve().parents[2]/'config/vlm_profile.json'
    value=json.loads(path.read_text())
    if value.get('schema')!='ainav-active-vlm-profile-v1' or value.get('fallback_provider') is not None:raise ValueError('Explicit frozen VLM profile without fallback required')
    return path,value


def create_vision_backend(*,max_calls=24,max_tokens=8192,max_total_tokens=200000):
    path,p=active_profile()
    if p['provider']=='sol_gateway':
        from .sol_gateway import SolGatewayBackend
        verification=json.loads((path.parent/p['vision_verification_file']).read_text())
        return SolGatewayBackend(base_url=p['base_url'],model=p['model'],reasoning_effort=p['reasoning_effort'],
            vision_verification=verification,max_calls=max_calls,max_tokens=max_tokens,max_total_tokens=max_total_tokens)
    if p['provider']=='deepseek':
        from .deepseek import DeepSeekBackend
        return DeepSeekBackend(model=p['model'],max_calls=max_calls,max_tokens=max_tokens,max_total_tokens=max_total_tokens)
    raise ValueError('Unregistered VLM provider; no implicit fallback')
