"""Bind the explicitly selected V4 TLS DeepSeek profile WITHOUT constructing API.

Read only public profile, exact original backend and full-course constructor source. No environment/key
inspection, request, model-list probe or transport creation. Data constructs the
backend once in its own frozen program with protected process-level injection.
"""
import ast
import hashlib
import json
from pathlib import Path
from .v4_successor_choice import need

PROFILE_SHA='87d38fefc86401a74de77933fe36d3d21c2fd047f61e897d37387df7f640f103'
BACKEND_SHA='11e5fdd868a41aa008469db6eb04f31d451c9e8cb35943fd65580573430a5919'
FULL_COURSE_SHA='038ce0455eba232755d6bf1354131a5c907964a9c084588c108e49bd9846b952'


def original_full_course_limits(path):
    """Parse the selected C/D profile; never import or execute its launcher."""
    path=Path(path)
    need(path.is_file() and not path.is_symlink(), 'Exact original full-course constructor profile source')
    raw=path.read_bytes()
    need(hashlib.sha256(raw).hexdigest()==FULL_COURSE_SHA,
         'Exact original full-course constructor profile source')
    tree=ast.parse(raw)
    calls=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and
           isinstance(n.func,ast.Name) and n.func.id=='create_vision_backend']
    need(len(calls)==1 and not calls[0].args and all(k.arg is not None for k in calls[0].keywords),
         'One explicit original full-course backend constructor declaration')
    limits={k.arg:ast.literal_eval(k.value) for k in calls[0].keywords}
    need(limits==dict(max_calls=100,max_tokens=8192,max_total_tokens=900000),
         'Selected full-course common capacity, not just backend implementation maximum')
    return limits


def runtime_binding(profile_path, *, original_backend_path, max_calls=100,
                    max_tokens=8192, max_total_tokens=900000, original_full_course_path=None):
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
    full_course_path=(source_path.parent.parent/'run_full_course.py' if original_full_course_path is None
                      else Path(original_full_course_path))
    common=original_full_course_limits(full_course_path)
    requested=dict(max_calls=max_calls,max_tokens=max_tokens,max_total_tokens=max_total_tokens)
    need(requested==common, 'V4 A-D must use the same original full-course API capacity')
    return dict(constructor='ainav.deepseek.DeepSeekBackend',
        kwargs=dict(model='deepseek-flash',max_calls=max_calls,max_tokens=max_tokens,
                    max_total_tokens=max_total_tokens,verify_models=True),
        profile_sha256=PROFILE_SHA,backend_source_sha256=BACKEND_SHA,
        original_full_course_source_sha256=FULL_COURSE_SHA,original_full_course_api_limits=common,
        all_four_actual_backend_instances_compared=False,
        official_TLS_endpoint='https://api.deepseek.com',credential_injection='EXISTING_PROTECTED_PROCESS_ONLY',
        credentials_read_or_persisted=False,backend_constructed=False,actual_API_calls=0,
        authenticated_model_metadata_and_actual_served_identity_still_required=True,
        E_calls=0,A_D_same_constructor_limits=True)
