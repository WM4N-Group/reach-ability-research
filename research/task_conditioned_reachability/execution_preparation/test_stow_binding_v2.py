"""V2 repair regression. Actual pinned ORIGINAL selected_push_session factory
creates the root/proxy graph; geometry and Machine construction stay fixtures.
No Runtime/Host/Actor/MjModel/physics construction or outcome replay.
"""
import importlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace as NS
import unittest
import numpy as np
from . import native_stow_path_binding as v1
from . import native_stow_path_binding_v2 as v2
from . import test_native_stow_path_binding as fixture_support
PACKAGE=fixture_support.PACKAGE


class TargetViewBindingRepairTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.dont_write_bytecode=True
        def fence(event,args):
            if event in ('socket.connect','socket.getaddrinfo','subprocess.Popen','os.system','os.fork','os.posix_spawn'):
                raise AssertionError('No remote/process or simulation launcher')
            if event=='import' and str(args[0]).split('.')[0] in ('torch','mujoco','onnxruntime','requests','httpx'):
                raise AssertionError('No Actor/physics/model imports in alias-graph regression')
        sys.addaudithook(fence)
        source=(PACKAGE/'reference-source').resolve();sys.path.insert(0,str(source))
        # These imports load definitions only. Do not import a Runtime adapter.
        cls.api=importlib.import_module('ainav.native.registered_push_api')
        cls.native=importlib.import_module('mujoco_zyh.native_behavior_executor')
        cls.original_compile=cls.api._compile_registered_push_machine
        cls.pins=[]
        base=json.loads((PACKAGE/'BASELINE_RELEASE_v1.json').read_text())
        import hashlib
        for name in ('ainav.native.registered_push_api','mujoco_zyh.native_behavior_executor'):
            p=Path(sys.modules[name].__file__).resolve();rel=str(p.relative_to(source))
            h=hashlib.sha256(p.read_bytes()).hexdigest()
            assert h==base['complete_reference_source_files_sha256'][rel]
            cls.pins.append(dict(path=str(p),sha256=h))

    def fixture(self):
        # Reuse only original method execution harness; replace its manually
        # flattened runtime graph with the ACTUAL original session factory graph.
        harness=fixture_support.NativeSourceBindingTests();harness.setUp();self.addCleanup(harness.doCleanups)
        f=harness.fixture(enabled=False);o=f.owner;view=o.s
        view.model=object();view.cfg=NS(push_distance=.6);view.scene=object()
        context=NS(cfg=view.cfg,scene=view.scene,_env=NS());view.target_context=context
        view.controller=NS(env=context);view.qids=np.arange(18);view.data.qpos=np.zeros(18)
        goal=np.array([[2.41,-2.,0.]])
        tensor=NS(numpy=lambda:goal);tensor.detach=lambda:tensor;tensor.cpu=lambda:tensor
        view.box_push_target=tensor
        vars(f.module)['np']=np
        view.termination=lambda:{};view.refresh=lambda:None
        # Root and target wrappers intentionally distinct, physical aliases exact.
        root=NS(model=view.model,data=view.data,queue=view.queue)
        class RootRuntimeFixture(NS):
            def push_enter(self,*args,**kwargs):raise AssertionError('No policy constructor invocation')
        runtime=RootRuntimeFixture(sim=root,last=o.r.last,step_count=13750,staircase=NS(),push={})
        option=NS(skill='PUSH',parameters=(('goal_world_x_m',1.82),('goal_world_y_m',-2.),('surface_height_m',0.),('push_distance_m',.6)),
                  original_push_goal_sha256=self.native.array_sha(view.box_push_target.detach().cpu().numpy()))
        class MachineFixture:
            def __init__(self,r,tasks):self.r=r;self.tasks=tasks
        self.api._compile_registered_push_machine=lambda *a,**k:(MachineFixture,{'role':'CPU_MACHINE_CONSTRUCTOR_FIXTURE'})
        self.addCleanup(setattr,self.api,'_compile_registered_push_machine',type(self).original_compile)
        # Full ORIGINAL function body executes: actual native class, proxy copy,
        # selected-view alias, root runtime and original NativeOptionSession init.
        session=self.api._selected_registered_push_session(runtime,'unused-no-SDK-compile',option,
            view=view,binding_receipt={'controller_env_is_explicit_context':True},extra_guards=lambda:None)
        native=session.machine;proxy=native.r
        o.r=proxy;o.original_goal=view.box_push_target.detach().cpu().numpy().copy()
        services=NS(native=native,p=view,session=session,assert_immutable=lambda:None)
        session.machine=NS(native=native,services=services,confirmed=True,brake=NS(r=proxy,stow=o))
        session.placement_source_height=0.
        f.host.r=runtime;f.host.executor.runtime=runtime;f.host.executor.session=session
        f.session=session;f.runtime=runtime;f.view=view;f.root=root;f.proxy=proxy;f.harness=harness
        return f

    def test_exact_original_factory_reproduces_v1_failure_and_v2_accepts(self):
        f=self.fixture()
        self.assertIsInstance(f.session,self.native.NativeOptionSession)
        self.assertIs(f.session.runtime,f.runtime)
        self.assertIsNot(f.runtime.sim,f.view);self.assertIs(f.proxy.sim,f.view)
        with self.assertRaisesRegex(RuntimeError,'owner/runtime identity mismatch'):v1._selected_session(f.host,f.owner)
        self.assertIs(v2._selected_session(f.host,f.owner),f.session)

    def test_repaired_binding_reaches_original_update_and_begin_segment(self):
        f=self.fixture();emitted=[]
        v2.bind_to_host(f.host,f.module,enabled=True,emit=emitted.append)
        f.owner.update()
        self.assertEqual(f.owner.phase,'PROTECTED_STOW')
        self.assertEqual(len(f.owner.waypoints),1)
        self.assertEqual(len(emitted),1)
        self.assertTrue(emitted[0]['equivalent_to_direct_baseline'])
        self.assertEqual(emitted[0]['physical_commands_issued_by_optimizer'],0)
        self.assertIs(f.runtime.sim.data,f.view.data)

    def test_repair_changes_no_other_v1_function_or_reference_law(self):
        import ast
        a={n.name:ast.dump(n,include_attributes=False) for n in ast.parse(Path(v1.__file__).read_text()).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
        b={n.name:ast.dump(n,include_attributes=False) for n in ast.parse(Path(v2.__file__).read_text()).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
        self.assertEqual(set(a),set(b))
        self.assertEqual({k:v for k,v in a.items() if k!='_selected_session'},
                         {k:v for k,v in b.items() if k!='_selected_session'})

    def test_wrong_world_or_FIFO_not_silently_accepted(self):
        for field in ('model','data','queue'):
            with self.subTest(field=field):
                f=self.fixture();setattr(f.root,field,list(f.view.queue) if field=='queue' else object())
                with self.assertRaisesRegex(RuntimeError,'root model/data/FIFO'):v2._selected_session(f.host,f.owner)

    def test_wrong_root_or_proxy_or_stale_last_still_refused(self):
        for change in ('host','executor','native','brake','last'):
            with self.subTest(change=change):
                f=self.fixture()
                if change=='host':f.host.r=object()
                elif change=='executor':f.host.executor.runtime=object()
                elif change=='native':f.session.machine.native.r=NS(sim=f.view)
                elif change=='brake':f.session.machine.brake.r=NS(sim=f.view)
                else:f.proxy.last=NS(position=f.runtime.last.position.copy())
                with self.assertRaises(RuntimeError):v2._selected_session(f.host,f.owner)

    def test_foreign_controller_context_or_false_receipt_refused(self):
        for change in ('controller','cfg','scene','receipt'):
            with self.subTest(change=change):
                f=self.fixture()
                if change=='controller':f.view.controller.env=object()
                elif change=='cfg':f.view.target_context.cfg=object()
                elif change=='scene':f.view.target_context.scene=object()
                else:f.session.binding_receipt['controller_env_is_explicit_context']=False
                with self.assertRaisesRegex(RuntimeError,'controller/context'):v2._selected_session(f.host,f.owner)

    def test_out_of_scope_still_unchanged(self):
        for change in ('unconfirmed','wrong_owner','wrong_services','NAV','elevated'):
            with self.subTest(change=change):
                f=self.fixture()
                if change=='unconfirmed':f.session.machine.confirmed=False
                elif change=='wrong_owner':f.session.machine.brake.stow=object()
                elif change=='wrong_services':f.session.machine.services.session=object()
                elif change=='NAV':f.host.executor.option.skill='NAV'
                else:f.session.placement_source_height=.2
                self.assertIsNone(v2._selected_session(f.host,f.owner))

    def test_v2_default_off_still_does_not_read_host(self):
        self.assertEqual(v2.bind_to_host(None,None),{'status':'DEFAULT_DISABLED','installed':False})


if __name__=='__main__':unittest.main()
