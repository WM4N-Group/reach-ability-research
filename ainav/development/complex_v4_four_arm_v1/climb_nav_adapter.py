"""Opt-in genuine CLIMB -> original compact NAV owner adapter, source candidate.

Connected by the V4 selected factory; still NOT physically qualified.
A same-tick observation alone is not accepted as a NAV witness: construct a
new typed live source from the real CLIMB and retained original placement.
During gait use the actually installed NAV owner, not the expired CLIMB pose.
All original NAV actor/update/command/arrival methods remain inherited.
"""
from dataclasses import dataclass
from pathlib import Path
import ast,hashlib,importlib,sys,textwrap
from v4_native_asset import require
from climb_nav_source import ActualClimbNavSourceObservation, source_readiness
from elevated_terminal import deck_normal_loads

NAV_SHA = 'bd173adeb4d31f651f5d8d5a9c2e37c6129421aa21c39edd09e5e986ac501361'
PLACEMENT_SHA = '461d4146aeed1622be01f1952a1b4d582eab631cbf14f9defbdc3e0a78099196'
_CLASS_SEAL = object()
OLD_TYPE = 'isinstance(capture_witness,(ActualCaptureWitness,ActualArrivalSupportWitness,ActualPushStowSupportWitness))'
NEW_TYPE = 'isinstance(capture_witness,(ActualCaptureWitness,ActualArrivalSupportWitness,ActualPushStowSupportWitness,LiveClimbNavSourceWitness))'
OLD_CONTACT = 'check_object_contacts(self.r,self.registry)'
NEW_CONTACT = 'check_object_contacts(self.r,self.registry,entered_climb_refs=self.capture_witness.entered_objects(self.r))'


def changed_methods(text):
    cls=next(n for n in ast.parse(text).body if isinstance(n,ast.ClassDef)and n.name=='RegisteredCompactNav')
    methods={n.name:ast.get_source_segment(text,n)for n in cls.body if isinstance(n,ast.FunctionDef)}
    require(methods['__init__'].count(OLD_TYPE)==1 and methods['check_guards'].count(OLD_CONTACT)==1,
            'Exact two original NAV source sites')
    new_init=methods['__init__'].replace(OLD_TYPE,NEW_TYPE,1)
    new_guard=methods['check_guards'].replace(OLD_CONTACT,NEW_CONTACT,1)
    require(new_init.replace(NEW_TYPE,OLD_TYPE,1)==methods['__init__']
            and new_guard.replace(NEW_CONTACT,OLD_CONTACT,1)==methods['check_guards'],
            'No removed original NAV source/history/effort/body/arrival checks')
    return textwrap.dedent(new_init),textwrap.dedent(new_guard)


def ownership_phase(*,executor,source_session,nav_owner,runtime,origin_tick,origin_time):
    """Identity/time switch, not a stand-in for native type/physical guards."""
    require(executor.runtime is runtime and executor.fatal is False,'Same live original executor')
    if executor.session is source_session:
        require(runtime.step_count==origin_tick and float(runtime.sim.data.time)==origin_time
                and executor.reported_end and executor.last_outcome=='succeeded'
                and source_session.outcome=='succeeded','Only the genuine same-tick source boundary may construct NAV')
        return 'SOURCE_BOUNDARY'
    session=executor.session
    require(nav_owner is not None and session is not None and session.runtime is runtime and session.entered
            and getattr(session.machine,'native_nav',None)is nav_owner
            and executor.option is not None and executor.option.skill=='NAV'
            and executor.last_outcome in(None,'succeeded') and session.outcome in('running','succeeded'),
            'Only this actually installed original NAV may take source contact authority')
    require(runtime.step_count>=origin_tick and executor.previous_tick==runtime.step_count
            and abs(float(runtime.sim.data.time)-runtime.step_count*.005)<=1e-7,
            'Actual consecutive issued NAV/current200Hz clock')
    return 'ACTIVE_NAV'


@dataclass(frozen=True)
class ClimbNavOwnerReferences:
    """True issued source refs/guard/limits; NOT Capture/failed-PUSH/HOLD."""
    r:object
    last_two:tuple
    guard:object
    limits:object
    original_climb_session:object


class LiveClimbNavSourceWitness:
    def __init__(self,observation,placements,nav_type):
        require(type(observation)is ActualClimbNavSourceObservation,
                'Actual guarded CLIMB observation required, not a scalar fixture')
        require(getattr(nav_type,'_climb_nav_class_seal',None)is _CLASS_SEAL,
                'Exact opt-in original NAV subclass')
        require(observation.validate_same_tick(observation.r),'Original four-foot12N/selected-object source not ready')
        self.origin=observation;self.r=observation.r;self.source_session=observation.session
        self.executor=observation.executor;self.original_registry=observation.registry
        self.object_ref=observation.actual_object_ref;self.support_ref=observation.surface.ref
        self.nav_type=nav_type;self.nav_owner=None;self.construction_attempted=False;self.revoked=False
        self.placements=placements;self._check_placement_type()
        self._placement_current()
        from ainav.native.scene_registry import SceneRegistry
        r=self.original_registry
        self.registry=SceneRegistry(r.objects.values(),(*r.surfaces.values(),observation.surface),r.goal,retired_objects=r.retired_objects)
        self.owner=ClimbNavOwnerReferences(self.r,tuple(v.copy()for v in observation.last_two),
            observation.original_guard,observation.original_limits.copy(),self.source_session)
        self._world=(self.r.sim.model,self.r.sim.data,self.r.sim.queue)

    def _check_placement_type(self):
        path=Path(__file__).resolve().parent.parent/'complex_dual_route_v1/terminal_stop.py'
        require(not path.is_symlink()and hashlib.sha256(path.read_bytes()).hexdigest()==PLACEMENT_SHA,
                'Exact original actual placement evidence')
        sys.path.insert(0,str(path.parent));module=importlib.import_module('terminal_stop')
        require(Path(module.__file__).resolve()==path and type(self.placements)is module.ActualPlacementEvidence
                and self.placements.r is self.r and self.placements.registry is self.original_registry,
                'Actual same-world original placement evidence, not a callback/oracle')

    def _placement_current(self):
        from ainav.native.placement_handoff import TwoPhasePlacementMachine
        row=self.placements.records.get(self.object_ref)
        require(row is not None and row['contract'].sha256==row['contract_sha256']
                and row['receipt'].status=='succeeded' and row['receipt'].option_sha256==row['option_sha256']
                and row['session'].machine.complete
                and row['session'].machine.brake.stow.complete
                and row['session'].machine.brake.stow.phase=='STOW_VERIFIED'
                and row['contract'].target_ref==self.object_ref
                and any(s is row['session']for s in self.executor.sessions)
                and isinstance(row['session'].machine,TwoPhasePlacementMachine),
                'Retained genuine original selected placement/session/immutable goal')
        obj=next(o for o in self.placements.scene['objects']if o['public_ref']==self.object_ref)
        require(row['contract'].public_goal_xy_m==tuple(obj['required_goal_xy_m']),
                'Current source must be the original required placement, not another finite goal')
        services=row['session'].machine.services;services.assert_immutable()
        require(services.session is row['session']and services.contract is row['contract']
                and services.measure()['placement_geometry_verified'],
                'Original placement geometric gate remains true; no new drift tolerance')

    def begin_constructor(self,nav):
        require(not self.revoked and not self.construction_attempted and type(nav)is self.nav_type,
                'One exact original NAV construction from this real source, no retry/alternative')
        self.validate(self.r)
        self.construction_attempted=True

    def attach_nav(self,nav):
        require(self.construction_attempted and not self.revoked and self.nav_owner is None
                and type(nav)is self.nav_type and nav.r is self.r and nav.registry is self.registry
                and nav.capture_witness is self,'Exact constructed original NAV/source/registry identity')
        self.nav_owner=nav

    def validate(self,runtime):
        require(runtime is self.r and not self.revoked and all(a is b for a,b in zip(self._world,
                (runtime.sim.model,runtime.sim.data,runtime.sim.queue))), 'Live CLIMB-NAV source world/FIFO revoked')
        require(self.origin.guard_callback()is not False,'Actual Data owner/resource guard refused')
        phase=ownership_phase(executor=self.executor,source_session=self.source_session,nav_owner=self.nav_owner,
            runtime=self.r,origin_tick=self.origin.observed_tick,origin_time=self.origin.observed_time)
        if phase=='SOURCE_BOUNDARY':
            require(self.origin.validate_same_tick(runtime),'Actual CLIMB source no longer ready')
        else:
            from mujoco_zyh.native_behavior_executor import NativeOptionSession
            from ainav.native.registered_nav_factory import RegisteredNavMachine
            session=self.executor.session
            require(type(session)is NativeOptionSession and isinstance(session.machine,RegisteredNavMachine)
                    and session.machine.r is runtime and self.nav_owner.r is runtime
                    and type(self.nav_owner)is self.nav_type and self.nav_owner.capture_witness is self,
                    'Exact actual original NAV session, not an owner/phase label')
            # Do NOT demand four-foot12N or the old stopped CLIMB pose during
            # the original NAV gait. Source/arrival boundaries retain12N; active
            # gait retains original actor/guard/contact/effort/footprint gates.
            self._current_support(require_stopped=bool(self.nav_owner.complete))
        self._placement_current()
        return True

    def _current_support(self,*,require_stopped):
        import numpy as np
        import mujoco
        from ainav.native.scene_registry import RegisteredTerrain,SurfaceSpec
        from mujoco_zyh.native_behavior_executor import world_snapshot
        p=self.r.sim;before=world_snapshot(self.r)
        obj=self.original_registry.objects[self.object_ref]
        binding=self.source_session.machine.binding
        bid=int(p.model.body(obj.body_name).id);gid=int(p.model.geom(obj.body_name+'_geom').id)
        require(bid==binding.body_id and int(p.model.geom_bodyid[gid])==bid,
                'Actual retained selected CLIMB support body/geom')
        geometry=RegisteredTerrain(self.original_registry).surface_geometry(p,self.object_ref)
        require(abs(geometry['top']-self.origin.surface.top_z_m)<=.01,'Original selected support layer changed')
        x0,y,L,W=geometry['front'],geometry['lane_y_m'],geometry['length'],geometry['width']
        surface=SurfaceSpec(self.support_ref,obj.body_name+'_geom',(x0,x0+L,y-W/2,y+W/2),geometry['top'])
        goal=self.nav_owner.goal
        require(x0+.35<goal[0]<x0+L-.35 and y-W/2+.3<goal[1]<y+W/2-.3,
                'Original NAV goal footprint must remain on actual selected support')
        if require_stopped:
            feet=[int(p.model.body(n+'_foot').id)for n in('FR','FL','RR','RL')]
            mapping={g:feet.index(int(p.model.geom_bodyid[g]))for g in range(p.model.ngeom)if int(p.model.geom_bodyid[g])in feet}
            contacts=[]
            for i in range(p.data.ncon):
                contact=p.data.contact[i]
                if gid not in(int(contact.geom1),int(contact.geom2)):continue
                force=np.zeros(6);mujoco.mj_contactForce(p.model,p.data,i,force)
                contacts.append((int(contact.geom1),int(contact.geom2),[float(v)for v in contact.frame[:3]],float(force[0])))
            loads=deck_normal_loads(mapping,gid,contacts)
            status=source_readiness(surface,feet=p.data.xpos[feet].tolist(),total_vertical_load_N=p.forces[feet,2].tolist(),
                selected_contact_normal_N=loads,base_xy=p.data.qpos[:2].tolist(),goal_xy=goal)
            require(status['necessary_source_ready'],'Actual stopped NAV arrival must retain four-foot12N on this selected object')
        require(world_snapshot(self.r)==before,'Live support check changed actual world/FIFO')

    def entered_objects(self,runtime):
        self.validate(runtime)
        return frozenset((self.object_ref,))

    def report(self):
        session=self.executor.session
        active=bool(not self.revoked and self.nav_owner is not None and session is not None
            and session is not self.source_session and session.runtime is self.r and session.entered
            and getattr(session.machine,'native_nav',None)is self.nav_owner
            and self.executor.option is not None and self.executor.option.skill=='NAV'
            and self.executor.fatal is False and self.executor.last_outcome in(None,'succeeded')
            and session.outcome in('running','succeeded')
            and self.executor.previous_tick==self.r.step_count
            and abs(float(self.r.sim.data.time)-self.r.step_count*.005)<=1e-7)
        return dict(kind='live_original_CLIMB_to_original_NAV_source_not_capture_or_failed_PUSH',
            support_ref=self.support_ref,actual_object_ref=self.object_ref,
            origin_CLIMB_time_s=self.origin.observed_time,origin_CLIMB_tick=self.origin.observed_tick,
            original_CLIMB_native_option_sha256=self.origin.original_option_sha256,
            source_height_m=self.origin.surface.top_z_m,construction_attempted=self.construction_attempted,
            native_NAV_constructed=self.nav_owner is not None,active_native_NAV_owner=active,
            constructor_pending_at_source_boundary=self.nav_owner is not None and session is self.source_session,
            private_registry_view_not_global_mutation=True,
            original_gait_not_replaced_by_four_foot_stationary_hold=True,model_input=False)


def nav_class(*,source_root=None,enabled=False):
    require(type(enabled)is bool,'Explicit owner opt-in')
    if not enabled:return None
    root=Path(source_root).resolve(strict=True);path=root/'ainav/native/registered_compact_nav.py'
    require(not path.is_symlink()and hashlib.sha256(path.read_bytes()).hexdigest()==NAV_SHA,'Exact original compact NAV')
    sys.path.insert(0,str(root));module=importlib.import_module('ainav.native.registered_compact_nav')
    require(Path(module.__file__).resolve()==path,'No ambient native NAV')
    init,guard=changed_methods(path.read_text());namespace=dict(vars(module),LiveClimbNavSourceWitness=LiveClimbNavSourceWitness)
    exec(compile(init,str(path)+'[typed-live-CLIMB-source]','exec'),namespace)
    exec(compile(guard,str(path)+'[actual-selected-source-contact]','exec'),namespace)
    original_init,original_guard=namespace['__init__'],namespace['check_guards']
    class ClimbSupportedOriginalNav(module.RegisteredCompactNav):
        _climb_nav_class_seal=_CLASS_SEAL
        def __init__(self,runtime,registry,*,capture_witness,goal_xy,journal):
            require(type(capture_witness)is LiveClimbNavSourceWitness and runtime is capture_witness.r
                    and registry is capture_witness.original_registry,'Exact new typed CLIMB source, never an expired observation')
            capture_witness.begin_constructor(self)
            try:
                original_init(self,runtime,capture_witness.registry,capture_witness=capture_witness,goal_xy=goal_xy,journal=journal)
                capture_witness.attach_nav(self)
            except BaseException:
                capture_witness.revoked=True
                raise
        def check_guards(self):return original_guard(self)
    ClimbSupportedOriginalNav.source_receipt=dict(original_source_sha256=NAV_SHA,
        narrow_type_and_entered_contact_source_delta_exactly_invertible=True,
        original_actor_update_command_after_step_arrival_unchanged=True,
        active_gait_not_subject_to_false_continuous_four_foot12N=True,
        actual_native_qualification=False,dispatch_authority_in_adapter_itself=False,
        factory_outer_guard_and_public_domain_qualification_is_separate=True)
    return ClimbSupportedOriginalNav


def make_live_source_witness(observation=None,placements=None,*,source_root=None,enabled=False):
    require(type(enabled)is bool,'Explicit owner opt-in')
    if not enabled:return None
    cls=nav_class(source_root=source_root,enabled=True)
    return LiveClimbNavSourceWitness(observation,placements,cls)
