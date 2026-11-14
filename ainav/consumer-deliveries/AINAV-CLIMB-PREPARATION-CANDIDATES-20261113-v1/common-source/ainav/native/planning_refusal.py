"""Reject blocked stow references, then use original guarded protective exit.

Never suppress a measured collision/effort flag or mark a refused native Finish
successful. The failed owner and original goal/history are retained explicitly.
"""
from .executor import NativeOptionSession,world_snapshot


class RetractionReferenceRefused(RuntimeError):pass


class RefusalAwareMachine:
    def __init__(self,native,hard_flags,journal):self.native,self.hard_flags,self.journal=native,hard_flags,journal
    def __getattr__(self,name):return getattr(self.native,name)
    def update(self):
        try:return self.native.update()
        except RuntimeError as error:
            if not str(error).startswith('retraction_path_blocked:'):raise
            bad=[k for k,v in self.hard_flags().items() if k!='box_settled' and v]
            if bad:raise
            self.journal(dict(event='native_retraction_reference_refused_requires_protection',
                reason=str(error),native_finish_success=False,original_clearance_not_relaxed=True,
                measured_hard_flags=bad,model_input=False))
            raise RetractionReferenceRefused(str(error)) from error


class RefusalAwareSession(NativeOptionSession):
    def request_exit(self):
        if not (self.failure and self.failure.startswith('retraction_path_blocked:')):
            return super().request_exit()
        if self.exit is not None or self.make_exit is None:raise RuntimeError('Protective ownership unavailable')
        before=world_snapshot(self.runtime);self.sync()
        self.exit=self.make_exit(list(self.last_two))
        if world_snapshot(self.runtime)!=before:raise RuntimeError('Protective construction changed world/FIFO')


def install_refusal_exit(session):
    """Keep the exact deployed native class identity; bind only exit ownership."""
    from types import MethodType
    original=session.request_exit
    def request_exit(this):
        if not (this.failure and this.failure.startswith('retraction_path_blocked:')):
            return original()
        if this.exit is not None or this.make_exit is None:raise RuntimeError('Protective ownership unavailable')
        before=world_snapshot(this.runtime);this.sync()
        this.exit=this.make_exit(list(this.last_two))
        if world_snapshot(this.runtime)!=before:raise RuntimeError('Protective construction changed world/FIFO')
    session.request_exit=MethodType(request_exit,session)
    return session
