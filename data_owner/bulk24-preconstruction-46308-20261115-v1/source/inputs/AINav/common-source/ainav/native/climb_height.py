"""Measured COM-offset compensation for the original ClimbEntry base-height goal.

A compact-arm PUSH exit changes the COM-to-base offset when ClimbEntry folds
its arm to native zero. A one-shot COM reference otherwise leaves base height
biased. Only the QP COM-z reference tracks that measured offset, at <=.02m/s.
Original height target, tolerance, dwell, timeout, support and safety gates stay
unchanged. No live-state/force/queue writes, actor changes or successor actions.
"""
import math


def height_reference_step(previous, base_goal, measured_base_z, measured_com_z, dt):
    values=(previous,base_goal,measured_base_z,measured_com_z,dt)
    if not all(math.isfinite(float(v)) for v in values) or not 0 <= dt <= .020001:
        raise ValueError('Finite measured height and original <=20ms clock required')
    target=base_goal+measured_com_z-measured_base_z
    return previous+max(-.02*dt,min(.02*dt,target-previous))


class MeasuredClimbHeightMachine:
    def __init__(self,native,journal):
        self.native_machine,self.journal=native,journal
        self.owner=None;self.last_time=None

    def __getattr__(self,name):return getattr(self.native_machine,name)

    def next_command(self):
        native=self.native_machine
        if native.phase=='prepare' and native.kind=='climb':
            entry=native.preparation;p=native.r.sim;now=float(p.data.time)
            if self.owner is None:
                self.owner=entry;self.last_time=now
                self.journal(dict(event='native_CLIMB_measured_COM_height_reference_started',
                    time_s=now,original_base_height_goal_m=float(entry.base_goal),
                    original_tolerance_m=float(entry.config.height_tolerance),
                    original_timeout_s=float(entry.config.timeout),
                    reference_slew_m_s=.02,model_input=False,live_state_written=False))
            if self.owner is not entry:raise RuntimeError('CLIMB preparation owner replaced')
            entry.com_goal[2]=height_reference_step(float(entry.com_goal[2]),float(entry.base_goal),
                float(p.data.qpos[2]),float(p.data.subtree_com[p.base_id,2]),now-self.last_time)
            self.last_time=now
        return native.next_command()
