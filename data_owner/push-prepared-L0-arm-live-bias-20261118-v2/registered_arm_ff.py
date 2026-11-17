"""SOURCE-ONLY startup-command candidate, not a controller or dispatch authority.

The ONLY proposed dynamics delta is the arm feedforward already constructed by
original PushEntry.command. Original standalone PD targets/gains/velocities and
all 12 leg feedforwards must match. No offset, clip, new world, forward, QP,
Actor, safety check, reset, queue operation or physical step occurs here.
A future parent must explicitly label this PREPARED L0, not unmodified L0/L1.
"""
import ast
import hashlib
from pathlib import Path
import types

ENTRY_SHA = 'c950304e392b41a10cded9f6e9890039807223f50e03ab5856f9c0315ddf0b6b'
STARTUP_SHA = 'a9c6ec0c2f51fe5a07acd067b907e2b0a402f14c985f338a8ca176a547c61d16'


def need(ok, message):
    if not ok:
        raise ValueError(message)


def _pinned(path, expected):
    path = Path(path)
    need(not path.is_symlink() and path.is_file(), 'Regular exact source, no symlink')
    raw = path.read_bytes()
    need(hashlib.sha256(raw).hexdigest() == expected, 'Exact source SHA required')
    return path, raw


def _load_startup(path):
    path, raw = _pinned(path, STARTUP_SHA)
    module = types.ModuleType('_data_pinned_original_L0_startup_for_source_FF')
    module.__file__ = str(path)
    # This pinned module has only stdlib imports/functions; no world or dispatch.
    exec(compile(raw, str(path), 'exec', dont_inherit=True), module.__dict__)
    return module


def _entry_arm_expression(path, np):
    path, raw = _pinned(path, ENTRY_SHA)
    tree = ast.parse(raw)
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'PushEntry')
    fn = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == 'command')
    gravity, arm = fn.body[2:4]
    need(ast.unparse(gravity) == 'gravity = p.data.qfrc_bias[p.dids[12:]]',
         'Exact original LIVE bias selection, not rebuilt gravity_data')
    need(ast.unparse(arm) == 'arm = r.Command(pm.REFERENCE.copy(), np.zeros(18), pm.KP.copy(), pm.KD.copy(), np.r_[np.zeros(12), gravity])',
         'Exact original registered arm command expression')
    # Copy ONLY these two original assignments. The QP, blend, legs and stage
    # update in PushEntry.command are deliberately NOT called or impersonated.
    prefix = ast.parse('p = r.sim\npm = r.push["model"]').body
    body = prefix + [gravity, arm] + ast.parse('return arm').body
    function = ast.FunctionDef(name='_registered_arm_command_expression',
        args=ast.arguments(posonlyargs=[], args=[ast.arg(arg='r')], kwonlyargs=[],
                           kw_defaults=[], defaults=[]), body=body, decorator_list=[])
    namespace = {'np': np}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[function], type_ignores=[])),
                 str(path)+'[arm-command-expression-only-NO-QP]', 'exec', dont_inherit=True), namespace)
    return namespace['_registered_arm_command_expression']


class _PreparedArmFFCommand:
    """Command construction only. Counts are NOT issued commands/physics fees."""
    def __init__(self, runtime, default, registered, np):
        self.r, self.default, self.registered, self.np = runtime, default, registered, np
        p = runtime.sim
        self.world = (p, p.model, p.data, p.queue)
        self.failed = False
        self.constructed = 0
        self.last_sample = None
        # Pin the original requested references at PREPARATION, not just compare
        # two namespaces which might share mutable KP/KD arrays at call time.
        baseline = default(p).array()
        need(baseline.shape == (5, 18) and np.isfinite(baseline).all() and
             np.array_equal(baseline[4], np.zeros(18)), 'Original finite zero-FF baseline')
        self.baseline = baseline.copy()
        self.baseline.flags.writeable = False

    def __call__(self, sim):
        try:
            need(not self.failed, 'Command-source failure latches; never resume')
            r, np = self.r, self.np
            need(sim is r.sim and all(a is b for a, b in zip(self.world,
                 (r.sim, r.sim.model, r.sim.data, r.sim.queue))), 'Same fresh startup world/FIFO aliases')
            original = self.default(sim)
            candidate = self.registered(r)
            need(type(original) is r.Command and type(candidate) is r.Command,
                 'Original command class, not a value-only stand-in')
            a, b = original.array(), candidate.array()
            need(a.shape == b.shape == (5, 18) and a.dtype == b.dtype and
                 np.isfinite(a).all() and np.isfinite(b).all(), 'Finite exact command layout/dtype')
            need(a.dtype == self.baseline.dtype and np.array_equal(a, self.baseline) and
                 np.array_equal(a[:4], b[:4]) and np.array_equal(a[4], np.zeros(18)) and
                 np.array_equal(b[4, :12], a[4, :12]),
                 'No change to original positions/velocities/gains/leg FF; no layering')
            bias = np.asarray(sim.data.qfrc_bias[sim.dids[12:]]).copy()
            need(bias.shape == (6,) and np.isfinite(bias).all() and
                 np.array_equal(b[4, 12:], bias), 'Unscaled original live arm bias only')
            # All arrays returned by this original expression must be detached
            # from live state and target/bias storage. No mutable FF view escapes.
            for array in (candidate.position, candidate.velocity, candidate.kp,
                          candidate.kd, candidate.feedforward):
                need(not any(np.shares_memory(array, state) for state in
                     (sim.data.qpos, sim.data.qvel, sim.data.qfrc_bias, sim.targets)),
                     'Command cannot alias live state/default targets')
            self.constructed += 1
            self.last_sample = dict(runtime_step=r.step_count, task_sim_s=float(sim.data.time),
                                    arm_feedforward_nm=bias.tolist())
            return candidate
        except BaseException:
            self.failed = True
            raise

    def snapshot(self):
        return dict(kind='PREPARED_L0_REGISTERED_ARM_LIVE_BIAS_SOURCE_CANDIDATE',
                    commands_constructed_not_issued=self.constructed, failed=self.failed,
                    last_command_source_sample=self.last_sample,
                    original_standalone_initialization_unchanged=False,
                    original_settle_control_flow_to_be_preserved=True,
                    original_registered_thresholds_to_be_preserved=True,
                    physical_or_skill_qualification=False, execution_permission=False,
                    entry_source_sha256=ENTRY_SHA, startup_source_sha256=STARTUP_SHA)


def prepare(runtime=None, *, original_physics_step=None, bridge_path=None,
            push_entry_path=None, startup_source_path=None, enabled=False):
    """Inert by default. Does not install into any parent or run any step.

    Integration into a future startup stepper is outstanding. This builder is
    not suitable for a natural predecessor, reset recovery or arbitrary world.
    """
    need(type(enabled) is bool, 'Explicit source-candidate opt-in')
    if not enabled:
        return None
    p = runtime.sim
    need(runtime.step_count == 0 and float(p.data.time) == 0. and not p.queue,
         'Only fresh task0/empty FIFO; never after predecessor or failed scope')
    need(tuple(float(x) for x in p.data.qpos[:3]) == (-.08, 0., .33),
         'Declared fresh L0 initial pose only')
    need(abs(float(p.model.opt.timestep)-.005) < 1e-12, 'Original 200Hz dt')
    import numpy as np
    base = _load_startup(startup_source_path)
    default, command_type = base._compile_default_PD(original_physics_step, bridge_path)
    need(runtime.Command is command_type, 'Actual original command class')
    registered = _entry_arm_expression(push_entry_path, np)
    return _PreparedArmFFCommand(runtime, default, registered, np)
