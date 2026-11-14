"""Native NN goal confirmation followed by existing guarded unload/brake/stow.

Direct Finish is retained as evidence, never falsely completed. The alternative
uses the original native PUSH zero-command leg stop and measured four-foot
capture, with unchanged clearance, effort, goal/history and .18m displacement.
"""
class GoalThenGuardedStow:
    def __init__(self,native,session,issued,journal):
        self.native,self.session,self.issued,self.journal=native,session,issued,journal
        self.stow=None;self._result=None
    def __getattr__(self,name):return getattr(self.native,name)
    @property
    def phase(self):return self.stow.phase if self.stow is not None else self.native.phase
    def _goal_verified(self):
        import numpy as np
        p=self.native.r.sim
        return float(np.linalg.norm(p.data.xpos[p.box_id,:2]-p.box_push_target[0,:2].detach().cpu().numpy()))<.02
    def _begin(self):
        from mujoco_zyh.moving_push_exit import MovingPushExit
        from mujoco_zyh.resume_nav import NAV_ARM
        self.session.check_guards()
        if not self._goal_verified():raise RuntimeError('Native goal not verified before guarded stow')
        self.stow=MovingPushExit(self.native.r,list(self.session.last_two),compact_goal=NAV_ARM,
            hold_issued_arm=True,leg_stop_seed=self.issued.seed(),nn_handoff=True,nn_handoff_dwell_s=0.,
            retirement_reason='voluntary_early_exit')
        self.journal(dict(event='original_PUSH_goal_verified_guarded_stow_started',
            time_s=float(self.native.r.sim.data.time),original_direct_finish_retained=True,
            original_goal_rebased=False,direct_retraction_command_issued=False,model_input=False))
    def update(self):
        if self.stow is None:
            self.native.update()
            if self.native.finish is not None:self._begin()
        if self.stow is not None:self.stow.update()
    def next_command(self):return self.stow.command() if self.stow is not None else self.native.next_command()
    def after_step(self):
        if self.stow is not None:self.stow.after_step()
        else:self.native.after_step()
    @property
    def complete(self):
        if self.stow is None:return self.native.complete
        if not self.stow.complete:return False
        if not self._goal_verified():raise RuntimeError('Original PUSH goal lost during guarded stow')
        return True
    @property
    def results(self):
        if self.stow is None or not self.stow.complete:return self.native.results
        # Result readers also run during exception cleanup: never cache a
        # success if the original goal has since been lost.
        goal_verified=self._goal_verified()
        if self._result is None or self._result['successful'] != goal_verified:
            self._result=dict(skill='push',successful=goal_verified,finish=self.stow.report(),
                original_goal_verified=goal_verified,
                completion_definition='original goal verified + native guarded unload/stow complete',
                original_direct_finish_claimed_complete=False)
        return list(self.native.results)+[self._result]
