"""Default-off original C/D AINav backbone assembly, not a method/dispatcher.

Accept an ALREADY constructed owner-verified original DeepSeek backend. Never
construct a backend, inspect a key/opener/environment, verify a remote model or
call generate. Reuse exact RoleRunner/AinavPlanner and the original full-course
constructor profile. Reach must wrap the returned original planner for C/D.
"""
from pathlib import Path
from types import MappingProxyType
import ast,hashlib,importlib,json,sys,threading,weakref
from v4_native_asset import require

PINS={
 'ainav/__init__.py':'635f91e2b609936a023e0563ca7ee975cef75110a3822ff3b9c9665d8d3b84b6',
 'ainav/contracts.py':'7d995f5a1dcb7135e1ca16d36e391a511bb8c8cefa0aeafd27430eba0932a669',
 'ainav/tree.py':'5091e340fb267b3a6455685526a343988653a39cf356176e41d46200718ae931',
 'ainav/planner.py':'fef70edb687dd7e3c9597cb04df24c74795bfde6c77a667457210c0f8040543a',
 'ainav/vlm.py':'1d044c833c8eb3858ce6b8f76e02634827de43278c21890c9fd164f2dd2198ee',
 'ainav/deepseek.py':'11e5fdd868a41aa008469db6eb04f31d451c9e8cb35943fd65580573430a5919',
 'ainav/intents.py':'257d5df748a932bd8b274ea308e823478c17d17ed5cb8fb217cc1986b1f49b76',
 'run_full_course.py':'038ce0455eba232755d6bf1354131a5c907964a9c084588c108e49bd9846b952',
}
_CLAIMED_BACKENDS=weakref.WeakSet()
_CLAIM_LOCK=threading.Lock()


def _original_types(source_root):
    root=Path(source_root).resolve(strict=True)
    for name,pin in PINS.items():
        p=root/name
        require(not p.is_symlink()and hashlib.sha256(p.read_bytes()).hexdigest()==pin,
                'Exact selected full AINav backbone dependency: '+name)
    sys.path.insert(0,str(root));modules={}
    for name in ['ainav','ainav.contracts','ainav.tree','ainav.planner','ainav.vlm','ainav.deepseek','ainav.intents']:
        module=importlib.import_module(name)
        path=root/('ainav/__init__.py'if name=='ainav'else name.replace('.','/')+'.py')
        require(Path(module.__file__).resolve()==path,'No ambient original backbone module: '+name)
        modules[name]=module
    return root,modules


def _full_course_profile(root):
    # Parse declarations only; NEVER import/execute the old launcher.
    tree=ast.parse((root/'run_full_course.py').read_bytes());profile={}
    for name,label,args in [('create_vision_backend','backend_caps',()),
                            ('RoleRunner','roles',('backend','journal')),
                            ('AinavPlanner','planner',('roles','journal'))]:
        calls=[n for n in ast.walk(tree)if isinstance(n,ast.Call)and isinstance(n.func,ast.Name)and n.func.id==name]
        require(len(calls)==1 and tuple(ast.unparse(n)for n in calls[0].args)==args,
                'One exact original full-course constructor declaration: '+name)
        require(all(k.arg is not None for k in calls[0].keywords),'No guessed original constructor overrides')
        profile[label]={k.arg:ast.literal_eval(k.value)for k in calls[0].keywords}
    return profile


def _checked_backend(backend,backend_type,profile):
    require(type(backend)is backend_type,'Already constructed exact original DeepSeek backend required; no fake/fallback')
    configuration=json.loads(Path(__file__).with_name('VLM_PROFILE.json').read_bytes())
    require(configuration['provider']=='deepseek'and configuration['transport_TLS']is True
            and configuration['fallback_provider']is None,'Explicit selected DeepSeek profile only')
    identity=backend.identity
    require(type(identity)is dict and identity.get('provider')=='DeepSeek'
            and identity.get('endpoint')==configuration['base_url']+'/chat/completions'
            and identity.get('requested_model')==backend.model==configuration['model']
            and identity.get('thinking')=='disabled','Existing verified backend identity must match shared V4 provider')
    cap=identity.get('model_capability',{})
    require(type(cap)is dict and cap.get('id')==configuration['model']
            and {'text','image'}<=set(cap.get('input_modalities',())),
            'Existing original authenticated image capability metadata required, no new probe')
    digest=identity.get('model_list_sha256')
    require(type(digest)is str and len(digest)==64 and all(c in '0123456789abcdef'for c in digest),
            'Existing original non-secret model metadata digest required')
    for name,value in profile['backend_caps'].items():
        require(type(getattr(backend,name,None))is int and getattr(backend,name)==value
                and identity.get(name)==value,'Preserve original full-course API capacity: '+name)
    require(type(backend.calls)is int and backend.calls==0 and type(backend.total_tokens)is int
            and backend.total_tokens==0,'Fresh owner backend only; no old arm/failed episode counters reset')
    # Whitelist only public identity/limits. Never hash/serialize __dict__, a
    # credential, opener, headers, arbitrary capability fields or raw transport.
    return dict(provider='DeepSeek',requested_model=backend.model,endpoint=identity['endpoint'],
        thinking='disabled',model_list_sha256=digest,**profile['backend_caps'])


def build_original_ainav_backbone(*,enabled=False,arm=None,source_root=None,backend=None,journal=None,guard=None):
    require(type(enabled)is bool,'Explicit owner opt-in')
    if not enabled:return None
    require(arm in ('C','D'),'This entry assembles original C/D only; never replace A/B or E')
    require(callable(guard)and callable(journal),'Actual owner guard and shared durable journal')
    require(guard()is not False,'Owner refused original backbone assembly')
    root,modules=_original_types(source_root);profile=_full_course_profile(root)
    identity=_checked_backend(backend,modules['ainav.deepseek'].DeepSeekBackend,profile)
    with _CLAIM_LOCK:
        require(backend not in _CLAIMED_BACKENDS,'One fresh original backbone per owner backend, no replacement/retry')
        _CLAIMED_BACKENDS.add(backend)
    roles=modules['ainav.vlm'].RoleRunner(backend,journal,**profile['roles'])
    planner=modules['ainav.planner'].AinavPlanner(roles,journal,**profile['planner'])
    require(guard()is not False,'Owner refused assembled original backbone')
    require(backend.calls==backend.total_tokens==roles.calls==planner.calls==0,
            'Backbone assembly cannot perform any VLM transport or role call')
    record=dict(event='V4_original_AINav_backbone_assembled_not_method_or_native_ready',arm=arm,
        original_source_sha256=PINS,original_full_course_profile=profile,backend_public_identity=identity,
        original_object_skill_proposer_tree_evaluator_advisor_arborist_replanning_retained=True,
        bare_backbone_requires_Reach_AinavSuccessorAdapter_and_common_factor_binding=True,
        not_API0_or_fixed_rule_substitute=True,backend_constructor_or_generate_calls=0,
        no_credential_environment_opener_or_remote_metadata_probe=True,model_input=False,
        physical_action_issued=False,task_success_claimed=False)
    ref=journal(record)
    require(type(ref)is str and bool(ref),'Durable original-backbone source evidence required')
    planner._v4_backbone_only_not_full_method=True
    planner._v4_backbone_source=MappingProxyType(dict(arm=arm,evidence_ref=ref,
        profile=profile,source_root=str(root),original_profile_source_sha256=PINS['run_full_course.py']))
    return planner
