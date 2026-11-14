"""Read-only CONSUMER of WM-owned v0, not a replacement skill ABI or solver.

Only reads pinned contract + manifest metadata. Does NOT initialize the owner
reader (whose constructor audits historical outcomes), read effect archives,
forge sensor histories or call predict without a real public observation.
"""
import hashlib
import json
from pathlib import Path

OWNER_DOCS=Path('/home/yuanyue/re-nav/GO2-PIPER/docs')
CONTRACT_SHA='d543745d91cbcf318617a90fef36b8a228d5e10d9706c2274c9333100bb2a68a'
MANIFEST_SHA='7b467daf8d6eb895bea48f5a68bb96693bc3a8426f8c3123ee8549193b59c1cb'
VERSION='go2-piper-mission-v9-ae1c724-full4'


def load_domain(contract_path=OWNER_DOCS/'skill_interface_contract_v0.json',
                manifest_path=OWNER_DOCS/'skill_executor_manifest_v0.json'):
    blobs=[]
    for path,expected in ((Path(contract_path),CONTRACT_SHA),(Path(manifest_path),MANIFEST_SHA)):
        raw=path.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=expected:
            raise ValueError('Owner version changed; explicitly review/rebind, never update pins silently')
        blobs.append(json.loads(raw))
    return validate_domain(*blobs)


def validate_domain(contract,manifest):
    if (contract.get('schema')!='skill-interface-contract-v0' or
        manifest.get('schema')!='skill-executor-manifest-v0' or
        contract.get('executor_version')!=VERSION or manifest.get('executor_version')!=VERSION or
        contract.get('source_sha')!=manifest.get('source_commit') or
        contract.get('executor_manifest',{}).get('sha256')!=MANIFEST_SHA):
        raise ValueError('Owner contract/manifest/version mismatch')
    push=contract['actions']['PUSH']
    if (push['parameters']['push_distance_m']['enum']!=[.2,.4,.6] or
        push['continuous_optimization'] is not False or
        push['fixed']['entry_front_standoff_m']!=.58 or
        contract['phases']['EXIT']['requestable'] is not False):
        raise ValueError('Changed exposed domain or independent EXIT authority')
    if (manifest.get('physical_dispatch_allowed') is not False or
        manifest.get('GPU_HOLD') is not True or
        contract.get('admission')!=dict(interface_CPU_only=True,physical_dispatch=False,GPU=False,training=False)):
        raise ValueError('This consumer must remain CPU-only and non-dispatching')
    return dict(schema='reach-owner-domain-consumption-v0',executor_version=VERSION,
                source_commit=manifest['source_commit'],contract_sha256=CONTRACT_SHA,
                manifest_sha256=MANIFEST_SHA,adoption_scope='Reach CPU domain reference only; NOT group consensus or physical admission',
                decision_variable=dict(name='push_distance_m',unit='m',kind='finite_enum',values=[.2,.4,.6]),
                objects=list(push['objects']),fixed=push['fixed'].copy(),
                continuous_preparation_domain=None,independent_exit_domain=None,
                continuous_sensitivity_status='NOT_APPLICABLE_TO_EXPOSED_FINITE_DOMAIN',
                robot_effect_model_status='NOT_READY_per_owner_delivery_not_queried_here',
                mathematical_optimizer_ready=False,execution_authorized=False,
                physical_safety_certificate=False,
                forbidden_uses=['goal_as_terminal_state','historical_outcome_as_prediction',
                                'continuous_interpolation','independent_exit_override'])


def candidates(domain,object_ref):
    if object_ref not in domain['objects']:
        raise ValueError('Unsupported bound PUSH object; no alias remapping')
    return [dict(executor_version=domain['executor_version'],skill='PUSH',object_ref=object_ref,
                 parameters=dict(push_distance_m=d),status='PARAMETER_TEMPLATE_NOT_EXECUTABLE_REQUEST',
                 observed_effect=None,cost_s=None,next_ready=None,feasible=None,
                 physical_dispatch=False) for d in domain['decision_variable']['values']]


def optimization_status(domain):
    # Domain enumeration is complete, but no causal outcome producer/cost exists.
    # No synthetic observation or nearest historical row fills the missing fields.
    return dict(status='UNKNOWN',reason='causal_candidate_effect_cost_and_next_ready_missing',
                candidate_domain_ready=True,finite_candidate_count=len(domain['decision_variable']['values']),
                best_candidate=None,continuous_solver_called=False,
                global_infeasible=False,execution_authorized=False)
