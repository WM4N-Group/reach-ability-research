"""Actual shared original SkillIntent catalogue for V4 A/B/C/D/E.

Only declared public geometry/targets, never a native permission, current object
pose, private body ID, correct route or learned successor probability/cost.
"""
from copy import deepcopy
import math
from v4_native_asset import validate,require

def declarations(scene):
    validate(scene);deck=scene['platforms'][0];bounds=deck['bounds_xy_m'];ground=[]
    def add(xy):
        xy=tuple(round(float(v),12)for v in xy);require(all(math.isfinite(v)for v in xy),'Finite declaration')
        # The deck occupies this region: never advertise a ground terminal/NAV
        # underneath it as an elevated-goal substitute. Boundary is blocked too.
        if bounds[0]<=xy[0]<=bounds[1]and bounds[2]<=xy[1]<=bounds[3]:return
        if xy not in ground:ground.append(xy)
    for xy in scene['public_waypoints_xy_m']:add(xy)
    for obj in scene['objects']:
        for x in [obj['initial_xy_m'][0],*obj['allowed_placement_x_m']]:add((x-obj['size_m'][0]/2-.58,obj['initial_xy_m'][1]))
    rows=[dict(skill='NAV',target_ref='v4-ground-nav-%03d'%i,parameters=dict(goal_world_x_m=xy[0],goal_world_y_m=xy[1],surface_height_m=0.))for i,xy in enumerate(ground)]
    for obj in scene['objects']:
        for x in obj['allowed_placement_x_m']:
            rows.append(dict(skill='PUSH',target_ref=obj['public_ref'],parameters=dict(goal_world_x_m=x,goal_world_y_m=obj['initial_xy_m'][1],surface_height_m=0.)))
    for obj in scene['objects']:
        rows.append(dict(skill='CLIMB',target_ref=obj['public_ref']+':upper-entry',parameters=dict(surface_height_m=obj['size_m'][2])))
    rows.append(dict(skill='CLIMB',target_ref=deck['name'],parameters=dict(surface_height_m=deck['top_z_m'])))
    g=scene['task']['goal_bounds_xy_m'];rows.append(dict(skill='NAV',target_ref='v4-goal-elevated',parameters=dict(goal_world_x_m=(g[0]+g[1])/2,goal_world_y_m=(g[2]+g[3])/2,surface_height_m=deck['top_z_m'])))
    require(len(rows)<=128 and len({(r['skill'],r['target_ref'],tuple(sorted(r['parameters'].items())))for r in rows})==len(rows),'Bounded distinct same shared public domain')
    return tuple(rows)

def declared_map(scene):
    rows=declarations(scene);objects={o['public_ref']:o for o in scene['objects']};anchors=[];seen=set()
    def add(ref,xyz,description):
        if ref in seen:return
        seen.add(ref);anchors.append(dict(target_ref=ref,position_xyz_m=list(xyz),uncertainty_xyz_m=[0.,0.,0.],description=description))
    for o in scene['objects']:add(o['public_ref'],[*o['initial_xy_m'],0.],'Declared INITIAL task blueprint only, never live box pose/association or native permission')
    for r in rows:
        p=r['parameters'];ref=r['target_ref']
        if r['skill']=='NAV':add(ref,[p['goal_world_x_m'],p['goal_world_y_m'],p['surface_height_m']],'Declared same-support NAV reference, not a measured current robot pose')
        elif r['skill']=='CLIMB':
            if ref.endswith(':upper-entry'):
                o=objects[ref.removesuffix(':upper-entry')];xy=o['required_goal_xy_m']
            else:
                b=scene['platforms'][0]['bounds_xy_m'];xy=((b[0]+b[1])/2,(b[2]+b[3])/2)
            add(ref,[*xy,p['surface_height_m']],'Declared destination surface after required placement only; current binding/support/20cm rise still unqualified')
    return dict(source_ref='V4 same-five-arm PUBLIC declaration catalogue; not private actual geometry',anchors=anchors)

def capability_contract():
    from ainav.contracts import canonical
    return canonical(dict(source_ref='V4 five-arm common semantic intents, not native admission',skills=['NAV','PUSH','CLIMB'],constraints=[
        'Choose tasks/objects/skills from the same public catalogue. These are semantic intents, NOT native motor permission.',
        'Declared initial/required placement geometry is not live pose. Current original RGBD association and actual receipts remain mandatory.',
        'All PUSH actions originate on ground, +world X, immutable absolute goal; original entry/NN/placement/STOW_VERIFIED gates remain.',
        'NAV stays on the actual current support layer; a declared elevated NAV cannot replace CLIMB or certify success at ground XY.',
        'CLIMB surface_height_m is the public DESTINATION height. Source support and original20cm rise/current binding must be established privately by the original judge.',
        'Current static goal_deck CLIMB binding and the V4 .2-to-.6 rise are NOT qualified by this catalogue. Unsupported prerequisites mean UNKNOWN/rejection, never success.',
        'Three original placements, actual CLIMB receipts, same-world owners and a four-foot goal_deck supported stop are required for complete task success.',
        'No VLM/WM/optimizer/rule may consume private force/pose, future trajectory or an isolated existence route.']))

def intent_catalogue(scene,observation,*,sequence):
    from ainav.intents import SkillIntent
    from ainav.contracts import Observation
    require(type(observation)is Observation and observation.value['declared_map']==declared_map(scene),'Original public observation with this exact same-five-arm declared map')
    require(type(sequence)is int and sequence>=0,'Actual original public acquisition sequence required')
    rows=declarations(scene);return tuple(SkillIntent('v4-intent-%d-%d'%(sequence,i),r['skill'],r['target_ref'],tuple(sorted(r['parameters'].items())))for i,r in enumerate(rows))

def public_effects(scene):
    """Source facts for Reach's own estimator. No costs, private starts or GT.

    All CLIMB fields keep destination-vs-source explicit; this is not a list of
    READY actions. We do not supply padded target8/public60 or invent WM IO.
    """
    effects=[]
    for r in declarations(scene):
        skill=r['skill'];p=r['parameters'];item=dict(deepcopy(r),actual_native_admission=False,actual_exit_pose=None,complete_successor_cost_s=None,success_probability=None)
        if skill=='NAV':item.update(declared_effect='same-support NAV reference only',source_height_m='CURRENT_VERIFIED_SUPPORT_REQUIRED',destination_height_m=p['surface_height_m'],requires_actual_arrival_and_stow=True)
        elif skill=='PUSH':item.update(declared_effect='selected immutable placement goal only',source_height_m=0.,requires_actual_placement_and_STOW_VERIFIED=True,relative_action11_distance=None,relative_distance_missing_reason='Absolute goal minus private/initial pose is not a causal public relative command')
        else:item.update(declared_effect='requested destination support only',source_height_m='CURRENT_VERIFIED_SUPPORT_REQUIRED',destination_height_m=p['surface_height_m'],selected_original_rise_m=.2,static_goal_deck_binding_qualified=False,complete_transition_qualified=False)
        effects.append(item)
    return dict(role='PUBLIC_SOURCE_CAPABILITY_AND_REQUESTED_EFFECTS_NOT_COST_PROVIDER_OR_NATIVE_ADMISSION',effects=effects,preparation_exit_variants=dict(status='NOT_YET_EXPORTED_OR_NATIVE_QUALIFIED',variants=[],missing_means_UNKNOWN_not_zero_or_no_cost=True),private_state_or_route_or_evaluation_outcomes=False,WM_public60_target8_issued_history_not_fabricated=True,source_native_qualified=False)
