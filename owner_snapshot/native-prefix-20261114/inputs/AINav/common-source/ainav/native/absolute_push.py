"""Explicit public-goal to private actuator-parameter binding, NOT prediction.

Outer option remains the selected/audited option. The original factory receives
its native relative-distance constructor declaration, sealed before selection.
No actual pose, derived displacement or native target leaks into VLM payloads.
"""
from dataclasses import replace


class AbsolutePushFactory:
    def __init__(self, inner, mappings, journal):
        self.inner,self.mappings,self.journal=inner,mappings,journal
    def bind_query(self,query_sha,options):
        native=tuple(self.mappings.get(o.sha256,o) for o in options)
        self.inner.bind_query(query_sha,native)
    def __call__(self,option):
        native=self.mappings.get(option.sha256,option)
        session=self.inner(native)
        # Only a refused future reference (not an actual collision) can be
        # retired through the independently guarded native brake/stow path.
        from .planning_refusal import RefusalAwareMachine,install_refusal_exit,RetractionReferenceRefused
        if hasattr(session,'machine') and hasattr(session,'soft_failure'):
            view=session.machine.r.sim
            # Native selected sessions already expose their actual hard guard;
            # run it before accepting a planning-only refusal.
            def hard_flags():session.check_guards();return {}
            proxy=session.machine.r
            from mujoco_zyh.native_push_stop import IssuedPushObservation
            from .goal_stow import GoalThenGuardedStow
            from types import MethodType
            observed=IssuedPushObservation(view)
            session.machine=GoalThenGuardedStow(session.machine,session,observed,self.journal)
            original_after=session.after_step
            def after_issued(this):
                original_after()
                observed.after_actual_issuance(this.runtime.last)
            session.after_step=MethodType(after_issued,session)
            session.soft_failure=session.soft_failure+(RetractionReferenceRefused,)
            install_refusal_exit(session)
            def protected(refs):
                from mujoco_zyh.moving_push_exit import MovingPushExit
                from mujoco_zyh.resume_nav import NAV_ARM
                return MovingPushExit(proxy,refs,compact_goal=NAV_ARM,hold_issued_arm=True,
                                      retirement_reason='native_contact_progress_failure')
            session.make_exit=protected
        if native is not option:
            self.journal(dict(event='private_absolute_PUSH_constructor_binding',
                selected_public_option_sha256=option.sha256,native_constructor_option_sha256=native.sha256,
                original_push_goal_sha256=option.original_push_goal_sha256,
                actual_frozen_goal_preserved=True,model_input=False,private_displacement_not_published=True))
        return session
