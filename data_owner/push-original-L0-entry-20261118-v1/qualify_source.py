"""Actual private-Python source + EXPLICIT software fixture; no world/Actor/lease."""
from pathlib import Path
import argparse,hashlib,json,sys,types
sys.path.insert(0,str(Path(__file__).resolve().parent))
from l0_startup import prepare_startup,derive_fresh_L0_runtime_source,_identity,PLAY_SHA,BRIDGE_SHA


def qualify(sdk,source_root):
    import numpy as np
    from types import SimpleNamespace as NS
    import l0_startup
    sdk=Path(sdk).resolve(strict=True);source_root=Path(source_root).resolve(strict=True)
    raw=(sdk/'switch/runtime.py').read_bytes();changed,proof=derive_fresh_L0_runtime_source(raw,enabled=True)
    sys.path.insert(0,str(source_root))
    from mujoco_zyh.runtime_adapter import prepare_runtime_source
    camera_source,camera_hook=prepare_runtime_source(changed)
    def function_code(raw,path,name,cls=None):
        compiled=compile(raw,str(path),'exec',dont_inherit=True)
        if cls:compiled=next(c for c in compiled.co_consts if isinstance(c,types.CodeType)and c.co_name==cls)
        return next(c for c in compiled.co_consts if isinstance(c,types.CodeType)and c.co_name==name)
    original_step=function_code(raw,sdk/'switch/runtime.py','step','Runtime')
    prepared_step=function_code(camera_source,sdk/'switch/runtime.py','step','Runtime')
    assert _identity(original_step)==_identity(prepared_step)
    assert prepare_startup(enabled=False)is None and derive_fresh_L0_runtime_source(enabled=False)is None
    class Command:
        def __init__(self,position,velocity,kp,kd,feedforward):
            self.position,self.velocity,self.kp,self.kd,self.feedforward=position,velocity,kp,kd,feedforward
        def array(self):return np.stack([self.position,self.velocity,self.kp,self.kd,self.feedforward])
    ns=dict(np=np,MotorCommand=Command,KP=np.full(18,10.),KD=np.ones(18))
    physics=types.FunctionType(function_code((sdk/'push/bridge.py').read_bytes(),sdk/'push/bridge.py','physics_step','PushBridge'),ns)
    # Function bodies below are the byte-exact compiled ORIGINAL functions with
    # a clearly fake world/NumPy namespace, not actual MuJoCo or model loading.
    settle=types.FunctionType(function_code((sdk/'push/play.py').read_bytes(),sdk/'push/play.py','settle'),
        dict(np=np,mujoco=NS(mjtGeom=NS(mjGEOM_SPHERE=2)),PHYSICS_DT=.005))
    def fixture():
        zero=np.zeros(18)
        data=NS(time=0.,qpos=np.r_[[-.08,0.,.33],np.zeros(22)],qvel=np.zeros(24),geom_xpos=np.tile([0.,0.,.05],(4,1)))
        reset=[]
        model=NS(body=lambda name:NS(id=('FL','FR','RL','RR').index(name.removesuffix('_foot'))),
                 opt=NS(timestep=.005),geom_bodyid=np.arange(4),geom_type=np.full(4,2),geom_size=np.tile([.02,0.,0.],(4,1)))
        def hidden(*args,**kwargs):raise AssertionError('SOURCE generator may not call hidden physics')
        sim=NS(data=data,model=model,queue=[],targets=zero.copy(),forces=np.tile([0.,0.,4.],(4,1)),
               applied_commands=np.ones(18),history='original-before-reset',refresh=lambda:None,
               controller=NS(reset=lambda arg:reset.append(arg)),physics_step=hidden)
        r=NS(step_count=0,sim=sim,Command=Command,last=Command(zero,zero,ns['KP'],ns['KD'],zero))
        stepper=prepare_startup(r,guard=lambda:True,actor_call_count=lambda:0,original_settle=settle,play_path=sdk/'push/play.py',
            original_physics_step=physics,bridge_path=sdk/'push/bridge.py',enabled=True)
        return r,stepper,reset
    r,stepper,resets=fixture()
    while True:
        command=stepper.next_command()
        if command is None:break
        assert np.array_equal(command.array(),Command(r.sim.targets,np.zeros(18),ns['KP'],ns['KD'],np.zeros(18)).array())
        # Acknowledge ONLY the explicit SOFTWARE fixture's external clock/count.
        r.last=command;r.step_count+=1;r.sim.data.time=r.step_count*.005
        stepper.after_actual_issue()
    report=stepper.snapshot()
    assert report['initialization_finished_not_PUSH_success']and report['original_startup_result']['stable']
    assert report['verified_actual_issue_acknowledgements']==1301 and len(report['original_initialization_writes_and_resets'])==6
    assert resets==[None]and r.sim.history is None and np.all(r.sim.applied_commands==0.)
    assert all(x['L0_initialization_not_continuous_L1']for x in report['original_initialization_writes_and_resets'])
    assert report['original_stable_gate_is_3N_NOT_registered12N_admission']
    assert float(np.min(r.sim.forces[:,2]))==4.<12. # Original startup PASS is NOT original registered12N entry.
    r2,s2,_=fixture();s2.next_command()
    try:s2.after_actual_issue()
    except ValueError:pass
    else:raise AssertionError('No invented physical issue acknowledgement')
    assert s2.failed
    r3,s3,_=fixture();s3.next_command()
    try:s3.next_command()
    except ValueError:pass
    else:raise AssertionError('No unissued request skip/duplicate')
    assert s3.failed
    r4,s4,_=fixture();r4.step_count=1
    try:
        prepare_startup(r4,guard=lambda:True,actor_call_count=lambda:0,original_settle=settle,
            play_path=sdk/'push/play.py',original_physics_step=physics,bridge_path=sdk/'push/bridge.py',enabled=True)
    except ValueError:pass
    else:raise AssertionError('Cannot initialize a predecessor world')
    r5,s5,_=fixture();s5.actor_call_count=lambda:1
    try:s5.next_command()
    except ValueError:pass
    else:raise AssertionError('Cannot hide an Actor invocation inside startup')
    assert s5.failed
    r6,s6,_=fixture();command=s6.next_command();r6.last=command;r6.step_count=1;r6.sim.data.time=.005
    marker=RuntimeError('fixture native failure, not an Actor result')
    try:s6.after_actual_issue(native_error=marker)
    except RuntimeError as exc:assert exc is marker
    else:raise AssertionError('Original Runtime failure cannot be acknowledged as a good request')
    snapshot=s6.snapshot();assert snapshot['failed']and snapshot['observed_task_clock']==.005
    assert snapshot['verified_actual_issue_acknowledgements']==0 # preserve actual clock even with no verified ACK.
    assert 'torch'not in sys.modules and 'mujoco'not in sys.modules
    return dict(stage='ACTUAL_PRIVATE_PYTHON_L0_SOURCE_AND_EXPLICIT_SOFTWARE_FIXTURE_PASS_NOT_NATIVE_PREPARE',
        Python=list(sys.version_info[:3]),interpreter=sys.executable,original_play_SHA256=PLAY_SHA,
        original_bridge_SHA256=BRIDGE_SHA,private_L0_initialization_source=proof,
        original_Runtime_step_bytecode_unchanged=True,original_camera_hook=camera_hook,
        SOFTWARE_fixture_acknowledged_steps=1301,SOFTWARE_fixture_original_startup_result=report['original_startup_result'],
        original_init_note_labels=[x['label']for x in report['original_initialization_writes_and_resets']],
        software_false_ack_duplicate_resume_predecessor_world_Actor_and_native_error_refused=True,software_original3N_pass_NOT_registered12N_entry=True,
        Runtime_MjModel_MjData_GPU_Actor_lease_or_actual_physics_calls=0,
        Torch_imported=False,original_SDK_files_not_modified=True,
        full_L0_parent_original12N_witness_registered_PUSH_full_exit_and_IO_still_to_connect=True,
        complete_program_freeze_or_actual_prepare=False,own_zero=0,main=0,not_qualification_or_training_data=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--enabled',action='store_true');ap.add_argument('--sdk');ap.add_argument('--source-root');a=ap.parse_args()
    if a.enabled:print(json.dumps(qualify(a.sdk,a.source_root),ensure_ascii=False,indent=2))
