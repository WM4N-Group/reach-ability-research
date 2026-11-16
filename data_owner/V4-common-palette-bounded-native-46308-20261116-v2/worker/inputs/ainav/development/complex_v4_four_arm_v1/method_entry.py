"""Default-off original C/D + canonical Reach assembly; no authentication or calls.

This closes method construction and the driver's factor-journal rebinding seam,
not method/native admission. D requires an explicit shared B/D cost callable;
its UNKNOWN/partial values retain Reach's conservative fallback unchanged.
"""
from pathlib import Path
from types import MappingProxyType
import hashlib,importlib,sys
from backbone_entry import build_original_ainav_backbone
from v4_native_asset import require

REACH_PACKAGE='research.task_conditioned_reachability.execution_preparation'
REACH_PINS={
 'v4_backbone_adapters.py':'38787016a99e346b92d745a8ca0884128b68356d29beb9fe28e8f140a2865689',
 'v4_successor_choice.py':'bb0d6ca0a7243354eea5e88f88534fc58bbaeea0eca9cbbf4fc7bcdf911eb1c9',
}


def _reach_modules(source_root):
    root=Path(source_root).resolve(strict=True)
    base=root/REACH_PACKAGE.replace('.','/')
    for name,pin in REACH_PINS.items():
        p=base/name
        require(not p.is_symlink()and hashlib.sha256(p.read_bytes()).hexdigest()==pin,
                'Exact canonical Reach method source: '+name)
    sys.path.insert(0,str(root));modules={}
    for short in ('v4_successor_choice','v4_backbone_adapters'):
        module=importlib.import_module(REACH_PACKAGE+'.'+short)
        require(Path(module.__file__).resolve()==base/(short+'.py'),
                'No ambient Reach method module: '+short)
        modules[short]=module
    adapter=modules['v4_backbone_adapters'];choice=modules['v4_successor_choice']
    require(adapter.choose is choice.choose and adapter.PublicPath is choice.PublicPath
            and adapter.NominalCost is choice.NominalCost and adapter.need is choice.need,
            'Both backbones use the exact same Reach successor kernel and UNKNOWN semantics')
    return root,adapter


def _parts(planner):
    """Only the source-assembled canonical C/D instance can rebind its journal."""
    meta=getattr(planner,'_v4_original_CD_assembly',None)
    require(isinstance(meta,MappingProxyType),'Explicit source-only original C/D assembly required')
    root,module=_reach_modules(meta['reach_source_root'])
    require(type(planner)is module.AinavSuccessorAdapter,'No replacement method wrapper')
    from ainav.planner import AinavPlanner
    from ainav.vlm import RoleRunner
    baseline=planner.baseline
    require(type(baseline)is AinavPlanner and type(baseline.roles)is RoleRunner
            and getattr(baseline,'_v4_backbone_only_not_full_method',False)is True,
            'Exact constructed original roles/tree/planner, not API0 or fixed rule')
    require(planner.enabled is (meta['arm']=='D') and planner.software_fixture is meta['software_fixture'],
            'Frozen source assembly factor identity')
    return baseline,baseline.roles


def bind_original_cd_journal(planner,journal):
    """Driver binds its ONE FactorJournal to wrapper, original planner AND roles.

    Do not wrap the ledger again, reset counters/pending state or call any role.
    Called only while installing the common layer before the first task decision.
    """
    require(callable(journal),'Actual shared durable factor journal')
    baseline,roles=_parts(planner)
    require(baseline.calls==roles.calls==roles.backend.calls==roles.backend.total_tokens==0
            and baseline.pending is None,'No live method journal hot-rebind or counter reset')
    require(planner.journal is baseline.journal and baseline.journal is roles.journal,
            'One existing journal before source-only factor rebinding')
    planner.journal=baseline.journal=roles.journal=journal


def build_original_cd_method(*,enabled=False,arm=None,source_root=None,reach_source_root=None,
                             backend=None,journal=None,guard=None,shared_path_cost=None,
                             software_fixture=False):
    require(type(enabled)is bool and type(software_fixture)is bool,'Explicit source/fixture factors')
    if not enabled:return None
    require(arm in ('C','D'),'Original C/D method only, never replace A/B or E')
    require((arm=='C'and shared_path_cost is None)or(arm=='D'and callable(shared_path_cost)),
            'C has no new treatment; D needs the SAME explicit B/D cost callable, not an unbound optimizer')
    require(software_fixture or not getattr(shared_path_cost,'software_fixture',False),
            'Fixture cost cannot enter a production method')
    require(callable(guard)and callable(journal)and guard()is not False,'Actual owner guard/journal')
    reach_root,module=_reach_modules(reach_source_root)
    baseline=build_original_ainav_backbone(enabled=True,arm=arm,source_root=source_root,
        backend=backend,journal=journal,guard=guard)
    planner=module.build_v4_planner(arm,journal=journal,ainav_baseline=baseline,
        path_cost=shared_path_cost,software_fixture=software_fixture)
    planner._v4_original_CD_assembly=MappingProxyType(dict(arm=arm,
        reach_source_root=str(reach_root),software_fixture=software_fixture))
    original,roles=_parts(planner)
    require(original is baseline and planner.journal is baseline.journal is roles.journal is journal,
            'One original backend/tree/roles and shared journal; no replacement')
    require(guard()is not False,'Owner refused source-assembled method')
    require(backend.calls==backend.total_tokens==roles.calls==baseline.calls==0,
            'No authentication, generate, role or method calls during assembly')
    ref=journal(dict(event='V4_original_CD_and_canonical_Reach_assembled_NOT_qualified',arm=arm,
        software_fixture=software_fixture,reach_source_files_sha256=REACH_PINS,
        new_successor_optimizer_enabled=planner.enabled,explicit_shared_path_cost_bound=shared_path_cost is not None,
        same_B_D_provider_identity_and_current_complete_cost_still_owner_responsibility=True,
        unknown_is_not_zero_or_native_admission=True,backend_auth_or_API_or_role_calls=0,
        method_or_native_or_task_ready_claimed=False,model_input=False,physical_action_issued=False))
    require(type(ref)is str and bool(ref),'Durable source assembly evidence required')
    return planner
