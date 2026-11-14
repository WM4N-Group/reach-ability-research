"""Explicit local CPU owner-release intake; no dispatch/remote/native imports."""
from dataclasses import asdict
from pathlib import Path
import argparse
import hashlib
import json
from .successor_preparation_intake import (verify_release, build_intake,
    minimal_public_input, unavailable_model_check, consume_owner_public_api)

AINAV_ROOT='/home/yuanyue/main/work/ainav/consumer-deliveries/AINAV-CLIMB-PREPARATION-CANDIDATES-20261113-v1'
DATA_ROOT='/home/yuanyue/main/work/data-team/consumer-deliveries/AINAV-DATA-SUCCESSOR-AWARE-PAIRED-CAPTURE-CPU-TEMPLATE-20261113-v1'
AINAV_SHA='0c17d2e70139a86a14b7a87fa9fb2cd6ed1bd37d8873a009a7b7613bea40718e'
DATA_SHA='26df01074ec037fae456ef25b695fe20ac7ec4ffb704f6ede5e38852688dba18'


def main():
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--output',type=Path,required=True)
    args=cli.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    a=verify_release(AINAV_ROOT,'CANDIDATE_RELEASE_v1.json',expected_release_sha256=AINAV_SHA,inventory_field='files_sha256')
    b=verify_release(DATA_ROOT,'release.json',expected_release_sha256=DATA_SHA,inventory_field='files')
    domain,schema,protocol,payloads=build_intake(a,b)
    example=minimal_public_input(domain,schema,protocol,decision_time_s=0.)
    results={
        'OWNER_RELEASE_INTEGRITY.json':dict(schema='Reach-owner-release-integrity-receipt-v1',
            role='CPU_INTEGRITY_AND_SCHEMA_NOT_NATIVE_PHYSICAL_QUALIFICATION',
            releases=[dict(path=x.root+'/'+x.release_name,sha256=x.release_sha256,
                verified_declared_members=len(x.members),all_declared_members_match=True) for x in (a,b)],
            old_outcome_or_arrays_reaudited=False, native_Runtime_or_Actor_or_GPU_or_remote_calls=0),
        'OWNER_BOUND_STAGE_B_PROTOCOL.json':protocol,
        'CPU_DOMAIN_AND_INFORMATION_SCHEMA.json':dict(domain=asdict(domain),schema=asdict(schema),
            static_example=asdict(example), actual_fresh_native_observation=False,
            future_domain_role_requires_native_qualification=True),
        'EXACT_FINITE_EXECUTION_PAYLOADS.json':list(payloads),
        'UNKNOWN_MODEL_ABSTENTION.json':unavailable_model_check(domain,schema,example),
        'ACTUAL_OWNER_PUBLIC_API_CONSUMED.json':consume_owner_public_api(a,protocol,payloads),
    }
    for name,value in results.items():
        with (args.output/name).open('x') as stream:
            json.dump(value,stream,ensure_ascii=False,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps(dict(status='PINNED_OWNER_CPU_INTAKE_COMPLETE_NOT_PHYSICAL',
        candidate_ids=protocol['candidate_ids'], verified_owner_members=len(a.members)+len(b.members),
        output=str(args.output.resolve()),dispatch=False),ensure_ascii=False))


if __name__=='__main__':main()
