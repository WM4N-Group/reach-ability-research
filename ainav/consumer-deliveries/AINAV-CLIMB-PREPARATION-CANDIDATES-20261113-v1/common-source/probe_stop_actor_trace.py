#!/usr/bin/env python3
"""Explicit synthetic private trace IO regression; NO robot/actor/physics."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace as NS


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('source','root'):p.add_argument('--'+k,required=True)
    a=p.parse_args();source,root=(Path(x).resolve() for x in (a.source,a.root));root.mkdir(parents=True,exist_ok=False);sys.path.insert(0,str(source))
    import numpy as np
    from ainav.native.stop_actor_trace import StopActorTrace,require_original_arm_ff_slew
    m=json.loads((source/'ainav-source.json').read_text())
    assert all(sha(source/k)==v for k,v in m['files'].items())
    trace=StopActorTrace(root);obs=np.arange(226,dtype=np.float32)/100;raw=np.arange(12,dtype=np.float32)/100
    obs_before=obs.copy();raw_before=raw.copy();slots=np.arange(12)[::-1];reference=np.linspace(0,1,18)
    trace.propose(time_s=1.,observation=obs,raw_leg=raw,scale=.7,slots=slots,reference=reference)
    action=np.zeros(18);action[slots]=raw*.7;legs=(reference+.25*np.clip(action,-10.,10.))[:12]
    def cmd(positions):return NS(position=positions,array=lambda:np.stack((positions,np.zeros(18),np.ones(18),np.ones(18),np.zeros(18))))
    actual=cmd(np.r_[legs,np.zeros(6)])
    trace.actual_issue(actual,physical_tick=200,time_s=1.)
    assert trace.samples[0]['first_actual_issue_tick']==-1
    trace.actual_issue(actual,physical_tick=201,time_s=1.005)
    trace.actual_issue(actual,physical_tick=202,time_s=1.01)
    assert trace.samples[0]['first_actual_issue_tick']==201
    trace.propose(time_s=1.02,observation=obs,raw_leg=raw,scale=.7,slots=slots,reference=reference)
    trace.actual_issue(cmd(np.r_[legs+1.,np.zeros(6)]),physical_tick=205,time_s=1.025)
    summary=trace.close();assert summary['proposals']==2 and summary['actually_committed']==1
    with np.load(root/summary['path'],allow_pickle=False) as z:
        assert z['observation'].shape==(2,226) and np.array_equal(z['observation'][0],obs)
        assert np.array_equal(z['raw_leg'][0],raw)
        assert z['first_actual_issue_tick'].tolist()==[201,-1]
        assert z['issued_command_sha256'][1]==''
    assert np.array_equal(obs,obs_before) and np.array_equal(raw,raw_before)
    require_original_arm_ff_slew([0.]*6,[.5]*6,[10.]*6)
    try:require_original_arm_ff_slew([0.]*6,[.51]*6,[10.]*6)
    except RuntimeError:pass
    else:raise AssertionError('Existing FF slew violation not denied')
    r=dict(schema='ainav-stop-trace-synthetic-IO-regression-v1',regression_passed=True,
        source_manifest_sha256=sha(source/'ainav-source.json'),synthetic_fixture_not_robot=True,
        actually_matched_synthetic_commands=1,unissued_proposals_not_credited=True,original_input_arrays_unmodified=True,
        first_actual_commit_not_double_counted=True,original_FF_gate_preserved=True,trace=summary,
        actual_task_motor_steps=0,actor_forwards=0,Runtime_instances_constructed=0,model_API_calls=0,
        probe_sha256=sha(__file__))
    with (root/'report.json').open('x') as f:json.dump(r,f,indent=2);f.write('\n')
    print(json.dumps(r))


if __name__=='__main__':main()
