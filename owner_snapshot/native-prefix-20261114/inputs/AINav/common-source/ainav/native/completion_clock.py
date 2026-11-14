"""Preserve native PUSH settled semantics at the actual 50Hz simulation clock.

Native termination is read by both the 50Hz Machine and 200Hz safety checks.
PushSettled.__call__ is stateful: EACH read increments duration by step_dt.
This adapter retains that exact native instance/predicate/threshold/history,
while allowing at most one advance per actually elapsed native control step.
All other hard termination predicates are still evaluated on every caller read.
No physics, actor, actuator command, target change, reset or success override.
"""
import hashlib
import inspect
import math


def scalar(value):
    return value.item() if hasattr(value,'item') else value


class ClockedNativeSettled:
    def __init__(self,native,env,*,journal=None):
        self.native=native;self.data=env.data;self.box=env.scene['box']
        self.interval=float(env.step_dt)
        if not callable(native) or abs(self.interval-.02)>1e-10:
            raise ValueError('Original 20ms native settled term required')
        self.signature=inspect.signature(native.__call__)
        hold=self.signature.parameters['hold_time'].default
        if hold!=.5:raise ValueError('Original native 0.5s hold threshold required')
        self.hold_time=float(hold)
        self.started=self.last_native_time=self.last_read_time=float(self.data.time)
        if not math.isfinite(self.started):raise ValueError('Actual finite simulation clock required')
        self.last_duration=float(scalar(native.duration));self.last_contact=bool(scalar(native.contact_seen))
        if self.last_duration!=0. or self.last_contact:
            raise ValueError('Attach clock only to a newly constructed native term; never reset a live term')
        self.native_source_sha256=hashlib.sha256(inspect.getsource(type(native).__call__).encode()).hexdigest()
        self.reads=0;self.advances=0;self.failed=False;self.journal=journal

    @property
    def duration(self):return self.native.duration
    @property
    def contact_seen(self):return self.native.contact_seen

    def reset(self,*args,**kwargs):
        raise RuntimeError('A clocked live PUSH completion term cannot be reset')

    def _consistent(self):
        if (float(scalar(self.native.duration))!=self.last_duration
                or bool(scalar(self.native.contact_seen))!=self.last_contact):
            raise RuntimeError('Native settled history advanced or changed outside its physical clock')

    def __call__(self,env,*args,**kwargs):
        if self.failed:raise RuntimeError('Failed native completion clock cannot be reused')
        try:
            bound=self.signature.bind(env,*args,**kwargs);bound.apply_defaults()
            if bound.arguments['hold_time']!=self.hold_time:
                raise ValueError('Native completion hold threshold must remain unchanged')
            if env.data is not self.data or env.scene['box'] is not self.box or float(env.step_dt)!=self.interval:
                raise ValueError('Clocked native completion must read the same actual selected world/object')
            now=float(self.data.time)
            if not math.isfinite(now) or now<self.last_read_time-1e-9:
                raise RuntimeError('Actual native completion clock moved backwards')
            self._consistent();self.reads+=1;self.last_read_time=now
            age=now-self.last_native_time
            if age>self.interval+1e-7:
                raise RuntimeError('Missing actual native completion samples; never fill an unobserved hold')
            if age>=self.interval-1e-7:
                # This is the only stateful call. Actor/history/goal are untouched.
                self.native(env,*args,**kwargs)
                self.advances+=1;self.last_native_time=now
                self.last_duration=float(scalar(self.native.duration));self.last_contact=bool(scalar(self.native.contact_seen))
                if not math.isfinite(self.last_duration) or self.last_duration<0 or self.last_duration>now-self.started+2e-6:
                    raise RuntimeError('Native settled dwell exceeds actually elapsed simulation time')
                if self.journal is not None:
                    self.journal(dict(event='native_PUSH_settled_actual_clock_sample',time_s=now,
                        native_duration_s=self.last_duration,native_contact_seen=self.last_contact,
                        native_result=bool(scalar(self.native.duration>=self.hold_time)),
                        original_hold_time_s=self.hold_time,actual_20ms_advances=self.advances,
                        native_predicate_sha256=self.native_source_sha256,model_input=False))
            # A repeated read is a fresh boolean comparison, never another dwell
            # increment. This has the same return type/threshold as PushSettled.
            return self.native.duration>=self.hold_time
        except Exception:
            self.failed=True
            raise

    def report(self):
        self._consistent()
        return dict(schema='ainav-native-settled-physical-clock-v1',original_hold_time_s=self.hold_time,
            original_step_dt_s=self.interval,actual_started_s=self.started,
            actual_last_native_sample_s=self.last_native_time,actual_last_read_s=self.last_read_time,
            caller_reads=self.reads,native_advances=self.advances,native_duration_s=self.last_duration,
            native_contact_seen=self.last_contact,native_result=bool(scalar(self.native.duration>=self.hold_time)),
            failed=self.failed,native_predicate_sha256=self.native_source_sha256,
            native_term_class_preserved=type(self.native).__name__,native_buffers_never_reset=True,
            native_goal_actor_and_motor_queue_not_modified=True,model_input=False)
