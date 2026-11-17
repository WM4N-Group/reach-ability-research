"""New D3 differential cases. Synthetic env, real CPU Torch; no native runtime.
The bounded read-only driver supplies exact original source and builder module.
"""
import ast
import copy
import types
import unittest
import torch

torch.set_num_threads(1)
SOURCE = SOURCE_BYTES
BUILDER = BUILDER_MODULE
PATCHED = BUILDER.instrument_push_settled_source(SOURCE, enabled=True)

class Base:
    def __init__(self, cfg, env): pass

def scene_cfg(*args, **kwargs): return None

def call_helper(env, name, value):
    env.trace.append(name)
    if env.raise_helper == name: raise env.failure
    return value.clone()

def hand_contact(env, cfg): return call_helper(env, 'hand', env.hand)
def push_target(env):
    env.trace.append('target')
    if not hasattr(env, 'box_push_target'):
        env.box_push_target = env.declared_target.clone()
    return env.box_push_target

def box_tipped(env): return call_helper(env, 'tip', env.tip)
def forbidden_box_contact(env): return call_helper(env, 'forbidden', env.forbidden)

def predicate_class(source):
    tree = ast.parse(source.decode()); node = next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='PushSettled')
    ns=dict(torch=torch, ManagerTermBase=Base, SceneEntityCfg=scene_cfg,
        hand_contact=hand_contact,push_target=push_target,box_tipped=box_tipped,forbidden_box_contact=forbidden_box_contact)
    exec(compile(ast.Module(body=[node],type_ignores=[]),'<synthetic-env-original-predicate-only>','exec'),ns)
    return ns['PushSettled']

Original=predicate_class(SOURCE); Audited=predicate_class(PATCHED)
class Env:
    def __init__(self,n=1):
        self.num_envs=n;self.device='cpu';self.trace=[];self.rows=[]
        self.hand=torch.ones(n,dtype=torch.bool);self.tip=torch.zeros(n,dtype=torch.bool);self.forbidden=self.tip.clone()
        self.declared_target=torch.zeros((n,3),dtype=torch.float64)
        self.scene={'box':types.SimpleNamespace(data=types.SimpleNamespace(root_pos_w=torch.zeros((n,3),dtype=torch.float64),root_lin_vel_w=torch.zeros((n,3),dtype=torch.float64)))}
        self.raise_helper=None;self.failure=RuntimeError('SYNTHETIC_HELPER_OR_SINK_ERROR')
        self._ainav_push_settled_audit=self.emit
    @property
    def step_dt(self):self.trace.append('dt');return .02
    def emit(self,row):self.trace.append('emit');self.rows.append(copy.deepcopy(row))

def pair(n=1):
    a,b=Env(n),Env(n);return a,b,Original(None,a),Audited(None,b)

class Differential(unittest.TestCase):
    def test_01_source_boundary_off_and_exact_pins(self):
        self.assertIs(BUILDER.instrument_push_settled_source(SOURCE),SOURCE)
        for bad in (SOURCE+b'\n',PATCHED):
            with self.assertRaises(ValueError):BUILDER.instrument_push_settled_source(bad,enabled=True)
        old=ast.parse(SOURCE);new=ast.parse(PATCHED)
        c=next(n for n in old.body if isinstance(n,ast.ClassDef)and n.name=='PushSettled')
        d=next(n for n in new.body if isinstance(n,ast.ClassDef)and n.name=='PushSettled')
        oc=next(n for n in c.body if isinstance(n,ast.FunctionDef)and n.name=='__call__')
        nc=next(n for n in d.body if isinstance(n,ast.FunctionDef)and n.name=='__call__')
        ob=SOURCE.splitlines(keepends=True);nb=PATCHED.splitlines(keepends=True)
        self.assertEqual(b''.join(ob[:oc.lineno-1]),b''.join(nb[:nc.lineno-1]))
        self.assertEqual(b''.join(ob[oc.end_lineno:]),b''.join(nb[nc.end_lineno:]))
        for name in ('hand_contact','push_target','box_tipped','forbidden_box_contact'):
            self.assertEqual(sum(isinstance(n,ast.Call)and isinstance(n.func,ast.Name)and n.func.id==name for n in ast.walk(nc)),1)

    def test_02_continuous_hold_and_each_helper_exactly_once(self):
        a,b,o,n=pair()
        results=[]
        for i in range(30):
            a.trace.clear();b.trace.clear();a.hand[:]=b.hand[:]=(i==0)
            x,y=o(a),n(b);self.assertTrue(torch.equal(x,y));self.assertTrue(torch.equal(o.duration,n.duration));self.assertTrue(torch.equal(o.contact_seen,n.contact_seen))
            self.assertEqual(a.trace,['hand','target','tip','forbidden','dt'])
            self.assertEqual(b.trace,a.trace+['emit']);results.append(bool(y[0]))
        self.assertFalse(results[23]);self.assertTrue(results[24]);self.assertEqual(len(b.rows),30)

    def test_03_each_original_false_predicate_strict_boundaries_3d(self):
        for case in ('goal','speed_z','contact','tip','forbidden'):
            with self.subTest(case=case):
                a,b,o,n=pair()
                if case=='goal':a.scene['box'].data.root_pos_w[0,0]=b.scene['box'].data.root_pos_w[0,0]=.12
                if case=='speed_z':a.scene['box'].data.root_lin_vel_w[0,2]=b.scene['box'].data.root_lin_vel_w[0,2]=.08
                if case=='contact':a.hand[:]=b.hand[:]=False
                if case=='tip':a.tip[:]=b.tip[:]=True
                if case=='forbidden':a.forbidden[:]=b.forbidden[:]=True
                self.assertTrue(torch.equal(o(a),n(b)));self.assertEqual(b.rows[-1]['settled_now'],(False,));self.assertEqual(b.trace,['hand','target','tip','forbidden','dt','emit'])
                field={'goal':'goal_xy_lt_original_012','speed_z':'speed_3d_lt_original_008','contact':'contact_seen_latched','tip':'not_tipped','forbidden':'no_forbidden_contact'}[case]
                self.assertEqual(b.rows[-1][field],(False,))

    def test_04_first_loss_records_before_after_without_repoll(self):
        a,b,o,n=pair()
        for _ in range(26):o(a);n(b)
        self.assertTrue(bool(n.duration[0]>=.5));a.scene['box'].data.root_lin_vel_w[0,0]=b.scene['box'].data.root_lin_vel_w[0,0]=.09
        x,y=o(a),n(b);self.assertTrue(torch.equal(x,y));row=b.rows[-1]
        self.assertGreater(row['duration_before_s'][0],.5);self.assertEqual(row['duration_after_s'],(0.,));self.assertEqual(row['contact_seen_latched'],(True,));self.assertEqual(row['returned_confirmed'],(False,))

    def test_05_latch_reset_lazy_target_and_snapshot_no_tensor_alias(self):
        a,b,o,n=pair();o(a);n(b);row=copy.deepcopy(b.rows[0]);self.assertTrue(hasattr(a,'box_push_target')and hasattr(b,'box_push_target'))
        o.reset();n.reset();a.hand[:]=b.hand[:]=False
        self.assertTrue(torch.equal(o(a),n(b)));self.assertEqual(b.rows[0],row);self.assertEqual(b.rows[-1]['contact_seen_latched'],(False,))
        self.assertTrue(all(not isinstance(v,torch.Tensor) for v in row.values()))
        self.assertTrue(all(not isinstance(v,(list,dict)) for v in row.values()))

    def test_06_multi_env_dtype_shape_and_values(self):
        a,b,o,n=pair(2);a.scene['box'].data.root_lin_vel_w[1,2]=b.scene['box'].data.root_lin_vel_w[1,2]=.1
        for _ in range(26):
            x,y=o(a),n(b);self.assertTrue(torch.equal(x,y));self.assertEqual(x.dtype,y.dtype);self.assertEqual(x.shape,y.shape)
        self.assertEqual(b.rows[-1]['returned_confirmed'],(True,False));self.assertEqual(b.rows[-1]['settled_now'],(True,False))

    def test_07_missing_or_noncallable_sink_fails_before_stateful_helpers(self):
        for missing in (True,False):
            e=Env();p=Audited(None,e)
            if missing:del e._ainav_push_settled_audit
            else:e._ainav_push_settled_audit=None
            with self.assertRaises((AttributeError,ValueError)):p(e)
            self.assertEqual(e.trace,[]);self.assertEqual(float(p.duration[0]),0.)

    def test_08_sink_failure_propagates_no_retry_and_caller_finally_once(self):
        e=Env();p=Audited(None,e);clean=[]
        def bad(row):e.trace.append('bad_sink');raise e.failure
        e._ainav_push_settled_audit=bad
        try:
            try:p(e)
            finally:clean.append('caller_cleanup')
        except RuntimeError as error:self.assertIs(error,e.failure)
        else:self.fail('Original caller must see sink failure, not fallback')
        self.assertEqual(clean,['caller_cleanup']);self.assertEqual(e.trace,['hand','target','tip','forbidden','dt','bad_sink']);self.assertGreater(float(p.duration[0]),0.)

    def test_09_original_helper_error_identity_and_no_extra_call_or_emit(self):
        a,b,o,n=pair();a.raise_helper=b.raise_helper='forbidden'
        for e,p in ((a,o),(b,n)):
            with self.assertRaises(RuntimeError) as raised:p(e)
            self.assertIs(raised.exception,e.failure);self.assertEqual(e.trace,['hand','target','tip','forbidden']);self.assertEqual(float(p.duration[0]),0.)
        self.assertEqual(b.rows,[])

suite=unittest.defaultTestLoader.loadTestsFromTestCase(Differential)
result=unittest.TextTestRunner(verbosity=2).run(suite)
assert result.wasSuccessful(), 'D3 new synthetic CPU differential failed; not native evidence'
print('D3_NEW_TARGETED_CPU_CASES_PASSED='+str(result.testsRun))
