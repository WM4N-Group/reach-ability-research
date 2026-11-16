"""Opt-in same-WM-anchor semantic HYPOTHESES for the NEW common palette only.

No native body lookup, live pose, old query aliases, image classifier/API, mass
or route truth. A published scene-specific colour prior is NOT an object-ID
certificate. Original same-family/depth/plane gates remain unchanged downstream.
This is not qualified on the old brown asset or a completed WM integration.
"""
import colorsys
import copy
import hashlib
import json
import math
from .v4_anchor_target8 import load_original_geometry
from .v4_successor_choice import need

ROLE = 'SHARED_DECLARED_APPEARANCE_HYPOTHESIS_NOT_NATIVE_IDENTITY'
SCENE_SHA = '6394740eb54b99ec0e0b4b35b0f804e7875dfc29255d9f897ba57b1ac0b48d20'
PUBLIC_GEOMS = dict(cuboid_a='complex_box_a_geom',cuboid_b='complex_box_b_geom',cuboid_c='complex_box_c_geom')
APPEARANCE_FILE_SHA = '75842a43ee8313edf95e8d92bbc6dc5b22d5f18474c316fa7c5f92a67e895457'
APPEARANCE_VALUE_SHA = '5b9bcacda809969cce749c8727515bb0463e7121b20bdc9acc1f1a60e4e5fa89'
FAMILIES = (('warm',.035,.16),('green',.28,.50),('violet',.70,.90),('red',.95,.035))


def _sha(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def declared_subjects(public_map, public_effects):
    """Derive declaration relations, NEVER current positions/arrival/success.

    Only registered box approach refs (original L/2+.58 arithmetic), box-top
    refs and explicit box intents get a subject. A generic waypoint is NOT a
    plane. Ambiguous coincident declarations remain unresolved.
    """
    anchors={a['target_ref']:a for a in public_map['anchors']}
    need(len(anchors)==len(public_map['anchors'])and set(PUBLIC_GEOMS)<=set(anchors),
         'Distinct common declaration anchors including the three public boxes')
    need(public_effects['role']=='PUBLIC_SOURCE_CAPABILITY_AND_REQUESTED_EFFECTS_NOT_COST_PROVIDER_OR_NATIVE_ADMISSION'and
         public_effects['private_state_or_route_or_evaluation_outcomes']is False, 'Only PUBLIC declared effects, not private/current pose or outcome records')
    rows=public_effects['effects']
    need(1<=len(rows)<=128 and 1<=len(anchors)<=128, 'Bounded shared public declaration domain')
    xy=lambda x,y:(round(float(x),12),round(float(y),12))
    placements={ref:{tuple(anchors[ref]['position_xyz_m'][:2])}for ref in PUBLIC_GEOMS}
    for row in rows:
        if row['skill']=='PUSH'and row['target_ref']in placements:
            p=row['parameters'];placements[row['target_ref']].add((p['goal_world_x_m'],p['goal_world_y_m']))
    result={}
    for row in rows:
        skill,ref,p=row['skill'],row['target_ref'],row['parameters'];subjects=set()
        if skill=='PUSH'and ref in PUBLIC_GEOMS:subjects.add(ref)
        elif skill=='CLIMB'and ref.endswith(':upper-entry')and ref[:-12]in PUBLIC_GEOMS:subjects.add(ref[:-12])
        elif skill=='NAV':
            goal=xy(p['goal_world_x_m'],p['goal_world_y_m']);height=p['surface_height_m']
            for subject,positions in placements.items():
                if height==0. and any(goal==xy(x-2.4/2-.58,y)for x,y in positions):subjects.add(subject)
                if height==.2 and any(goal==xy(x,y)for x,y in positions):subjects.add(subject)
        result[(skill,ref,_sha(p))]=next(iter(subjects))if len(subjects)==1 else None
    return result


class DeclaredPaletteAnchorAssociation:
    def __init__(self, *, public_appearance, public_map, public_effects, journal,
                 enabled=False, active_revision_id=None, selected_MJB_sha256=None,
                 selected_asset_evidence=None, geometry_source_root=None, software_fixture=False, fixture_api=None):
        need(type(enabled)is bool and type(software_fixture)is bool and callable(journal), 'Explicit opt-in/provenance/journal')
        need(fixture_api is None or software_fixture, 'Fixture proposals cannot become a live semantic producer')
        self.enabled,self.software_fixture=enabled,software_fixture
        self.appearance=copy.deepcopy(public_appearance);self.map=copy.deepcopy(public_map)
        self.effects=copy.deepcopy(public_effects);self.journal=journal;self.last_evidence_ref=None
        self.api=fixture_api;self.geometry_source_root=geometry_source_root
        self.active_revision_id,self.selected_MJB_sha256=active_revision_id,selected_MJB_sha256
        self.subjects=declared_subjects(self.map,self.effects)
        a=self.appearance
        need(_sha(a)==APPEARANCE_VALUE_SHA, 'Exact published new common appearance prior, not an arbitrary colour identity table')
        self.asset_evidence_sha256=None
        need(a['schema']=='AINav-V4-common-visible-appearance-revision-v1'and a['scene_sha256']==SCENE_SHA and
             a['shared_arms']==list('ABCDE')and a['no_geometry_mass_friction_contact_robot_Actor_camera_goal_or_detector_change']is True,
             'Explicit five-arm common NEW render contract, not a private instance-colour observation')
        self.family={}
        for ref,geom in PUBLIC_GEOMS.items():
            color=a['body_geom_review_hex'][geom]
            need(type(color)is str and len(color)==7 and color[0]=='#','Exact public review hex declaration')
            hue=colorsys.rgb_to_hsv(*(int(color[i:i+2],16)/255 for i in (1,3,5)))[0]
            names=[name for name,lo,hi in FAMILIES if (lo<=hue<hi if lo<hi else hue>=lo or hue<hi)]
            need(len(names)==1,'Nominal public colour must have one ORIGINAL hue family')
            self.family[ref]=names[0]
        need(len(set(self.family.values()))==3,'This prior requires distinct declared families; no old all-brown inference')
        if enabled:
            need('SHARED_PUBLIC_APPEARANCE_PRIOR:'+APPEARANCE_FILE_SHA in self.map['source_ref'],
                 'Same prior must be exposed in the common PUBLIC observation for ALL five arms')
            anchors={x['target_ref']:x for x in self.map['anchors']}
            for subject,geom in PUBLIC_GEOMS.items():
                need('SHARED_REVIEW_RGB='+a['body_geom_review_hex'][geom] in anchors[subject]['description'],
                     'No A/B-exclusive hidden colour-to-name prior')
            for (skill,ref,_),subject in self.subjects.items():
                if skill=='NAV'and subject is not None:
                    need('WM_CONDITIONING_SUBJECT='+subject in anchors[ref]['description'],
                         'Declared NAV subject relation must be common public information, not a hidden route')
            need(active_revision_id==a['revision_id']and type(selected_MJB_sha256)is str and
                 len(selected_MJB_sha256)==64 and all(c in '0123456789abcdef'for c in selected_MJB_sha256)and
                 selected_MJB_sha256!=a['reference_static_MJB_sha256'],
                 'Explicit NEW selected-asset binding required; never apply new palette to old brown asset')
            e=selected_asset_evidence
            need(type(e)is dict and e.get('revision_id')==active_revision_id and
                 e.get('contract_sha256')==APPEARANCE_FILE_SHA and
                 e.get('new_static_MJB_sha256')==selected_MJB_sha256 and
                 e.get('reference_static_MJB_sha256')==a['reference_static_MJB_sha256']and
                 e.get('all_five_same_new_asset_required')is True,
                 'Source compiled-asset evidence must bind the exact common prior/model, not a hand-labelled hash')
            proof=e.get('compiled_render_only_delta_proof',{})
            need(proof.get('only_changed_array')=='geom_rgba'and
                 set(proof.get('only_changed_rows',{}))==set(PUBLIC_GEOMS.values())and
                 len(set(proof['only_changed_rows'].values()))==3 and
                 proof.get('engine_options_unchanged')is True and
                 proof.get('topology_names_paths_unchanged')is True and
                 type(proof.get('unchanged_nonRGBA_array_count'))is int and
                 proof['unchanged_nonRGBA_array_count']>0 and
                 type(proof.get('unchanged_nonRGBA_arrays_sha256'))is dict and
                 len(proof['unchanged_nonRGBA_arrays_sha256'])==proof['unchanged_nonRGBA_array_count']and
                 all(type(x)is str and len(x)==64 and all(c in '0123456789abcdef'for c in x)
                     for x in proof['unchanged_nonRGBA_arrays_sha256'].values()),
                 'Exact render-only source proof; this producer cannot certify native model/render itself')
            self.asset_evidence_sha256=_sha(e)

    def __call__(self, observation, options, anchor):
        need(self.enabled,'Declared palette association is default OFF, not an adopted runtime policy')
        need(observation.value['declared_map']==self.map,'Same current common public declaration, never a stale/private map')
        need(-1e-7<=observation.time_s-anchor['time_s']<=.100001, 'Current original WM anchor clock, not a future/stale semantic hypothesis')
        need(tuple(anchor['rgb'].shape)==(64,96,3)and tuple(anchor['depth_m'].shape)==(64,96)and
             type(anchor['time_s'])in(int,float)and math.isfinite(anchor['time_s']), 'Actual original WM anchor only')
        if self.api is None:self.api=load_original_geometry(self.geometry_source_root)
        rgb_sha=hashlib.sha256(anchor['rgb'].tobytes()).hexdigest()
        calibration=self.api.visual_calibration_sha(anchor['camera_K'],anchor['T_base_optical'])
        inventory=self.api.propose_visual_candidates(anchor['rgb'],anchor['depth_m'],anchor['camera_K'],anchor['T_base_optical'])
        need(inventory['schema']=='pixel-only-appearance-proposals-v1'and inventory['RGB_sha256']==rgb_sha and
             inventory['calibration_sha256']==calibration,'Original current-anchor proposal identity')
        candidates=inventory['candidates'];keys=[o.sha256 for o in options]
        need(len(set(keys))==len(keys),'Unique exact current candidate domain')
        selected={};reasons={};subjects={}
        for option in options:
            subject=self.subjects.get((option.skill,option.target_ref,_sha(dict(option.parameters))))
            selected[option.sha256]=None;subjects[option.sha256]=subject
            if subject is None:
                reasons[option.sha256]='NO_UNIQUE_DECLARED_BOX_SUBJECT_NOT_WAYPOINT_AS_PLANE';continue
            # Count ALL siblings, including ones with unusable depth, just as
            # original single_visible_hypothesis. Never keep only the largest.
            matches=[p for p in candidates if p['appearance_family']==self.family[subject]]
            if len(matches)!=1 or matches[0]['geometry_valid']is not True:
                reasons[option.sha256]='MISSING_AMBIGUOUS_OR_DEPTH_INVALID_CURRENT_FAMILY';continue
            selected[option.sha256]=dict(frame_local_ref=matches[0]['frame_local_ref'],declared_standoff_m=.58)
            reasons[option.sha256]='SCENE_SPECIFIC_PUBLIC_RENDER_PRIOR_HYPOTHESIS_ONLY'
        ref=self.journal(dict(event='reach_v4_same_anchor_declared_palette_hypotheses',role=ROLE,
            software_fixture=self.software_fixture,WM_anchor_RGB_bytes_sha256=rgb_sha,WM_anchor_time_s=anchor['time_s'],
            WM_anchor_calibration_sha256=calibration,public_prior_sha256=_sha(self.appearance),
            public_map_sha256=_sha(self.map),public_effects_sha256=_sha(self.effects),
            selected_public_revision_id=self.active_revision_id,selected_MJB_sha256=self.selected_MJB_sha256,
            source_compiled_asset_evidence_sha256=self.asset_evidence_sha256,
            subjects_by_option_sha256=subjects,reasons_by_option_sha256=reasons,
            native_identity_or_pose_or_admission_claimed=False,WM_forward_or_physics_calls=0))
        need(type(ref)is str and bool(ref),'Durable original public-prior semantic hypothesis evidence')
        self.last_evidence_ref=ref
        return dict(WM_anchor_RGB_bytes_sha256=rgb_sha,WM_anchor_time_s=anchor['time_s'],
            WM_anchor_calibration_sha256=calibration,frame_local_ref_by_option_sha256=selected,association_evidence_ref=ref,
            association_scope=ROLE,declared_subject_by_option_sha256=subjects)
