#!/usr/bin/env python3
"""One actual configured backend image request; no robot scene or physics."""
import argparse,json,os,sys,hashlib,time
from datetime import datetime
from pathlib import Path


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for k in ('source','image','root'):ap.add_argument('--'+k,required=True)
    a=ap.parse_args();source,image,root=(Path(v).resolve() for v in (a.source,a.image,a.root))
    if root.exists():raise FileExistsError('Fresh backend verification root required')
    root.mkdir(parents=True);sys.path.insert(0,str(source))
    from ainav.backend import create_vision_backend
    from ainav.contracts import file_sha
    report=dict(schema='ainav-real-configured-gateway-vision-verification-v1',started_at=datetime.now().astimezone().isoformat(),
        source_manifest_sha256=file_sha(source/'ainav-source.json'),image_sha256=file_sha(image),image_scope='synthetic_two_color_diagnostic_not_task_scene',
        actor_forwards=0,task_Runtime_instances_constructed=0,physics_steps=0,task_success=False,automatic_retry=False)
    backend=None;start=time.monotonic()
    try:
        backend=create_vision_backend(max_calls=1,max_tokens=2048,max_total_tokens=10000)
        report['backend_identity']=backend.identity
        request=dict(system='You verify a diagnostic image. No robot control or tools.',instruction='Return JSON with keys left_color and right_color identifying the dominant colors of the image halves. Use plain English color names, not hexadecimal or RGB codes.',
            payload={'question':'What are the left and right dominant colors?'},image={'path':str(image),'sha256':file_sha(image)})
        raw=backend.generate(request,timeout_s=120);answer=json.loads(raw)
        # Preserve raw evidence even if the diagnostic comparison rejects it.
        report.update(raw_final_response=raw,parsed_answer=answer,provider_metadata=backend.last_response_metadata)
        correct=answer.get('left_color','').lower() in ('red','#ff0000','#f50f0f') and answer.get('right_color','').lower() in ('blue','#0000ff','#0f0ff5')
        if not correct:raise ValueError('Synthetic image interpretation incorrect')
        report.update(outcome='configured_gpt61sol_high_image_verified',answer=answer,provider_metadata=backend.last_response_metadata,
            actual_image_answer_correct=True,model_alias_and_effort_requested_verified=True,upstream_effort_or_weights_independently_verified=False)
    except Exception as e:
        message=type(e).__name__+': '+str(e);key=os.environ.get('AINAV_VLM_API_KEY','')
        if key:message=message.replace(key,'[REDACTED]')
        report.update(outcome='failed_no_retry',error=message)
    finally:
        report.update(actual_API_calls=backend.calls if backend else 0,total_tokens=backend.total_tokens if backend else 0,wall_seconds=time.monotonic()-start)
        with (root/'report.json').open('x') as f:json.dump(report,f,indent=2,allow_nan=False);f.write('\n')
    print(json.dumps(report));return 0 if report['outcome']=='configured_gpt61sol_high_image_verified' else 2


if __name__=='__main__':raise SystemExit(main())
