"""CPU/source consumer proof using exact pinned native METHOD ASTs.

All measured states, queue results, geometry and array math below are SOFTWARE
FIXTURES. No actual capture/geometry/QP/NN/safety/motor validation is asserted.
The command probe stops at the unmodified select_reference argument boundary.
"""
import ast
import hashlib
import math
from pathlib import Path
import tempfile
from types import ModuleType, SimpleNamespace as NS
import unittest
from .native_stow_path_binding import (CALLBACK, INSERT, bind_to_host,
    restore_stall_source, transform_stall_source)
from .build_stow_path_choice_delta import build, ALIASES

PACKAGE = Path('/home/yuanyue/main/work/ainav/consumer-deliveries/AINAV-ABSOLUTE-PLACEMENT-BASELINE-20261113-v1')
SOURCE = PACKAGE/'reference-source'/ALIASES[0]


class Vec(tuple):
    def copy(self): return Vec(self)
    def tolist(self): return list(self)
    def __getitem__(self, i):
        if isinstance(i, (list, tuple)): return Vec(tuple.__getitem__(self,j) for j in i)
        value = tuple.__getitem__(self,i)
        return Vec(value) if isinstance(i,slice) else value
    def __add__(self, other): return Vec(a+b for a,b in zip(self,other))
    def __sub__(self, other): return Vec(a-b for a,b in zip(self,other))
    def __mul__(self, scalar): return Vec(a*scalar for a in self)
    __rmul__ = __mul__
    def __abs__(self): return Vec(abs(a) for a in self)


def q(x): return Vec((x,0.,0.,0.,0.,0.))


class DesiredObserved(Exception): pass


class NativeSourceBindingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.original = SOURCE.read_text()
        self.changed = transform_stall_source(self.original)
        self.path = Path(self.tmp.name)/'stall_stow.py';self.path.write_text(self.changed)

    def fixture(self, *, transformed=True, enabled=True, guard=None, queue_pass=True):
        module = ModuleType('source_fixture');ns = vars(module);module.__file__=str(self.path)
        self.probes=[];self.calls=[];self.emitted=[];self.queue_calls=[]
        np = NS(array=lambda v,**kw:Vec(v), max=max, array_equal=lambda a,b:tuple(a)==tuple(b),
                clip=lambda x,a,b:max(a,min(b,x)))
        def segment(a,b):
            self.calls.append((tuple(a),tuple(b)))
            return '' if guard is None else guard(a,b)
        def screen(**kwargs):
            self.queue_calls.append(kwargs);return {'screen_pass': queue_pass}
        def select_reference(desired,*args,**kwargs):
            self.probes.append(tuple(desired));raise DesiredObserved()
        ns.update(np=np, math=math, history_sha=lambda s:'history', committed_queue_screen=screen,
                  select_reference=select_reference, emit_capsule=lambda *a,**k:None)
        # Unmodified function AST nodes from the exact selected original class;
        # no imports, constructors, simulator, NumPy, NN or native guard loaded.
        tree=ast.parse(self.changed if transformed else self.original)
        cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='ProtectedStow')
        cls.body=[n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name in ('update','begin_segment','command')]
        exec(compile(ast.Module(body=[cls],type_ignores=[]),str(self.path),'exec'),ns)
        owner=module.ProtectedStow.__new__(module.ProtectedStow)
        s=NS(data=NS(time=3.,qpos=Vec([0.]*18),qvel=Vec([0.]*18)),
             qids=list(range(18)),dids=list(range(18)),queue=[Vec([0.]*18)],delays=Vec([0.]*18),
             box_push_target=NS(numpy=lambda:Vec([2.3,-2.])),
             robot=NS(joint_names=['joint'+str(i) for i in range(1,7)],
                      get_gravity_compensation_forces=lambda:NS(numpy=lambda:[Vec([0.]*6)])))
        owner.s=s;owner.r=NS(sim=s,last=NS(position=Vec([0.]*18),velocity=Vec([0.]*18),feedforward=Vec([0.]*18)))
        owner.native=NS(guard=NS(segment=segment))
        owner.pm=NS(EFFORT=Vec([10.]*18),KP=Vec([1.]*18),KD=Vec([1.]*18))
        owner.waypoints=[q(1.),q(.5),q(.1)];owner.reference=q(0.);owner.velocity=q(0.)
        owner.compact_goal=q(.1);owner.unload_target=q(0.);owner.original_goal=Vec([2.3,-2.])
        owner.retired_history_sha='history';owner.native_arrival=None;owner.phase='UNLOAD_CAPTURE'
        owner.started=0.;owner.index=0;owner.segment_start=None;owner.segment_duration=None;owner.segment_origin=None
        owner.support_anchors_latched=True;owner.support_anchor_since=0.;owner.captured_since=2.5
        owner.stable_since=None;owner.complete=False;owner.last_update=-math.inf;owner.limits=None
        owner.events=[];owner.event=lambda text:owner.events.append(text)
        metrics=dict(base_horizontal_displacement_m=0.,base_linear_speed=0.,foot_normal_N=[20.]*4,
                     max_foot_speed=0.,hand_force_N=0.,legal_hand_contact=False,base_angular_speed=0.,
                     tilt_rad=0.,box_linear_speed=0.,box_angular_speed=0.,arm_speed=0.,arm_error=0.)
        owner.measure=lambda:metrics.copy();owner.clearance_gate=lambda m:True
        immutable_calls=[]
        services=NS(session=None,native=NS(r=owner.r),p=s,assert_immutable=lambda:immutable_calls.append(True))
        machine=NS(brake=NS(stow=owner,r=owner.r),confirmed=True,services=services,native=services.native)
        session=NS(machine=machine,placement_source_height=0.,runtime=NS(sim=s));services.session=session
        host=NS(executor=NS(session=session,option=NS(skill='PUSH'),reported_end=False))
        binding=bind_to_host(host,module,enabled=enabled,emit=self.emitted.append)
        return NS(owner=owner,module=module,host=host,session=session,metrics=metrics,
                  binding=binding,immutable_calls=immutable_calls)

    def command_desired(self, f):
        o=f.owner;o.s.data.time=o.segment_start+.5*o.segment_duration
        with self.assertRaises(DesiredObserved):o.command()
        return self.probes[-1]

    def test_exact_reversible_single_hunk_and_both_aliases(self):
        self.assertEqual(SOURCE.read_bytes(),(PACKAGE/'reference-source'/ALIASES[1]).read_bytes())
        self.assertEqual(restore_stall_source(self.changed),self.original)
        self.assertEqual(self.changed.replace(INSERT,'',1),self.original)
        for mutation in (self.original+'\n',self.changed):
            with self.assertRaises(ValueError):transform_stall_source(mutation)
        with self.assertRaises(ValueError):restore_stall_source(self.changed.replace('>=4.-1e-8','>=0.'))

    def test_default_off_does_not_read_host_or_module(self):
        self.assertEqual(bind_to_host(None,None),{'status':'DEFAULT_DISABLED','installed':False})
        with self.assertRaises(ValueError):bind_to_host(None,None,enabled=1)

    def test_disabled_update_matches_exact_original_consumer(self):
        a=self.fixture(transformed=False,enabled=False);a.owner.update()
        state_a=(a.owner.phase,a.owner.waypoints,a.owner.segment_duration,self.command_desired(a))
        b=self.fixture(transformed=True,enabled=False);b.owner.update()
        state_b=(b.owner.phase,b.owner.waypoints,b.owner.segment_duration,self.command_desired(b))
        self.assertEqual(state_a,state_b);self.assertNotIn(CALLBACK,vars(b.module))
        self.assertEqual(self.emitted,[])

    def test_real_update_begin_segment_and_desired_consume_selected_path(self):
        f=self.fixture();f.owner.update()
        self.assertEqual(f.owner.waypoints,[q(.1)])
        self.assertEqual(f.owner.phase,'PROTECTED_STOW')
        self.assertAlmostEqual(f.owner.segment_duration,math.sqrt(5.78*.1/.8))
        self.assertEqual(self.calls[-1],(q(0.),q(.1))) # Original caller full-path recheck AFTER callback.
        self.assertEqual(len(self.queue_calls),1);self.assertGreaterEqual(len(f.immutable_calls),2)
        self.assertAlmostEqual(self.command_desired(f)[0],.05)
        self.assertEqual(self.emitted[0]['physical_commands_issued_by_optimizer'],0)
        self.assertTrue(self.emitted[0]['equivalent_to_direct_baseline'])

    def test_same_source_can_select_intermediate_subsequence(self):
        f=self.fixture(guard=lambda a,b:'direct blocked' if a==q(0.) and b==q(.1) else '')
        f.owner.update();self.assertEqual(f.owner.waypoints,[q(.5),q(.1)])
        self.assertTrue(self.emitted[0]['distinct_from_original_and_direct'])
        self.assertEqual(self.command_desired(f),tuple(q(.25)))

    def test_current_A_prefix_and_wrong_stow_instance_not_modified(self):
        for change in ('no_session','wrong_owner','unconfirmed','elevated','wrong_services','nav','ended'):
            with self.subTest(change=change):
                f=self.fixture();o=f.owner
                if change=='no_session':f.host.executor.session=None
                elif change=='wrong_owner':f.session.machine.brake.stow=object()
                elif change=='unconfirmed':f.session.machine.confirmed=False
                elif change=='elevated':f.session.placement_source_height=.2
                elif change=='wrong_services':f.session.machine.services.session=object()
                elif change=='nav':f.host.executor.option.skill='NAV'
                else:f.host.executor.reported_end=True
                original=o.waypoints;o.update();self.assertIs(o.waypoints,original)
                self.assertEqual(self.emitted,[]);self.assertEqual(len(self.calls),3)

    def test_live_current_session_not_stale_cached_session(self):
        f=self.fixture();f.host.executor.session=NS(machine=NS(),placement_source_height=0.)
        f.owner.update();self.assertEqual(self.emitted,[])

    def test_capture_and_queue_original_gates_precede_any_selection(self):
        for gate in ('hand_force_N','tilt_rad','box_linear_speed','base_linear_speed','clearance','dwell','queue'):
            with self.subTest(gate=gate):
                f=self.fixture(queue_pass=gate!='queue')
                if gate in f.metrics:f.metrics[gate]=.11 if gate!='hand_force_N' else 4.
                elif gate=='clearance':f.owner.clearance_gate=lambda m:False
                elif gate=='dwell':f.owner.captured_since=2.99
                if gate=='queue':
                    with self.assertRaisesRegex(RuntimeError,'fold_handoff_pending_queue_refused'):f.owner.update()
                else:f.owner.update()
                self.assertEqual(self.emitted,[]);self.assertEqual(self.calls,[])

    def test_arrival_capture_never_calls_binding(self):
        f=self.fixture();f.owner.phase='ARRIVAL_CAPTURE';f.owner.native_arrival=object()
        f.owner.reference=f.owner.compact_goal.copy();f.owner.update()
        self.assertEqual(f.owner.phase,'STOW_VERIFY');self.assertEqual(self.emitted,[])
        self.assertEqual(len(self.calls),1)

    def test_phase_string_cannot_bypass_capture_witness(self):
        f=self.fixture();callback=vars(f.module)[CALLBACK]
        for kwargs in ({'capture':False,'queued':{'screen_pass':True},'now':3.},
                       {'capture':True,'queued':{'screen_pass':False},'now':3.},
                       {'capture':True,'queued':{'screen_pass':True},'now':4.}):
            with self.assertRaisesRegex(RuntimeError,'caller witness'):callback(f.owner,q(0.),**kwargs)
        self.assertEqual(self.emitted,[])

    def test_original_full_path_refusal_is_still_executed(self):
        f=self.fixture(guard=lambda a,b:'fixture blocked')
        original=f.owner.waypoints
        with self.assertRaisesRegex(RuntimeError,'failure_stow_path_blocked:fixture blocked'):f.owner.update()
        self.assertIs(f.owner.waypoints,original);self.assertIsNone(f.owner.segment_start)
        self.assertFalse(self.emitted[0]['guarded_candidate_found'])

    def test_unknown_guard_no_selection_original_recheck_preserved(self):
        f=self.fixture(guard=lambda a,b:None);original=f.owner.waypoints;f.owner.update()
        self.assertIs(f.owner.waypoints,original)
        self.assertEqual(self.emitted[0]['status'],'GUARD_UNKNOWN_ORIGINAL_FOR_NATIVE_RECHECK')
        # The original caller's semantics are unchanged, NOT certified safe.
        self.assertEqual(len(self.calls),4)

    def test_guard_mutation_detected_before_waypoint_assignment(self):
        f=self.fixture();original=f.owner.waypoints
        def corrupt(a,b):f.owner.s.queue.append(Vec([1.]*18));return ''
        f.owner.native.guard.segment=corrupt
        with self.assertRaisesRegex(RuntimeError,'query changed'):f.owner.update()
        self.assertIs(f.owner.waypoints,original);self.assertEqual(self.emitted,[])

    def test_immutable_check_failure_not_suppressed(self):
        f=self.fixture()
        def refuse():raise RuntimeError('immutable failed')
        f.session.machine.services.assert_immutable=refuse
        with self.assertRaisesRegex(RuntimeError,'immutable failed'):f.owner.update()
        self.assertEqual(self.calls,[])

    def test_evidence_sink_cannot_silently_mutate_control(self):
        f=self.fixture();original=f.owner.waypoints
        vars(f.module).pop(CALLBACK)
        bind_to_host(f.host,f.module,enabled=True,emit=lambda r:setattr(f.owner,'reference',q(.8)))
        with self.assertRaisesRegex(RuntimeError,'sink mutated'):f.owner.update()
        self.assertIs(f.owner.waypoints,original)

    def test_duplicate_or_wrong_source_binding_refused(self):
        f=self.fixture()
        with self.assertRaises(ValueError):bind_to_host(f.host,f.module,enabled=True,emit=self.emitted.append)
        self.path.write_text(self.original)
        with self.assertRaises(ValueError):bind_to_host(f.host,f.module,enabled=True,emit=self.emitted.append)

    def test_final_four_seconds_original_code_not_shortened(self):
        f=self.fixture();o=f.owner;o.phase='STOW_VERIFY';o.reference=o.compact_goal.copy()
        o.update();self.assertFalse(o.complete)
        o.s.data.time=6.995;o.update();self.assertFalse(o.complete)
        o.s.data.time=7.;o.update();self.assertTrue(o.complete)
        self.assertEqual(self.emitted,[])

    def test_bundle_is_local_delta_not_new_freeze_or_hot_edit(self):
        before=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
        out=Path(self.tmp.name)/'bundle';m=build(PACKAGE,out)
        self.assertFalse(m['default_enabled']);self.assertFalse(m['physical_execution_authorized'])
        self.assertEqual(before,hashlib.sha256(SOURCE.read_bytes()).hexdigest())
        for rel in ALIASES:
            self.assertEqual(restore_stall_source((out/'source-delta'/rel).read_text()),self.original)
        with self.assertRaises(FileExistsError):build(PACKAGE,out)
        with self.assertRaises(ValueError):build(PACKAGE,PACKAGE/'do-not-write')


if __name__ == '__main__':unittest.main()
