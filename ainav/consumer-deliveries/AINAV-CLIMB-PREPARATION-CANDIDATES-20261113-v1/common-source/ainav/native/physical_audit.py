"""Private same-world achievement history, never a planner input or controller.

Final endpoint alone cannot prove visiting the 40cm platform. Observe actual
loaded foot placements on B, HIGH and C without imposing a skill/stage order or
PUSH count. The unchanged original endpoint/FarBankStop still owns final success.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import math

SURFACES = ('B', 'HIGH', 'C')


@dataclass
class PhysicalCourseHistory:
    stable_seconds: float = .1
    max_observation_gap_s: float = .020001
    last_time_s: float | None = None
    since: dict = field(default_factory=dict)
    achieved: dict = field(default_factory=dict)
    samples: int = 0

    def observe(self, *, time_s, loaded_footprints, evidence_ref):
        if (type(time_s) not in (int,float) or not math.isfinite(time_s) or time_s < 0
                or set(loaded_footprints) != set(SURFACES)
                or any(type(v) is not bool for v in loaded_footprints.values()) or not evidence_ref):
            raise ValueError('Actual clock and explicit private footprint booleans required')
        if self.last_time_s is not None:
            dt = time_s-self.last_time_s
            if abs(dt) < 1e-9: return ()
            if dt < 0: raise ValueError('Physical audit cannot rewind')
            if dt > self.max_observation_gap_s:
                self.since.clear()  # never interpolate a support interval through missing samples
        self.last_time_s = time_s
        self.samples += 1
        newly = []
        for name in SURFACES:
            if not loaded_footprints[name]:
                self.since.pop(name, None)
                continue
            self.since.setdefault(name,time_s)
            if name not in self.achieved and time_s-self.since[name] >= self.stable_seconds-1e-8:
                self.achieved[name] = dict(surface=name, first_loaded_time_s=self.since[name],
                    observed_time_s=time_s, stable_seconds=time_s-self.since[name],
                    evidence_ref=evidence_ref, actual_four_feet_loaded=True, model_input=False)
                newly.append(dict(self.achieved[name]))
        return tuple(newly)

    def report(self):
        return dict(schema='private-course-physical-achievement-history-v1', model_input=False,
            all_required_surfaces_observed=set(self.achieved)==set(SURFACES),
            required_surfaces=list(SURFACES), achievements=dict(self.achieved),
            minimum_stable_seconds=self.stable_seconds, samples=self.samples,
            skill_order_required=False, prescribed_PUSH_count=False,
            actual_native_endpoint_still_required=True)


def measure_footprints(runtime, config, integrated):
    """Read real native geometry/contact force only on the private audit path.

    No mass/friction query, controller construction, step, simulation mutation or
    map-to-achieved shortcut. Every foot must be supported on the actual top face.
    """
    import numpy as np
    p = runtime.sim
    ids = [p.model.body(name+'_foot').id for name in ('FR','FL','RR','RL')]
    feet = np.asarray(p.data.xpos[ids], dtype=np.float64)
    loads = np.asarray(p.forces[ids,2], dtype=np.float64)
    if feet.shape != (4,3) or loads.shape != (4,) or not np.isfinite(feet).all() or not np.isfinite(loads).all():
        raise ValueError('Actual finite four-foot position/support evidence required')
    c, g = config['integrated_case'], integrated.layout(config['integrated_case'])
    supported = bool(np.all(loads > 3.))
    result, boxes = {}, {}
    for label, body, length, width in (
        ('B','wm_object_middle',c['step_length_m'],c['step_width_m']),
        ('C','wm_object_heavy',c['bridge_length_m'],c['bridge_width_m'])):
        bid = p.model.body(body).id
        position = np.asarray(p.data.xpos[bid])
        rotation = np.asarray(p.data.xmat[bid]).reshape(3,3)
        local = (feet-position)@rotation
        dock = runtime.staircase.dock_metrics(type('AuditView',(),dict(model=p.model,data=p.data,box_id=bid))())
        boxes[label] = dict(body=body,position_world_m=position.tolist(),
            rotation_world_from_box=rotation.tolist(),length_m=length,width_m=width,
            dock_gap_m=float(dock['gap_m']))
        result[label] = bool(supported and -.01 <= dock['gap_m'] <= .01
            and np.all(abs(local[:,0]) < length/2) and np.all(abs(local[:,1]) < width/2)
            and np.all(abs(local[:,2]-.122) < .04))
    result['HIGH'] = bool(supported and np.all(feet[:,0] > g['high_front'])
        and np.all(feet[:,0] < g['near_edge'])
        and np.all(abs(feet[:,1]-c['lane_y_m']) < c['bank_width_m']/2)
        and np.all(abs(feet[:,2]-.422) < .04))
    return dict(schema='actual-private-course-footprint-sample-v1',model_input=False,
        time_s=float(p.data.time),feet_world_m=feet.tolist(),foot_vertical_load_N=loads.tolist(),
        boxes=boxes,loaded_footprints=result)


def loaded_footprints(runtime, config, integrated):
    return measure_footprints(runtime,config,integrated)['loaded_footprints']
