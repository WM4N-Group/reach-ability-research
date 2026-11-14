"""Executor-only actual NAV arrival witness, never a model/planner input."""
import numpy as np


class NativeNAVArrivalWitness:
    def __init__(self,runtime,nav,native_started,compact_goal):
        if nav is None or not hasattr(nav,'native'):raise ValueError('Actual native NAV owner required')
        self.r=runtime;self.nav=nav;self.started=float(native_started)
        self.data=runtime.sim.data;self.queue=runtime.sim.queue;self.observed_time=float(self.data.time)
        self.compact_goal=np.asarray(compact_goal,float).copy();self.checks={}
        self.original_goal=np.asarray(nav.native.goal).copy()
        self.validate(runtime)
        if (np.max(abs(runtime.last.position[12:]-self.compact_goal))>.002
            or np.max(abs(runtime.last.velocity[12:]))>.02):
            raise ValueError('Actually issued compact arm reference required, not a requested arm pose')
    def validate(self,runtime):
        if runtime is not self.r or runtime.sim.data is not self.data or runtime.sim.queue is not self.queue:
            raise ValueError('Native arrival witness belongs to another physical world/FIFO')
        if float(self.data.time)<self.observed_time-1e-7:raise ValueError('Native arrival clock regressed')
        if not np.array_equal(self.nav.native.goal,self.original_goal):raise ValueError('Original native NAV goal changed during capture')
        state=runtime.nav_state(self.started)
        self.checks=self.nav.native.stability_checks(state)
        if not self.nav.arrived or not self.checks or not all(self.checks.values()):
            raise RuntimeError('Actual native NAV goal/stability hold not passed or lost')
    def retain_goal(self,runtime):
        """During native braking/capture, retain actual position/yaw gates.

        Admission and FINAL acceptance still require ALL native checks. The
        original ResumeNav contract permits transient speed/arm-speed while its
        WBC lands feet, then re-verifies every native gate at completion.
        """
        if runtime is not self.r or runtime.sim.data is not self.data or runtime.sim.queue is not self.queue:
            raise ValueError('Native arrival witness belongs to another physical world/FIFO')
        if not np.array_equal(self.nav.native.goal,self.original_goal):raise ValueError('Original native NAV goal changed during capture')
        self.checks=self.nav.native.stability_checks(runtime.nav_state(self.started))
        if not self.checks.get('position') or not self.checks.get('yaw'):
            raise RuntimeError('Actual native NAV position/yaw gate lost during protected capture')

    def report(self):
        return dict(purpose='actual_native_NAV_arrival_compact_capture',actual_observed_time_s=self.observed_time,
            actual_native_checks=self.checks,original_NAV_goal_unchanged=True,failed_PUSH_front_is_not_arrival_target=True,
            actual_compact_reference=self.compact_goal.tolist(),private_executor_only=True)
