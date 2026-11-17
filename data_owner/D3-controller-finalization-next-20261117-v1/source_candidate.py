"""Future-only launcher metadata finalization fix. No dispatch/IO/source writes.
Does not fix the independent >2s resource observation failure or qualify retry.
"""
import hashlib
ORIGINAL_SHA='f248f1bf1e1ceaba1d786a73c2b6c64e83a33b1d0a3fdfca1644a170a855bc7d'
OLD="    write_json(budget,L/'result-CAS-proof.json',cas(finish));budget.begin_finalization()"
NEW="    closure_proof=cas(finish)\n    budget.begin_finalization()  # Preserve failure latch; permit bounded final reports.\n    write_json(budget,L/'result-CAS-proof.json',closure_proof)"

def derive(source, *, enabled=False):
    if type(enabled)is not bool or type(source)is not bytes:raise ValueError('Explicit bounded new-source revision')
    if not enabled:return source
    if hashlib.sha256(source).hexdigest()!=ORIGINAL_SHA:raise ValueError('Exact failed frozen controller source only')
    text=source.decode()
    if text.count(OLD)!=1:raise ValueError('One exact finalization order site')
    changed=text.replace(OLD,NEW,1)
    if changed.replace(NEW,OLD,1)!=text:raise ValueError('Only one finalization order change')
    compile(changed,'<future-controller-finalization-only>','exec')
    return changed.encode()
