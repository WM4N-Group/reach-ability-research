"""Opt-in CLIMB motor-reference integration, not a task/actor modification.

One proposal is shared by the entry QP, policy/stop command and issued command.
Native leg blends remain intact; arm blending is replaced by the admitted motor
reference BEFORE each QP as well as after the native full-command blends. A
proposal is not history until the same-world runtime actually advances one tick.
No simulation rollout, world writes, fallback, retries or guard relaxation.
"""
import hashlib

_FIELDS = ('position', 'velocity', 'kp', 'kd', 'feedforward')


def arm_array(command):
    import numpy as np
    value = np.stack([getattr(command, name)[12:].copy() for name in _FIELDS])
    if value.shape != (5, 6) or not np.isfinite(value).all():
        raise ValueError('Finite original six-axis arm command required')
    return value


def arm_sha(value):
    import numpy as np
    return hashlib.sha256(np.asarray(value, dtype='<f8').tobytes()).hexdigest()


class ClimbArmTransaction:
    """Per-instance QP/command identity gate; fixture-testable without physics."""
    def __init__(self, *, tick, previous_arm, previous_reference, propose, journal):
        import numpy as np
        self.tick = int(tick)
        self.previous = np.array(previous_arm, dtype=float, copy=True)
        self.previous_reference = np.array(previous_reference, dtype=float, copy=True)
        if (self.tick < 2 or self.previous.shape != (5, 6)
                or self.previous_reference.shape != (6,)
                or not np.isfinite(self.previous).all()
                or not np.isfinite(self.previous_reference).all()):
            raise ValueError('Two actual issued references required, never duplicate seeds')
        self.propose, self.journal = propose, journal
        self.pending = None
        self.commits = 0
        self.qp_calls = 0
        self.last_receipt = None
        self._hooked = []

    def begin(self, tick, last):
        import numpy as np
        if self.pending is not None:
            raise RuntimeError('Uncommitted CLIMB proposal; no duplicate command or retry')
        if tick != self.tick or not np.array_equal(arm_array(last), self.previous):
            raise RuntimeError('Actual CLIMB issued history/clock differs; no rebase')
        reference_velocity = (self.previous[0]-self.previous_reference)/.005
        proposal, intervals = self.propose(self.previous.copy(), reference_velocity.copy())
        proposal = np.array(proposal, dtype=float, copy=True)
        if proposal.shape != (5, 6) or not np.isfinite(proposal).all():
            raise ValueError('Finite governed arm proposal required')
        # Motor velocity stays native zero; reference velocity is a separate
        # finite difference, not an extra PD velocity target.
        if np.any(proposal[1] != 0.) or not np.array_equal(proposal[2:4], self.previous[2:4]):
            raise RuntimeError('Original arm gains/zero motor velocity changed')
        self.pending = dict(tick=tick, arm=proposal, intervals=intervals,
                            qp_inputs=[], finalized=False)

    def apply(self, command):
        if self.pending is None:
            raise RuntimeError('CLIMB QP/command outside actual-tick proposal')
        for i, name in enumerate(_FIELDS):
            getattr(command, name)[12:] = self.pending['arm'][i]
        return command

    def install_qp(self, qp, label):
        if any(instance is qp for instance, _ in self._hooked):
            return
        if any(existing == label for _, existing in self._hooked):
            raise RuntimeError('CLIMB QP owner replaced within one session')
        original = qp.solve
        def solve(*args, **kwargs):
            # Original pinned Entry/Stop call solve(..., arm_command) positionally.
            if len(args) != 8 or kwargs:
                raise RuntimeError('Original CLIMB QP call contract changed')
            command = self.apply(args[-1])
            digest = arm_sha(arm_array(command))
            self.pending['qp_inputs'].append(dict(owner=label, arm_sha256=digest))
            result = original(*args)
            if arm_sha(arm_array(command)) != digest:
                raise RuntimeError('CLIMB QP mutated its arm input')
            return result
        qp.solve = solve
        self._hooked.append((qp, label))

    def finalize(self, command, *, expected_qp_calls):
        if self.pending is None or self.pending['finalized']:
            raise RuntimeError('CLIMB proposal missing or already finalized')
        if len(self.pending['qp_inputs']) != expected_qp_calls:
            raise RuntimeError('Original CLIMB QP was bypassed or called unexpectedly')
        command = self.apply(command)
        digest = arm_sha(arm_array(command))
        if any(row['arm_sha256'] != digest for row in self.pending['qp_inputs']):
            raise RuntimeError('QP/issued CLIMB arm command mismatch')
        self.pending['finalized'] = True
        self.pending['issued_sha256'] = digest
        return command

    def commit(self, tick, last):
        import numpy as np
        p = self.pending
        if p is None or not p['finalized'] or tick != self.tick+1:
            raise RuntimeError('One actual consecutive motor tick required to commit CLIMB proposal')
        actual = arm_array(last)
        if not np.array_equal(actual, p['arm']) or arm_sha(actual) != p['issued_sha256']:
            raise RuntimeError('Actual issued CLIMB command differs from QP proposal')
        receipt = dict(event='climb_arm_actual_issue', physical_tick=tick,
            proposal_sha256=arm_sha(p['arm']), issued_arm_sha256=arm_sha(actual),
            qp_inputs=p['qp_inputs'], motor_interval_receipts=p['intervals'],
            original_task_arm_goal=[0.]*6,
            motor_goal_only=True, model_input=False)
        self.journal(receipt)
        self.previous_reference = self.previous[0].copy()
        self.previous = actual.copy()
        self.tick = tick
        self.commits += 1
        self.qp_calls += len(p['qp_inputs'])
        self.last_receipt = receipt
        self.pending = None

    def report(self):
        return dict(policy='hard_interior_reference_gravity_only',
            actual_issued_commands=self.commits, actual_issued_qp_calls=self.qp_calls,
            pending_unissued_proposal=self.pending is not None,
            last_actual_issue=self.last_receipt, original_task_arm_goal=[0.]*6,
            original_hard_guard_enabled=True, trajectory_safety_proven=False)


class GovernedClimbMachine:
    """Wrap the measured-height native Machine; hooks only its own QP instances."""
    def __init__(self, native, runtime, witness, journal, *, goal_policy='hard_interior_reference_gravity_only'):
        import numpy as np
        import mujoco
        from .climb_arm_candidate import propose_climb_arm_step
        if goal_policy=='maximin_original_acceptance_gravity_only':
            from .climb_arm_reserve import propose_reserve_climb_arm_step as proposal_function
        elif goal_policy=='hard_interior_reference_gravity_only':
            proposal_function=propose_climb_arm_step
        else:
            raise ValueError('Reviewed CLIMB motor goal policy required')
        self.goal_policy=goal_policy
        self.native_machine, self.runtime = native, runtime
        witness.validate(runtime)
        history = getattr(witness.session, 'last_two', ())
        if (len(history) != 2 or getattr(witness, 'actual_issued_steps', 0) < 2
                or not np.array_equal(history[-1], runtime.last.position)):
            raise ValueError('Actual successful support-owner issued history required')
        p = runtime.sim
        self.qids, self.dids = p.qids[12:].copy(), p.dids[12:].copy()
        self.limits = p.model.jnt_range[p.jids[12:]].copy()
        self.effort = np.asarray(runtime.push['model'].EFFORT[12:], dtype=float).copy()
        self.gravity_data = mujoco.MjData(p.model)
        self.started_time = float(p.data.time)
        self.started_tick = runtime.step_count
        self.policy_owner = None
        native_gains = np.stack((runtime.push['model'].KP[12:], runtime.push['model'].KD[12:]))
        if not np.array_equal(arm_array(runtime.last)[2:4], native_gains):
            raise ValueError('Actual incoming arm gains differ from original CLIMB/Entry gains')
        self.gravity_evaluations = 0
        original_gains = arm_array(runtime.last)[2:4].copy()
        def propose(previous, reference_velocity):
            # Original gravity-only calculation on an independent MjData;
            # current-world generalized positions are only read, never written.
            data = self.gravity_data
            data.qpos[:] = p.data.qpos
            data.qvel[:] = 0.
            mujoco.mj_fwdPosition(p.model, data)
            mujoco.mj_fwdVelocity(p.model, data)
            gravity = np.zeros(p.model.nv)
            mujoco.mj_rne(p.model, data, 0, gravity)
            self.gravity_evaluations += 1
            pos, speed, ff, intervals = proposal_function(
                np.zeros(6), previous[0], reference_velocity,
                p.data.qpos[self.qids], p.data.qvel[self.dids],
                original_gains[0], original_gains[1], gravity[self.dids], previous[4],
                self.effort, self.limits)
            return np.stack((pos, np.zeros(6), *original_gains, ff)), intervals
        self.transaction = ClimbArmTransaction(tick=runtime.step_count,
            previous_arm=arm_array(runtime.last), previous_reference=history[-2][12:],
            propose=propose, journal=journal)

    def __getattr__(self, name):
        return getattr(self.native_machine, name)

    def next_command(self):
        import numpy as np
        r, native = self.runtime, self.native_machine
        if abs(float(r.sim.data.time)-self.started_time-(r.step_count-self.started_tick)*.005)>1e-7:
            raise RuntimeError('CLIMB governor actual physics clock differs')
        self.transaction.begin(r.step_count, r.last)
        if native.phase == 'prepare' and native.kind == 'climb':
            self.transaction.install_qp(native.preparation.qp, 'original_climb_entry')
            expected = 1
        elif native.kind == 'climb' and native.phase != 'startup':
            c, stop = native.r.c, native.r.stop
            if (not np.array_equal(c.qids[12:], self.qids)
                    or not np.array_equal(c.dids[12:], self.dids)
                    or np.any(c.reference[12:] != 0.)):
                raise RuntimeError('Original zero CLIMB task/arm joint ordering changed')
            if self.policy_owner is None:
                original = c.policy_command
                def policy_command():
                    command = original()
                    gains = arm_array(command)[2:4]
                    if not np.array_equal(gains, self.transaction.previous[2:4]):
                        raise RuntimeError('Original CLIMB actor arm gains differ')
                    return self.transaction.apply(command)
                c.policy_command = policy_command
                self.policy_owner = c
            if c is not self.policy_owner or stop.failure:
                raise RuntimeError('Original CLIMB policy/stop owner lost')
            self.transaction.install_qp(stop.qp, 'original_climb_stop')
            expected = None  # Stop.command itself may activate takeover on this tick.
        else:
            raise RuntimeError('Governed CLIMB cannot issue unrelated startup/skill commands')
        command = native.next_command()
        if expected is None:
            if stop.failure:
                raise RuntimeError('Original CLIMB stop refused command:'+str(stop.failure))
            expected = int(bool(stop.active))
        # Native entry (.3s) and skill (.2s) leg blends remain unchanged. Arm
        # fields here are EXACTLY those already consumed by the original QP.
        return self.transaction.finalize(command, expected_qp_calls=expected)

    def after_step(self):
        self.transaction.commit(self.runtime.step_count, self.runtime.last)
        return self.native_machine.after_step()

    def governor_report(self):
        report=self.transaction.report()
        report['policy']=self.goal_policy
        return dict(**report, gravity_only_reference_evaluations=self.gravity_evaluations,
                    independent_reference_MjData_instances=1, live_state_written=False)
