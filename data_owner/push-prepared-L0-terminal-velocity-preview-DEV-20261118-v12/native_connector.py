"""Source-only Data adapter, retaining the exact original session and motor path."""
from hashlib import sha256
from pathlib import Path
from types import FunctionType
import ast
import copy
import importlib
import inspect
import math
import textwrap

from terminal_action import BrakeAction, brake_eligible, preview_lead_m

HANDOFF_SHA = 'b364ff970bd89db72bbff668c4b90c7c7486eec660315e8ee5ce649de9d68c53'
FACTORY_SHA = '2da2c075e1316ab81251ac71f72004b927e769bfd88047a3af1a171d8d1d387e'
EXECUTOR_SHA = '8d42281aa890bd5224f7d8c0bacc2c44d1fa1bda0ba5a89fec8bffa59f701995'
INHERITED = ('_begin', '_confirmation', '_verify_complete', 'next_command', 'after_step', 'complete', 'results')


def need(ok, why):
    if not ok:
        raise RuntimeError(why)


def legal_original_contact(services):
    """Keep the original hand-contact predicate; no guessed/absent observations."""
    p = services.p
    box_api = services.native.r.push['bridge'].box_push
    return bool(box_api.hand_contact(p, p.hand_cfg)[0])


def new_machine_class(*, source_root=None, enabled=False):
    need(type(enabled) is bool, 'Explicit independent connector opt-in')
    if not enabled:
        return None
    path = Path(source_root).resolve(strict=True) / 'ainav/native/placement_handoff.py'
    need(not path.is_symlink() and sha256(path.read_bytes()).hexdigest() == HANDOFF_SHA, 'Exact qualified two-phase owner source')
    mod = importlib.import_module('ainav.native.placement_handoff')
    need(Path(mod.__file__) == path, 'No ambient placement alias')
    Base = mod.TwoPhasePlacementMachine
    old_update = Base.update
    source = textwrap.dedent(inspect.getsource(old_update))
    original = ast.parse(source)
    patched = copy.deepcopy(original)
    fingerprint = "self.native.phase=='run' and measurement['task_geometry_pass']"
    want = ast.dump(ast.parse(fingerprint, mode='eval').body, include_attributes=False)
    replacements = [n for n in ast.walk(patched) if isinstance(n, ast.If)
                    and ast.dump(n.test, include_attributes=False) == want]
    need(len(replacements) == 1, 'Find only the original brake-entry decision, not a safety predicate')
    gate = replacements[0]
    old_test = gate.test
    gate.test = ast.copy_location(ast.parse(
        "self.native.phase=='run' and (measurement['task_geometry_pass'] or self._should_request_early(measurement))", mode='eval').body, old_test)
    ast.fix_missing_locations(patched)
    ns = dict(old_update.__globals__)
    exec(compile(patched, str(path)+'[private-terminal-gate]', 'exec', dont_inherit=True), ns)
    private_update = ns['update']
    # Freeze verification proves the only AST change is the original branch condition.
    gate.test = old_test
    need(ast.dump(patched, include_attributes=False) == ast.dump(original, include_attributes=False),
         'Private update changes only brake request predicate, not measurement, clock, command or terminal')

    class TerminalConnector(Base):
        def __init__(self, native, services, journal, action):
            super().__init__(native, services, journal)
            need(type(action) is BrakeAction, 'Fixed action for this world only')
            self._action = action
            self._expected = (action.index, action.lead_m)
            self._early_requested = False
            self._contact_audit_rows = 0

        def update(self):
            a = self._action
            need(type(a) is BrakeAction and (a.index, a.lead_m) == self._expected, 'Terminal action changed mid-attempt')
            if a.index == 0:
                return old_update(self)  # exact baseline call, no extra guard read
            return private_update(self)

        def _should_request_early(self, m):
            a = self._action
            # This executes AFTER the existing original measurement and confirmation.
            # No policy action can bypass the original _begin / FF / FIFO / goal checks.
            geometry = brake_eligible(a, m, self.services.contract,
                                      actual_legal_hand=True, contact_seen=True)
            d=m['actual_signed_dock_gap_m']
            if not 0. < d <= .20:  # broader read-only observation, never action authority
                return False
            seen = self.services.clock_report()['native_contact_seen']
            need(type(seen) is bool, 'Original actual contact history required')
            legal = legal_original_contact(self.services)  # same original predicate; exactly one at this call site
            sensor=self.services.p.scene.sensors['box_contact_hand'].data
            force=float(sensor.force_matrix_w.sum(dim=(1,2)).norm(dim=1)[0].item())
            finite_pos=bool(sensor.contact_pos_w[:,0,0].isfinite().all(dim=1)[0].item())
            should_request=bool(geometry and seen and legal)
            self._contact_audit_rows+=1
            need(self._contact_audit_rows<=960, 'Bounded private DEV contact rows; never silently drop')
            self.journal(dict(event='connector_same_tick_contact_gate', time_s=m['time_s'],
                gap_m=d, vx_mps=m['actual_box_linear_velocity_m_s'][0], geometry_speed_inside_action_profile=geometry,
                actual_preview_lead_m=preview_lead_m(a,m['actual_box_linear_velocity_m_s'][0]),
                historical_original_contact=seen, original_instant_hand_contact=legal,
                finite_original_hand_contact_position=finite_pos, actual_hand_force_norm_N=force if math.isfinite(force) else None,
                action_requested_by_gate=should_request, model_input=False, not_training=True))
            if not should_request:
                return False
            need(not self._early_requested, 'At most one guarded early request, no retry')
            self._early_requested = True
            self.journal(dict(event='connector_early_brake_requested', time_s=m['time_s'],
                action_index=a.index, lead_cap_m=a.lead_m, actual_gap_m=m['actual_signed_dock_gap_m'],
                actual_preview_lead_m=preview_lead_m(a,m['actual_box_linear_velocity_m_s'][0]),
                placement_inferred=False, no_command_or_reward_emitted=True, model_input=False))
            return True

    need(all(getattr(TerminalConnector, n) is getattr(Base, n) for n in INHERITED), 'Exact original brake, issue and terminal methods')

    def attach(session, action):
        m = session.machine
        need(type(m) is Base and m.brake is None and m._result is None and m.entry_receipt is None
             and m.confirmed is False and session.entered is False and m.native.phase == 'startup' and m.native.index == -1,
             'Only a fresh selected native constructor, no state replacement after entry')
        need(m.services.native is m.native and m.services.session is session, 'Original constructor/session aliases')
        new = TerminalConnector(m.native, m.services, m.journal, action)
        session.machine = new
        return new

    TerminalConnector.attach_pristine = staticmethod(attach)
    return TerminalConnector


def factory_class(original, *, source_root, factory_sha256, action, world_snapshot, enabled=False):
    """New factory type only. It must be frozen before the actual runtime starts."""
    if enabled is not True:
        return None
    need(type(action) is BrakeAction and isinstance(world_snapshot, FunctionType), 'One preregistered action and original no-physics witness')
    root = Path(source_root).resolve(strict=True)
    path = root / 'ainav/native/registered_skill_factory.py'
    mod = importlib.import_module('ainav.native.registered_skill_factory')
    api = importlib.import_module('mujoco_zyh.native_behavior_executor')
    ex = root / 'mujoco_zyh/native_behavior_executor.py'
    need(not ex.is_symlink() and Path(api.__file__) == ex and sha256(ex.read_bytes()).hexdigest() == EXECUTOR_SHA
         and api.world_snapshot is world_snapshot, 'Original pinned read-only native world snapshot')
    need(factory_sha256 == FACTORY_SHA and original is mod.RegisteredSkillSessionFactory and Path(mod.__file__) == path and not path.is_symlink()
         and sha256(path.read_bytes()).hexdigest() == factory_sha256, 'Exact original shared native factory')
    Machine = new_machine_class(source_root=root, enabled=True)
    class TerminalFactory(original):
        def __call__(self, option):
            need(option.skill == 'PUSH', 'Standalone PUSH connector cannot select NAV/CLIMB or protected actions')
            before = world_snapshot(self.r)
            session = super().__call__(option)
            need(session.runtime is self.r and world_snapshot(self.r) == before, 'Original same-world selected session')
            Machine.attach_pristine(session, action)
            need(world_snapshot(self.r) == before, 'Connector attachment cannot step or rewrite FIFO')
            return session
    return TerminalFactory
