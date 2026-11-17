"""NEW integration-only CPU fixtures. No world/Actor/native/old test suite.

python -I -B this_file SDK_ROOT DATA_OWNER_SOURCE_ROOT
"""
import ast
import contextlib
import hashlib
import importlib.util
import json
from pathlib import Path
import resource
import sys
import time
import types
import unittest
from types import SimpleNamespace as NS
START=time.perf_counter()
HERE=Path(__file__).resolve().parent
SDK,ROOT=map(Path,sys.argv[1:3]);sys.argv[1:]=[]
sys.path[:0]=[str(HERE),str(ROOT/'push-original-L0-entry-20261118-v1')]
import numpy as np
stub=types.ModuleType('standard_runtime')
def need(ok,msg):
    if not ok:raise ValueError(msg)
stub.need=need;sys.modules['standard_runtime']=stub
import l0_witness as variant

def code(path,name,cls=None):
    root=compile(path.read_bytes(),str(path),'exec',dont_inherit=True)
    if cls:root=next(c for c in root.co_consts if isinstance(c,types.CodeType)and c.co_name==cls)
    return next(c for c in root.co_consts if isinstance(c,types.CodeType)and c.co_name==name)

class Command:
    def __init__(self,position,velocity,kp,kd,feedforward):
        self.position,self.velocity,self.kp,self.kd,self.feedforward=position,velocity,kp,kd,feedforward
    def array(self):return np.stack([self.position,self.velocity,self.kp,self.kd,self.feedforward])

class Push(dict):
    def active(self):return contextlib.nullcontext()

def fixture():
    reference=np.zeros(18);kp=np.full(18,10.);kd=np.ones(18)
    physics=types.FunctionType(code(SDK/'push/bridge.py','physics_step','PushBridge'),
        dict(np=np,MotorCommand=Command,KP=kp,KD=kd))
    class FakeSim:pass
    FakeSim.physics_step=physics
    sim=FakeSim();sim.data=NS(time=0.,qpos=np.r_[[-.08,0.,.33],np.zeros(22)],qvel=np.zeros(24),
        qfrc_bias=np.linspace(-3.,3.,24),geom_xpos=np.tile([0.,0.,.05],(4,1)))
    sim.model=NS(opt=NS(timestep=.005),geom_bodyid=np.arange(4),geom_type=np.full(4,2),
        geom_size=np.tile([.02,0.,0.],(4,1)),body=lambda name:NS(id=('FL','FR','RL','RR').index(name.removesuffix('_foot'))))
    sim.queue=[];sim.targets=reference.copy();sim.dids=np.arange(6,24)
    sim.forces=np.tile([0.,0.,4.],(4,1));sim.applied_commands=np.ones(18);sim.history='before-original-reset'
    resets=[];sim.controller=NS(reset=lambda x:resets.append(x));sim.refresh=lambda:None
    play=types.ModuleType('play');play.__file__=str(SDK/'push/play.py')
    play.settle=types.FunctionType(code(SDK/'push/play.py','settle'),
        dict(np=np,mujoco=NS(mjtGeom=NS(mjGEOM_SPHERE=2)),PHYSICS_DT=.005))
    sys.modules['play']=play
    r=NS(sim=sim,step_count=0,Command=Command,
        push=Push(model=NS(REFERENCE=reference,KP=kp,KD=kd)),last=None)
    trace=NS(rows={})
    owner=variant.L0StartupOwner(dict(runtime=r,registry=object()),bundle=SDK,trace=trace,guard=lambda:True)
    return r,owner,trace,resets

def software_issue(r,owner,cmd):
    # Explicit software-only simulated external ACK. NOT real Runtime.step/MjData.
    r.last=cmd;r.step_count+=1;r.sim.data.time=r.step_count*.005
    r.sim.queue.append(cmd.array().copy());r.sim.queue[:]=r.sim.queue[-5:]
    owner.after_step()

def finish_fixture():
    r,o,t,resets=fixture()
    while True:
        command=o.command()
        if command is None:break
        software_issue(r,o,command)
    return r,o,t,resets

class Checks(unittest.TestCase):
    def test_01_selected_FF_is_sealed_BEFORE_actual_issue_ACK(self):
        r,o,_,_=fixture()
        command=o.command();a=command.array()
        self.assertEqual(o.startup.expected,(a.shape,str(a.dtype),a.tobytes()))
        np.testing.assert_array_equal(a[4,:12],np.zeros(12))
        np.testing.assert_array_equal(a[4,12:],r.sim.data.qfrc_bias[r.sim.dids[12:]])
        self.assertTrue(np.any(a[4,12:]!=0.));self.assertEqual(r.step_count,0)
        software_issue(r,o,command)
        self.assertEqual(o.startup.issued,1)

    def test_02_post_seal_FF_tampering_or_invented_ACK_latches_original_stepper(self):
        for tamper in ('old-zero-FF','no-issue'):
            r,o,_,_=fixture();c=o.command()
            if tamper=='old-zero-FF':
                c.feedforward[:]=0.;r.last=c;r.step_count=1;r.sim.data.time=.005
            with self.assertRaises(ValueError):
                if tamper=='old-zero-FF':o.after_step()
                else:o.after_step()
            self.assertTrue(o.startup.failed)
            with self.assertRaises(ValueError):o.command()

    def test_03_same_settle_control_flow_and_six_original_actions_NO_extra_step(self):
        r,o,_,resets=finish_fixture()
        report=o.report()
        self.assertEqual((r.step_count,o.startup.issued,o.prepared_arm_ff.constructed),(1301,1301,1301))
        self.assertTrue(o.startup.finished and o.startup.original_result['stable'])
        self.assertEqual(len(report['original_initialization_writes_and_resets']),6)
        self.assertEqual(resets,[None]);self.assertIsNone(r.sim.history)
        np.testing.assert_array_equal(r.sim.applied_commands,np.zeros(18))
        self.assertEqual(len(r.sim.queue),5)
        self.assertEqual(o.arm_gate_attempts,0) # Constructor is not registration.
        self.assertFalse(report['unmodified_standalone_L0'])
        self.assertFalse(report['natural_predecessor_L1'])
        self.assertNotIn('original_startup_result',report)
        self.assertEqual(report['kind'],'actual_prepared_L0_registered_arm_live_bias_FF_only')

    def test_04_original_no_Actor_and_guard_failure_preserved(self):
        r,o,trace,_=fixture();trace.rows['software-only']={'attempted':1}
        with self.assertRaises(ValueError):o.command()
        self.assertEqual(o.prepared_arm_ff.constructed,0)
        self.assertEqual((r.step_count,r.sim.data.time),(0,0.))
        self.assertTrue(o.startup.failed)

    def test_05_same_original_witness_constructor_validate_and_one_guard_AST(self):
        original=ROOT/'push-L0-arm-admission-observer-20261118-v1/l0_witness.py'
        self.assertEqual(hashlib.sha256(original.read_bytes()).hexdigest(),'c05e90d3e2375a6982d6eacadd98dae7c10ff10875322c9393530a0c0b33fc55')
        a,b=ast.parse(original.read_bytes()),ast.parse((HERE/'l0_witness.py').read_bytes())
        def get(t,cls,name):
            c=next(n for n in t.body if isinstance(n,ast.ClassDef)and n.name==cls)
            return ast.dump(next(n for n in c.body if isinstance(n,ast.FunctionDef)and n.name==name),include_attributes=False)
        for name in ('__init__','validate'):self.assertEqual(get(a,'OriginalL0Witness',name),get(b,'OriginalL0Witness',name))
        for t in (a,b):
            n=next(n for n in t.body if isinstance(n,ast.FunctionDef)and n.name=='_current_arm_gate_once')
            if t is a:previous=ast.dump(n,include_attributes=False)
            else:self.assertEqual(previous,ast.dump(n,include_attributes=False))

    def test_06_boundary_PASS_and_refusal_do_not_select_task_or_repeat_witness(self):
        tree=ast.parse((HERE/'boundary_driver.py').read_bytes())
        factory=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='driver_class')
        cls=next(n for n in factory.body if isinstance(n,ast.ClassDef))
        connect=next(n for n in cls.body if isinstance(n,ast.FunctionDef)and n.name=='_connect_execution')
        for fail in (False,True):
            r,o,_,_=finish_fixture();calls=[];marker=RuntimeError('original guard fixture refusal')
            def witness(owner):
                calls.append(owner);owner.arm_gate_attempts+=1
                owner.arm_gate_audit=dict(original_guard_calls=1)
                if fail:raise marker
                return object()
            ns=dict(need=need,_OriginalL0Witness=witness)
            exec(compile(ast.fix_missing_locations(ast.Module(body=[connect],type_ignores=[])),'[only future boundary method]','exec'),ns)
            log=[];driver=NS(loop=None,executor=None,factory=None,startup=o,r=r,boundary_reached=False,_write_boundary=log.append)
            if fail:
                with self.assertRaises(RuntimeError)as got:ns['_connect_execution'](driver)
                self.assertIs(got.exception,marker);self.assertFalse(driver.boundary_reached);self.assertIsNone(o.witness)
            else:
                ns['_connect_execution'](driver);self.assertTrue(driver.boundary_reached);self.assertEqual(len(log),1)
            self.assertEqual(len(calls),1)
            self.assertIsNone(driver.loop);self.assertIsNone(driver.executor);self.assertIsNone(driver.factory)
            self.assertEqual(r.step_count,1301)

if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Checks))
    assert not any(k=='mujoco' or k.startswith(('mujoco.','torch'))for k in sys.modules)
    print(json.dumps(dict(stage='PREPARED_L0_LIVE_BIAS_STARTUP_INTEGRATION_CPU_ONLY',
        at=__import__('datetime').datetime.now().astimezone().isoformat(),tests=result.testsRun,
        passed=result.wasSuccessful(),failures=len(result.failures),errors=len(result.errors),
        wall_s=time.perf_counter()-START,maxrss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
        actual_world_Actor_GPU_lease_or_physics=False,old_nine_source_checks_not_rerun=True),indent=2))
    raise SystemExit(0 if result.wasSuccessful()else 1)
