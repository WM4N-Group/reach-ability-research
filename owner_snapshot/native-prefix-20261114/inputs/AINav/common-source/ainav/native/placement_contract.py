"""Immutable task placement versus native braking reference, BEFORE an attempt.

A derived drive target does not move the public task goal. Both identities must
be retained; existing 20mm public XY, 10mm dock and native 12cm settled bounds
are checked independently. No actor, dynamics, success threshold or live target
mutation is performed by this contract.
"""
from dataclasses import asdict,dataclass
import hashlib
import json
import math


def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,allow_nan=False,separators=(',',':')).encode()).hexdigest()


@dataclass(frozen=True)
class PlacementContract:
    target_ref: str
    public_goal_xy_m: tuple
    docking_plane_x_m: float
    box_size_m: tuple
    source_surface_height_m: float
    native_stop_distance_m: float
    mode: str
    public_XY_tolerance_m: float=.02
    original_dock_tolerance_m: float=.01
    original_native_settled_distance_m: float=.12

    def __post_init__(self):
        if (not isinstance(self.target_ref,str) or not self.target_ref
                or type(self.public_goal_xy_m) is not tuple or type(self.box_size_m) is not tuple
                or len(self.public_goal_xy_m)!=2 or len(self.box_size_m)!=3):
            raise ValueError('Explicit target and immutable XY/cuboid tuples required')
        values=(*self.public_goal_xy_m,self.docking_plane_x_m,*self.box_size_m,self.source_surface_height_m,self.native_stop_distance_m)
        if not all(type(x) in (float,int) and math.isfinite(x) for x in values) or min(self.box_size_m)<=0:raise ValueError('Finite registered placement geometry required')
        if self.mode not in ('uncompensated','declared_native_stop_offset'):raise ValueError('Explicit preregistered drive mode required')
        if not .05<=self.native_stop_distance_m<=.11:raise ValueError('Original native stop-distance domain required')
        if (self.public_XY_tolerance_m,self.original_dock_tolerance_m,self.original_native_settled_distance_m)!=(.02,.01,.12):
            raise ValueError('Task/public/dock/native thresholds must not be relaxed')
        if abs(self.public_goal_xy_m[0]+self.box_size_m[0]/2-self.docking_plane_x_m)>1e-8:
            raise ValueError('Public aligned-box goal must meet the declared plane')
    @property
    def drive_goal_xy_m(self):
        offset=0. if self.mode=='uncompensated' else self.native_stop_distance_m
        return (self.public_goal_xy_m[0]+offset,self.public_goal_xy_m[1])
    @property
    def sha256(self):return digest(asdict(self))
    def public(self):return dict(asdict(self),native_drive_goal_xy_m=list(self.drive_goal_xy_m),
        task_goal_is_not_drive_reference=True,world_state_predicted=False)

    def evaluate(self,*,box_position,rotation_world_from_box,native_goal_xy):
        if len(box_position)!=3 or len(native_goal_xy)!=2 or len(rotation_world_from_box)!=3 or any(len(r)!=3 for r in rotation_world_from_box):
            raise ValueError('Actual measured 3D box pose and native goal required')
        if not all(math.isfinite(x) for x in [*box_position,*native_goal_xy,*[v for row in rotation_world_from_box for v in row]]):
            raise ValueError('Finite actual placement measurements required')
        if any(abs(a-b)>1e-6 for a,b in zip(native_goal_xy,self.drive_goal_xy_m)):raise ValueError('Native drive goal was changed/rebased')
        extent=sum(abs(rotation_world_from_box[0][j])*self.box_size_m[j]/2 for j in range(3))
        gap=self.docking_plane_x_m-box_position[0]-extent
        public_error=math.hypot(box_position[0]-self.public_goal_xy_m[0],box_position[1]-self.public_goal_xy_m[1])
        drive_error=math.hypot(box_position[0]-native_goal_xy[0],box_position[1]-native_goal_xy[1])
        geometry_ok=(public_error<self.public_XY_tolerance_m and abs(gap)<=self.original_dock_tolerance_m
            and drive_error<self.original_native_settled_distance_m
            and abs(box_position[2]-self.source_surface_height_m-self.box_size_m[2]/2)<.02)
        return dict(public_XY_error_m=public_error,actual_signed_dock_gap_m=gap,native_drive_goal_error_m=drive_error,
            placement_geometry_verified=geometry_ok,native_goal_confirmed_separately_required=True,
            protected_stow_completion_separately_required=True,contract_sha256=self.sha256,model_input=False)


class PlacementThenGuardedStow:
    """Construct the existing guarded stow wrapper with an explicit contract.

    Dynamic subclassing is confined to the LOCAL completion wrapper, never the
    deployed NativeOptionSession class identity.
    """
    def __new__(cls,native,session,issued,journal,*,contract):
        from .goal_stow import GoalThenGuardedStow
        class MeasuredPlacement(GoalThenGuardedStow):
            def placement_receipt(self):
                if contract.sha256!=self.contract_sha:raise RuntimeError('Public placement contract changed')
                from mujoco_zyh.native_behavior_executor import array_sha
                p=self.native.r.sim;goal=p.box_push_target.detach().cpu().numpy()
                if array_sha(goal)!=self.native_goal_sha:raise RuntimeError('Original native drive goal changed')
                return contract.evaluate(box_position=p.data.xpos[p.box_id].tolist(),
                    rotation_world_from_box=p.data.xmat[p.box_id].reshape(3,3).tolist(),native_goal_xy=goal[0,:2].tolist())
            def _goal_verified(self):
                return self.native.finish is not None and self.placement_receipt()['placement_geometry_verified']
            @property
            def results(self):
                rows=super().results
                if self.stow is not None and self.stow.complete:
                    if self._result is not None:self._result.update(placement=self.placement_receipt(),
                        completion_definition='original native NN confirmation + frozen public XY/10mm dock + actual guarded stow',
                        original_native_drive_goal_sha256=self.native_goal_sha,public_placement_contract_sha256=self.contract_sha,
                        drive_reference_distinct_from_task_goal=True)
                return rows
        from mujoco_zyh.native_behavior_executor import array_sha
        obj=MeasuredPlacement(native,session,issued,journal);obj.contract=contract;obj.contract_sha=contract.sha256
        obj.native_goal_sha=array_sha(native.r.sim.box_push_target.detach().cpu().numpy())
        return obj


class PlacementTerrain:
    """Explicit selected placement diagnostics for the original single PUSH."""
    def __init__(self,contract):self.contract=contract
    def dock_metrics(self,view):
        return self.contract.evaluate(box_position=view.data.xpos[view.box_id].tolist(),
            rotation_world_from_box=view.data.xmat[view.box_id].reshape(3,3).tolist(),
            native_goal_xy=view.box_push_target.detach().cpu().numpy()[0,:2].tolist())


def wrap_placement_session(session,contract,journal):
    from mujoco_zyh.native_push_stop import IssuedPushObservation
    from types import MethodType
    view=session.machine.r.sim;observed=IssuedPushObservation(view)
    session.machine=PlacementThenGuardedStow(session.machine,session,observed,journal,contract=contract)
    original_after=session.after_step
    def after_actual_issue(this):
        original_after();observed.after_actual_issuance(this.runtime.last)
    session.after_step=MethodType(after_actual_issue,session)
    return session
