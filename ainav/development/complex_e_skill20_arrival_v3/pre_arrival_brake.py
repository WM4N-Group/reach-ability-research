"""One DEV early-brake hypothesis, not a placement/stability certificate.

Start the SAME original guarded brake up to 40mm before the docking plane.
Never claim geometry has passed: final placement/NN/stow success stays inherited.
No native imports when disabled. No original module/class/source monkeypatch.
"""
from pathlib import Path
import hashlib,importlib,sys,math
from v4_native_asset import require

HANDOFF_SHA='b364ff970bd89db72bbff668c4b90c7c7486eec660315e8ee5ce649de9d68c53'
POLICY='DEV_PRE_ARRIVAL_ORIGINAL_BRAKE_40MM_20261116_v1'
MARGIN_M=.04  # ONE preregistered DEV hypothesis, not a fitted dynamics model.


def entry_candidate(measurement,contract):
    """Native-side trigger only; does not alter/replace any measured field."""
    if measurement['placement_geometry_verified'] or measurement['task_geometry_pass']:return False
    position=measurement['actual_box_position_m'];velocity=measurement['actual_box_linear_velocity_m_s']
    gap=measurement['actual_signed_dock_gap_m']
    values=(*position,*velocity,gap,*contract.public_goal_xy_m,*contract.box_size_m)
    require(len(position)==len(velocity)==3 and all(math.isfinite(float(v))for v in values),
            'Actual finite native placement state required')
    # Same registered ground, same Y/height, approach from +gap, still moving +X.
    # Far away, stationary, reversed, past the plane or tilted enough to spoil
    # this measured dock gap do not get a fabricated placement proof.
    return bool(contract.source_surface_height_m==0. and
        contract.mode=='declared_native_stop_offset' and contract.native_stop_distance_m==.11 and
        contract.box_size_m==(2.4,1.4,.2) and
        0.<gap<=MARGIN_M and velocity[0]>0. and
        abs(position[1]-contract.public_goal_xy_m[1])<contract.public_XY_tolerance_m and
        abs(position[2]-contract.source_surface_height_m-contract.box_size_m[2]/2)<.02)


def machine_class(*,source_root=None,enabled=False):
    require(type(enabled)is bool,'Explicit source owner opt-in')
    if not enabled:return None
    root=Path(source_root).resolve(strict=True);path=root/'ainav/native/placement_handoff.py'
    require(not path.is_symlink()and hashlib.sha256(path.read_bytes()).hexdigest()==HANDOFF_SHA,
            'Exact original two-phase placement implementation')
    sys.path.insert(0,str(root));module=importlib.import_module('ainav.native.placement_handoff')
    require(Path(module.__file__).resolve()==path,'No ambient placement state machine')
    Base=module.TwoPhasePlacementMachine

    class PreArrivalBrakeMachine(Base):
        # All original next_command/after_step/complete/results and verification
        # methods are INHERITED unchanged. Only the admissible entry may occur
        # before goal crossing; original _begin still screens actual FIFO/FF/etc.
        def update(self):
            if self.brake is None and self.native.phase=='run':
                self.services.assert_immutable();m=self.services.measure()
                if entry_candidate(m,self.services.contract):
                    ready=self._confirmation()  # Actual original clock, not a guessed result.
                    self.journal(dict(m,event='DEV_pre_arrival_original_brake_entry',policy=POLICY,
                        fixed_early_margin_m=MARGIN_M,native_confirmation=ready,
                        task_success_declared=False,geometry_relabelled=False,
                        state_is_private_native_control_not_planner_input=True,model_input=False))
                    self._begin(ready)  # EXACT original safety-screened brake, no new command.
            return super().update()

    # Installation only at the constructor boundary, never in a live session.
    def attach(session):
        old=session.machine
        require(type(old)is Base and old.brake is None and old._result is None and
                not old.confirmed and old.entry_receipt is None and old.native.phase=='prepare',
                'Only original pristine selected PUSH constructor, never resume/replace live state')
        require(old.services.native is old.native and old.services.session is session,
                'Retain the original session/services/native bindings')
        new=PreArrivalBrakeMachine(old.native,old.services,old.journal)
        require(all(getattr(PreArrivalBrakeMachine,n)is getattr(Base,n)
                    for n in ('_begin','_confirmation','_verify_complete','next_command','after_step','complete','results')),
                'Original safety, clock, issuance and full placement/stow completion retained')
        session.machine=new
        return new
    PreArrivalBrakeMachine.attach_pristine=staticmethod(attach)
    PreArrivalBrakeMachine.original_base=Base
    return PreArrivalBrakeMachine
