"""Declarative transfer scene and private physical witnesses, not a task router.

The public task contains only a goal and anonymous geometry. There are no
NAV/PUSH/CLIMB sequences, object-role labels or controller reference points.
Box prototypes are copied from the actual original full-4 compiled model.
"""
from copy import deepcopy
import hashlib
import json
import math


def sha(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def make_scene(prototypes):
    scene=dict(schema='ainav-transfer-geometry-v1',case_id='bridge-first-five-boxes-v1',
        box_prototypes=deepcopy(prototypes),
        surfaces=[
            dict(id='s17',bounds_xy_m=[-1.60,7.40,-5.10,2.90],top_z_m=0.,bottom_z_m=-.8),
            dict(id='s04',bounds_xy_m=[7.75,13.55,-5.10,2.90],top_z_m=.2,bottom_z_m=-.8),
            dict(id='s29',bounds_xy_m=[13.55,17.85,-5.10,2.90],top_z_m=.6,bottom_z_m=-.8)],
        # Declaration order is deliberately unrelated to location or function.
        objects=[
            dict(id='o43',prototype='p1',center_xy_m=[10.84,1.25],support='s04'),
            dict(id='o08',prototype='p2',center_xy_m=[5.48,-1.15],support='s17'),
            dict(id='o61',prototype='p0',center_xy_m=[3.05,-3.40],support='s17'),
            dict(id='o25',prototype='p1',center_xy_m=[11.72,-1.35],support='s04'),
            dict(id='o37',prototype='p2',center_xy_m=[4.98,1.20],support='s17')],
        initial_robot=dict(xy_m=[-.55,-.90],yaw_rad=0.,support='s17'),
        goal=dict(bounds_xy_m=[16.15,16.95,-1.35,-.45],surface='s29',
            instruction='Reach the marked goal region. Stop safely with all four feet supported there.'),
        physical_environment=dict(floor_top_z_m=-.8,static_friction=.7,gravity_m_s2=[0.,0.,-9.81]),
        private_acceptance=dict(model_input=False,departure='s17',landing='s04',upper='s29',
            dock_tolerance_m=.01,foot_load_gt_N=3.,foot_z_tolerance_m=.04,
            foot_center_radius_m=.022,loaded_dwell_s=.1,final_dwell_s=.5,
            max_linear_speed_m_s=.03,max_angular_speed_rad_s=.12,max_tilt_rad=.03,
            crossing_base_clearance_above_bridge_m=.05,
            required_physical_order=['loaded_gap_spanning_object','gap_crossed','upper_goal_loaded_stop'],
            fixed_skill_sequence=None,required_object_ids=None),
        scope=dict(training_allowed=False,automatic_retry=False,reset_after_initial_allowed=False,
            current_baseline_compatible=None,physical_task_passed=False,
            original_required_failure_prefix=False,
            new_case_is_not_a_claim_that_original_full4_passed=True))
    validate_scene(scene)
    return scene


def object_geometry(scene,item):
    p=scene['box_prototypes']['prototypes'][item['prototype']]
    support=next(s for s in scene['surfaces'] if s['id']==item['support'])
    return dict(id=item['id'],size_m=list(p['size_m']),
        initial_center_xyz_m=[*item['center_xy_m'],support['top_z_m']+p['size_m'][2]/2],
        initial_support_height_m=support['top_z_m'])


def validate_scene(scene):
    if scene['schema']!='ainav-transfer-geometry-v1':raise ValueError('Unsupported geometry schema')
    surfaces={s['id']:s for s in scene['surfaces']};objects=scene['objects']
    if len(surfaces)!=len(scene['surfaces']) or len({o['id'] for o in objects})!=len(objects):
        raise ValueError('Unique anonymous entities required')
    if len(objects)<=3:raise ValueError('Transfer must change original three-box count')
    if scene['scope']['automatic_retry'] or scene['scope']['reset_after_initial_allowed']:
        raise ValueError('No reset or automatic retry')
    for s in surfaces.values():
        x0,x1,y0,y1=s['bounds_xy_m']
        if not all(math.isfinite(x) for x in [x0,x1,y0,y1,s['top_z_m'],s['bottom_z_m']]):raise ValueError('Finite geometry required')
        if not (x0<x1 and y0<y1 and s['bottom_z_m']<s['top_z_m']):raise ValueError('Nonempty support required')
    geoms=[]
    for o in objects:
        g=object_geometry(scene,o);x,y,z=g['initial_center_xyz_m'];L,W,H=g['size_m']
        s=surfaces[o['support']];x0,x1,y0,y1=s['bounds_xy_m']
        if not (x0<=x-L/2 and x+L/2<=x1 and y0<=y-W/2 and y+W/2<=y1):
            raise ValueError('Initial object must be wholly supported; no prebuilt bridge')
        geoms.append(g)
    for i,a in enumerate(geoms):
        for b in geoms[i+1:]:
            if all(abs(a['initial_center_xyz_m'][j]-b['initial_center_xyz_m'][j])<(a['size_m'][j]+b['size_m'][j])/2-1e-8 for j in range(3)):
                raise ValueError('Initial objects overlap')
    spec=scene['private_acceptance'];a=surfaces[spec['departure']];b=surfaces[spec['landing']];c=surfaces[spec['upper']]
    gap=b['bounds_xy_m'][0]-a['bounds_xy_m'][1]
    if not gap>0 or not math.isclose(c['top_z_m']-b['top_z_m'],.4):raise ValueError('Real gap before a 40cm rise required')
    if not b['bounds_xy_m'][1]==c['bounds_xy_m'][0]:raise ValueError('Landing must lead to upper platform')
    if not scene['physical_environment']['floor_top_z_m']<a['top_z_m']-.4:raise ValueError('Gap cannot be a flat hidden floor')
    # Existence is a geometric preflight only, not a prescribed plan or dynamics result.
    bridge=[g for g in geoms if g['initial_support_height_m']==a['top_z_m']
        and math.isclose(a['top_z_m']+g['size_m'][2],b['top_z_m']) and g['size_m'][0]>gap+1.]
    steps=[g for g in geoms if g['initial_support_height_m']==b['top_z_m']
        and math.isclose(b['top_z_m']+2*g['size_m'][2],c['top_z_m'])]
    if not bridge or not steps:raise ValueError('Original 20cm rise skill requires geometric bridge and step candidates')
    return dict(box_count=len(objects),gap_width_m=gap,upper_rise_from_landing_m=c['top_z_m']-b['top_z_m'],
        bridge_geometric_candidates=len(bridge),step_geometric_candidates=len(steps),
        dynamics_feasibility_verified=False,task_success=False)


def public_scene(scene):
    """No intended ordering, material truths, roles, waypoints or candidate actions."""
    return dict(schema='ainav-public-declared-geometry-v1',
        goal=deepcopy(scene['goal']),surfaces=[{k:deepcopy(s[k]) for k in ('id','bounds_xy_m','top_z_m')} for s in scene['surfaces']],
        objects=[object_geometry(scene,o) for o in scene['objects']],
        note='Initial blueprint only; object positions after execution must not be treated as current observations.')


class TransferPhysicalWitness:
    """Private measured-sample acceptance. Never supplies actions or gates a route.

    Inputs must come from a separate live/recorded measurement producer. This
    class alone does not authenticate samples or replace motor/native audits.
    """
    def __init__(self,scene):
        validate_scene(scene);self.scene=scene;self.last_time=None
        self.bridge_since={};self.bridge_seen={};self.crossing_time=None;self.final_since=None;self.passed=False

    def observe(self,sample):
        t=sample['time_s'];feet=sample['feet_world_m'];loads=sample['foot_vertical_load_N']
        if not math.isfinite(t) or self.last_time is not None and t<=self.last_time:raise ValueError('Strict actual sample clock required')
        if len(feet)!=4 or any(len(p)!=3 for p in feet) or len(loads)!=4:raise ValueError('Four measured feet/loads required')
        if not all(math.isfinite(x) for row in feet for x in row) or not all(math.isfinite(x) for x in loads):raise ValueError('Finite actual measurements required')
        if self.last_time is not None and t-self.last_time>.020001:
            self.bridge_since.clear();self.final_since=None
        self.last_time=t;cfg=self.scene['private_acceptance'];surfaces={s['id']:s for s in self.scene['surfaces']}
        a=surfaces[cfg['departure']];b=surfaces[cfg['landing']];high=surfaces[cfg['upper']]
        loaded=all(x>cfg['foot_load_gt_N'] for x in loads);spanning={}
        for obj in self.scene['objects']:
            o=sample['objects'][obj['id']];p=o['position_world_m'];R=o['rotation_world_from_box']
            size=self.scene['box_prototypes']['prototypes'][obj['prototype']]['size_m'];half=[v/2 for v in size]
            extent=sum(abs(R[0][i])*half[i] for i in range(3));top=p[2]+half[2]
            span=(p[0]-extent<a['bounds_xy_m'][1]-.3 and abs(p[0]+extent-b['bounds_xy_m'][0])<=cfg['dock_tolerance_m']
                and abs(top-b['top_z_m'])<.02 and abs(R[2][2]-1.)<.01)
            local=[[sum((foot[k]-p[k])*R[k][j] for k in range(3)) for j in range(3)] for foot in feet]
            on=(loaded and span and all(abs(f[0])<half[0] and abs(f[1])<half[1]
                and abs(f[2]-half[2]-cfg['foot_center_radius_m'])<cfg['foot_z_tolerance_m'] for f in local))
            if span:spanning[obj['id']]=(p,half,top)
            if on:
                self.bridge_since.setdefault(obj['id'],t)
                if t-self.bridge_since[obj['id']]>=cfg['loaded_dwell_s']-1e-8:self.bridge_seen.setdefault(obj['id'],t)
            else:self.bridge_since.pop(obj['id'],None)
        base=sample['base_world_xyz_m']
        if a['bounds_xy_m'][1]<=base[0]<=b['bounds_xy_m'][0]:
            for ident,(p,half,top) in spanning.items():
                if ident in self.bridge_seen and abs(base[1]-p[1])<half[1]-.15 and base[2]>top+cfg['crossing_base_clearance_above_bridge_m']:
                    if self.crossing_time is None:self.crossing_time=t
        x0,x1,y0,y1=self.scene['goal']['bounds_xy_m']
        final=(loaded and self.crossing_time is not None and self.crossing_time<t
            and all(x0<f[0]<x1 and y0<f[1]<y1 and abs(f[2]-high['top_z_m']-.022)<cfg['foot_z_tolerance_m'] for f in feet)
            and sample['base_linear_speed_m_s']<cfg['max_linear_speed_m_s']
            and sample['base_angular_speed_rad_s']<cfg['max_angular_speed_rad_s'] and sample['tilt_rad']<cfg['max_tilt_rad'])
        self.final_since=(t if self.final_since is None else self.final_since) if final else None
        self.passed=bool(final and t-self.final_since>=cfg['final_dwell_s']-1e-8)
        return dict(passed=self.passed,loaded_bridge_objects=dict(self.bridge_seen),crossing_time_s=self.crossing_time,
            model_input=False,sample_authenticity_independently_required=True)
