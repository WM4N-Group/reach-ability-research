"""Strict future D3 source derivation only. No IO, dispatch or mutable old SDK.

Original base manifest remains byte-exact, explicitly a BASE manifest. The NEW
verifier admits precisely ONE named/hashed predicate delta, never arbitrary files.
"""
import ast
import hashlib

OLD_PREDICATE='399aada0ee3b79af11014a22d8ba6f942e2df90f4658aa959139fc941bb59ed5'
NEW_PREDICATE='a15634610b69c0d01b68d6c61bcced9f74d60c5ffc98ffb45de9d54745ba28af'
VERIFIER_SHA='689be5c169265f87ec324d11908b331d5830f9409c73b153298418be4627ebd1'
CONTEXT_SHA='d29c270671e8c5c71b41af05769a9493cb0dc3a2d51d7b2d1d95c7ad5222a033'


def _pin(raw, expected):
    if type(raw)is not bytes or hashlib.sha256(raw).hexdigest()!=expected:
        raise ValueError('Exact original selected source required')
    return raw.decode('utf-8')


def derive_bundle_verifier(raw, *, original_source_sha256, enabled=False):
    if type(enabled)is not bool:raise ValueError('Explicit new-program source revision')
    if not enabled:return raw
    if original_source_sha256 != VERIFIER_SHA:raise ValueError('Only canonical original strict bundle verifier')
    text=_pin(raw,VERIFIER_SHA)
    site='    checksums = parse_checksums(data.decode())\n    for name, expected in checksums.items():'
    if text.count(site)!=1:raise ValueError('One exact original strict verifier loop')
    new='''    checksums = parse_checksums(data.decode())
    require(checksums.get('push/controller/box_push.py') == 'OLD', 'Exact original base predicate SHA in published BASE manifest')
    checksums = dict(checksums)
    checksums['push/controller/box_push.py'] = 'NEW'
    for name, expected in checksums.items():'''.replace('OLD',OLD_PREDICATE).replace('NEW',NEW_PREDICATE)
    text=text.replace(site,new,1)
    before='        original_source_or_weights_modified=False, formal_skill_acceptance=False)'
    after="        original_source_or_weights_modified=True, original_actor_weights_modified=False,\n        D3_single_predicate_delta={'push/controller/box_push.py': '"+NEW_PREDICATE+"'},\n        base_manifest_not_a_claim_of_unmodified_published_bundle=True, formal_skill_acceptance=False)"
    if text.count(before)!=1:raise ValueError('One exact original truthful provenance return')
    text=text.replace(before,after,1)
    if text.replace(new,site,1).replace(after,before,1)!=raw.decode('utf-8'):
        raise ValueError('Only explicit checksum override and truthful provenance changed')
    ast.parse(text)
    return text.encode()


def derive_selected_context(raw, *, enabled=False):
    if type(enabled)is not bool:raise ValueError('Explicit new-program context source revision')
    if not enabled:return raw
    text=_pin(raw,CONTEXT_SHA)
    site='    view.refresh()\n    return view,dict('
    if text.count(site)!=1:raise ValueError('One original fresh selected-view return boundary')
    new='''    view.refresh()
    _data_d3_bind = getattr(runtime, '_data_d3_bind_selected_view', None)
    if not callable(_data_d3_bind):
        raise RuntimeError('D3 selected view needs its registered owner sink before termination')
    try:
        _data_d3_bind(view)
    except BaseException:
        raise RuntimeError('D3 sink binding failed; no retry or silent BLOCKED fallback') from None
    return view,dict('''
    text=text.replace(site,new,1)
    if text.replace(new,site,1)!=raw.decode('utf-8'):raise ValueError('Only one pre-return selected-view sink binding site changed')
    ast.parse(text)
    return text.encode()
