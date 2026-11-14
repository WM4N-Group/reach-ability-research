"""Run the development public-only selector with the existing owner pure API.

Example public ref is a schema example, NOT a measured observation or real run.
No Data dependencies, package verifier stack, native imports, host binding or job.
"""
import argparse
from dataclasses import asdict
import importlib.util
import json
from pathlib import Path
import sys

from .public_preparation_selector import PublicReference,build_problem,with_public_observation,choose,materialize_fresh_plan

OWNER=Path('/home/yuanyue/main/work/ainav/consumer-deliveries/AINAV-CLIMB-PREPARATION-CANDIDATES-20261113-v1/climb_preparation_candidates.py')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--owner-api',type=Path,default=OWNER)
    parser.add_argument('--target-ref',default='cuboid-2:upper-entry')
    parser.add_argument('--reference-x',type=float,default=.050000000000000044)
    parser.add_argument('--reference-y',type=float,default=-2.)
    parser.add_argument('--method',choices=('original_fixed','current_greedy','successor_aware'),default='successor_aware')
    parser.add_argument('--on-unknown',choices=('original_default','abstain'),default='original_default')
    parser.add_argument('--observation-json',type=Path,help='Existing public Observation.value; source role must be truthful, never relabel audit data')
    parser.add_argument('--observation-source-role',choices=('ONLINE_PUBLIC','AUDIT_ONLY'))
    parser.add_argument('--now-s',type=float,help='Explicit current owner clock; never infer freshness from recorded observation time')
    parser.add_argument('--reobservations-used',type=int,default=0)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    # Import just the established, stdlib-only owner API. No Host/Runtime or
    # default-module globals in the frozen worker are installed or modified.
    name='_Reach_dev_selector_public_owner_API'
    spec=importlib.util.spec_from_file_location(name,args.owner_api)
    owner=importlib.util.module_from_spec(spec);sys.modules[name]=owner;spec.loader.exec_module(owner)
    problem=build_problem(PublicReference(args.target_ref,(args.reference_x,args.reference_y),0.,True,
        'CLI_STATIC_PUBLIC_REFERENCE_EXAMPLE_NOT_LIVE_NATIVE_OBSERVATION'),public_candidates=owner.public_candidates)
    information=None
    if args.observation_json is not None:
        if args.now_s is None or args.observation_source_role is None:
            parser.error('--observation-json requires --now-s and --observation-source-role; no inferred freshness/permission')
        from .public_information import public_snapshot,information_action
        observation=json.loads(args.observation_json.read_text())
        snapshot=public_snapshot(observation,now_s=args.now_s,source_role=args.observation_source_role)
        information=information_action(snapshot,reobservations_used=args.reobservations_used)
        if snapshot['fresh_complete_kinematic_measurement']:
            problem=with_public_observation(problem,observation,now_s=args.now_s,source_role=args.observation_source_role)
            out=choose(problem,method=args.method,on_unknown=args.on_unknown)
        else:
            # No stale dynamic values reach any cost evaluator. A refresh request
            # is returned to the owner, not executed or converted to HOLD/NAV.
            out=dict(status='PUBLIC_MEASUREMENT_UNRESOLVED',optimized_candidate_id=None,
                proposed_payload=None,reason=snapshot['status'],shared_evaluation_count=0,
                execution_authorized=False)
    else:
        out=choose(problem,method=args.method,on_unknown=args.on_unknown)
    selection=None
    if out.get('proposed_payload') is not None and problem.inputs.decision_time_s==0.:
        selection=materialize_fresh_plan(problem,out,selection_from_payload=owner.selection_from_payload,phase='FRESH_PREEXECUTION')
    out.update(owner_immutable_selection=asdict(selection) if selection is not None else None,
        role='DEVELOPMENT_PUBLIC_SELECTOR_NOT_FROZEN_STAGEB_OR_PHYSICAL',
        public_information_action=information,
        actual_Host_or_Runtime_constructed=False,bind_to_host_called=False,
        actual_public_acquisition_calls=0,source_live_authentication_by_this_CLI=False,
        public_observation_json_provided=args.observation_json is not None,
        live_replan_installed=False,validated_dynamic_model_supplied=False)
    with args.output.open('x') as stream:
        json.dump(out,stream,ensure_ascii=False,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps({k:out[k] for k in ('status','optimized_candidate_id','proposed_payload','reason','shared_evaluation_count','execution_authorized')},ensure_ascii=False))


if __name__=='__main__':main()
