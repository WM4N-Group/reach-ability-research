"""Consume one launcher ticket before ANY Isaac import. Idempotent only in PID.

The SDK checker executes actual probe definitions in this SAME process, so its
second guard call is allowed; another process may never reuse the admission.
"""
import os,sys
from pathlib import Path
from release_authority import approval,context,exclusive,family_snapshot,load,pid_start_ticks,phase_directory,sdk_gate,sha
_ADMITTED=None


def require_execution_authority():
    global _ADMITTED
    root=Path(__file__).resolve().parent.parent
    if 'REACH_POSE_PERMIT' not in os.environ:raise PermissionError('No launcher ticket: no App may start')
    ticket_path=Path(os.environ['REACH_POSE_PERMIT']).resolve()
    if ticket_path.parent!=root/'permits':raise PermissionError('Ticket outside this release')
    ticket=load(ticket_path);mode=ticket['mode'];a,p=approval(root,mode);family_snapshot(p)
    if mode not in ('sdk','physical') or ticket['release_root']!=str(root) or ticket['allocation_id']!=p['allocation_id']:
        raise PermissionError('Wrong ticket mode/root/allocation')
    if ticket['source_manifest_sha256']!=sha(root/'source/manifest.json') or ticket['approval_sha256']!=sha(root/'approval.json'):
        raise PermissionError('Ticket source or approval changed')
    if os.environ.get('REACH_POSE_NONCE')!=ticket['nonce'] or Path(sys.argv[0]).resolve()!=root/'source'/ticket['script'] or sys.argv[1:]!=ticket['argv']:
        raise PermissionError('Ticket does not bind this script/command/nonce')
    claim_path=Path(ticket['claim_path'])
    expected=phase_directory(p)/'sdk.claim.json' if mode=='sdk' else phase_directory(p)/'physical_claims'/(ticket['item']['output_name']+'.json')
    if claim_path!=expected:raise PermissionError('Claim outside registered phase')
    claim=load(claim_path)
    if any(claim[k]!=ticket[k] for k in ['mode','release_root','nonce','source_manifest_sha256','approval_sha256','item','supervisor_pid','supervisor_start_ticks']):raise PermissionError('Claim/ticket mismatch')
    if not Path('/proc',str(ticket['supervisor_pid'])).exists() or pid_start_ticks(ticket['supervisor_pid'])!=ticket['supervisor_start_ticks']:raise PermissionError('Original supervisor no longer exists or PID reused')
    if mode=='physical':sdk_gate(root)
    identity=(os.getpid(),str(ticket_path),ticket['nonce'])
    if _ADMITTED==identity:return ticket
    admitted_dir=claim_path.parent/'admissions';admitted_dir.mkdir(exist_ok=True)
    admitted=admitted_dir/claim_path.name
    exclusive(admitted,dict(pid=os.getpid(),ticket=str(ticket_path),nonce=ticket['nonce'],mode=mode))
    _ADMITTED=identity
    return ticket
