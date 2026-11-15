"""Bind the explicitly selected V4 TLS DeepSeek profile WITHOUT constructing API.

Read only public profile and exact original backend source. No environment/key
inspection, request, model-list probe or transport creation. Data constructs the
backend once in its own frozen program with protected process-level injection.
"""
import hashlib
import json
from pathlib import Path
from .v4_successor_choice import need

PROFILE_SHA='87d38fefc86401a74de77933fe36d3d21c2fd047f61e897d37387df7f640f103'
BACKEND_SHA='11e5fdd868a41aa008469db6eb04f31d451c9e8cb35943fd65580573430a5919'


def runtime_binding(profile_path, *, original_backend_path, max_calls=100,
                    max_tokens=8192, max_total_tokens=1000000):
    """Return exact original-constructor kwargs, not an authenticated readiness claim."""
    profile_path=Path(profile_path);source_path=Path(original_backend_path)
    need(profile_path.is_file() and not profile_path.is_symlink() and source_path.is_file()
         and not source_path.is_symlink(), 'Explicit existing public profile and original backend source')
    raw=profile_path.read_bytes();need(hashlib.sha256(raw).hexdigest()==PROFILE_SHA, 'Exact AINav user-selected V4 profile')
    need(hashlib.sha256(source_path.read_bytes()).hexdigest()==BACKEND_SHA, 'Exact original TLS DeepSeek constructor')
    profile=json.loads(raw)
    need(profile['schema']=='AINav-V4-explicit-DeepSeek-runtime-profile-v1' and profile['provider']=='deepseek'
         and profile['base_url']=='https://api.deepseek.com' and profile['model']=='deepseek-flash'
         and profile['thinking']=='disabled' and profile['transport_TLS'] is True
         and profile['fallback_provider'] is None and profile['original_backend_sha256']==BACKEND_SHA,
         'No implicit provider/model or old HTTP fallback')
    # This is the constructor's actual immutable bound, not an economic limit.
    # Passing the earlier proposed256 would be refused BEFORE any real run.
    need(type(max_calls) is int and 1<=max_calls<=100 and type(max_tokens) is int and 64<=max_tokens<=8192
         and type(max_total_tokens) is int and 1<=max_total_tokens<=1000000,
         'Respect exact original backend API call/token constructor limits')
    return dict(constructor='ainav.deepseek.DeepSeekBackend',
        kwargs=dict(model='deepseek-flash',max_calls=max_calls,max_tokens=max_tokens,
                    max_total_tokens=max_total_tokens,verify_models=True),
        profile_sha256=PROFILE_SHA,backend_source_sha256=BACKEND_SHA,
        official_TLS_endpoint='https://api.deepseek.com',credential_injection='EXISTING_PROTECTED_PROCESS_ONLY',
        credentials_read_or_persisted=False,backend_constructed=False,actual_API_calls=0,
        authenticated_model_metadata_and_actual_served_identity_still_required=True,
        E_calls=0,A_D_same_constructor_limits=True)
