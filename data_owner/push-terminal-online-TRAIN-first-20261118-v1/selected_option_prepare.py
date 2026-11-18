"""Actual original resolver/option exercised on synthetic aliases; no world/Actor/lease."""
from pathlib import Path
from types import SimpleNamespace as NS
from dataclasses import replace
import hashlib
from selected_push_option import make_selected_push_option
import selected_push_option as adapter


def qualify_selected_option(freeze):
    from ainav.native import registered_bindings as orig, behavior_authority, session_factory

    def pin(module):
        p=Path(module.__file__).resolve(strict=True)
        digest=hashlib.sha256(p.read_bytes()).hexdigest()
        assert freeze['files'][str(p)]==digest
        return digest

    for module in (orig,behavior_authority,session_factory,adapter):pin(module)
    assert adapter.make_selected_push_option is make_selected_push_option
    query,goal='a'*64,'b'*64
    ref='CPU-fixture-only-target'; target=NS(target_ref=ref,association_evidence_ref='CPU-only-evidence')
    data,queue,model=object(),object(),object(); rt=NS(sim=NS(data=data,queue=queue,model=model)); entry='CPU-only-READY';op=adapter.make_selected_push_option(target_ref=ref,distance_m=.6,surface_height_m=0.,attempt_id='original-L0-single-PUSH',original_goal_sha256=goal,entry_receipt=entry)
    prior=NS(target_ref=ref,distance_m=.6,surface_height_m=0.,goal_sha256=goal,seal=('same',),approach_xy=(-.08,0.),view=object(),receipt={'fixture':True},history_owner=lambda:None,history_sha256=lambda:'c'*64)
    resolver=NS(_current=lambda:None,runtime=rt,_query_sha=query,api=NS(world_snapshot=lambda _:('fixture',)),_targets=(target,),_pushes={op.attempt_id:prior},_push_seal=lambda p:p.seal)
    def resolve(option):
     q=NS(query_sha256=query,data=data,queue=queue,model=model,world=('fixture',),targets=(target,),options=(option,))
     return orig.RegisteredBindingResolver.resolve(resolver,rt,option,q)
    def reject(option):
     try:resolve(option)
     except orig.NotAdmitted as e:assert str(e)=='not_admitted: exact prebound attempt/target/distance/goal/public parameters required'
     else:raise AssertionError('Original resolver unexpectedly accepted invalid public option')
    old=replace(op,parameters=(('goal_world_x_m',-.08),('goal_world_y_m',0.),*op.parameters));reject(old)
    for wrong in [replace(op,parameters=(('push_distance_m',.4),('surface_height_m',0.))),replace(op,original_push_goal_sha256='d'*64),replace(op,attempt_id='wrong')]:reject(wrong)
    new=resolve(op);assert new.mode=='selected_push' and new.approach_xy==prior.approach_xy and new.view is prior.view and new.history_owner is prior.history_owner and new.history_sha256 is prior.history_sha256
    return dict(CPU_fixture_only=True,original_movement_XY_rejected=True,wrong_distance_goal_attempt_rejected=True,
                only_public_push_parameters=dict(op.parameters),private_approach_view_and_history_preserved=True,
                original_goal_SHA_carried_unchanged=True,helper_sha256=pin(adapter))
