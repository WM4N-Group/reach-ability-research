"""Geometry-only registration shared by old and new scenes; no task successor table.

The registry maps anonymous public entities to PRIVATE compiled bodies. It does
not choose goals, admit skills, encode material affordances, or rank objects.
Native skills currently use world +X; this is not arbitrary-direction planning.
"""
from dataclasses import dataclass
import math
from types import MappingProxyType


@dataclass(frozen=True)
class SurfaceSpec:
    ref: str
    geom_name: str
    bounds_xy_m: tuple
    top_z_m: float


@dataclass(frozen=True)
class ObjectSpec:
    ref: str
    body_name: str
    size_m: tuple
    initial_support: str


@dataclass(frozen=True)
class GoalSpec:
    surface_ref: str
    bounds_xy_m: tuple


def bounds(value):
    if len(value)!=4 or not all(type(v) in (float,int) and math.isfinite(v) for v in value):
        raise ValueError('Finite explicit XY bounds required')
    if not value[0]<value[1] or not value[2]<value[3]:raise ValueError('Nonempty XY bounds required')
    return tuple(float(x) for x in value)


class SceneRegistry:
    def __init__(self,objects,surfaces,goal,*,retired_objects=()):
        objects=tuple(objects);surfaces=tuple(surfaces)
        if not objects or not surfaces:raise ValueError('Explicit objects and surfaces required')
        all_refs=[o.ref for o in objects]+[s.ref for s in surfaces]
        if len(set(all_refs))!=len(all_refs) or any(not r.isidentifier() for r in all_refs):
            raise ValueError('Unique identifier references required')
        if len({o.body_name for o in objects})!=len(objects):raise ValueError('No object/body aliasing')
        if len({s.geom_name for s in surfaces})!=len(surfaces):raise ValueError('No surface/geom aliasing')
        sm={s.ref:s for s in surfaces}
        for s in surfaces:
            bounds(s.bounds_xy_m)
            if not math.isfinite(s.top_z_m):raise ValueError('Finite surface height required')
        for o in objects:
            if not o.body_name.isidentifier() or o.initial_support not in sm or len(o.size_m)!=3:
                raise ValueError('Explicit native body, support and size required')
            if not all(type(v) in (float,int) and math.isfinite(v) and v>0 for v in o.size_m):
                raise ValueError('Finite positive cuboid dimensions required')
        if goal.surface_ref not in sm:raise ValueError('Goal needs a declared surface')
        g=bounds(goal.bounds_xy_m);s=sm[goal.surface_ref].bounds_xy_m
        if not (s[0]<=g[0]<g[1]<=s[1] and s[2]<=g[2]<g[3]<=s[3]):raise ValueError('Goal region must lie on its surface')
        if set(retired_objects)-{o.ref for o in objects}:raise ValueError('Only actual registered retired identities allowed')
        self.objects=MappingProxyType({o.ref:o for o in objects});self.surfaces=MappingProxyType(sm)
        self.goal=goal;self.retired_objects=frozenset(retired_objects)

    @classmethod
    def from_transfer(cls,scene,bindings):
        # Schema conversion only: case_id, expected route and private acceptance
        # are deliberately NOT inputs to the registry.
        from ainav.transfer_scene import object_geometry
        if set(bindings)!={o['id'] for o in scene['objects']}:raise ValueError('Exact private compiled object mapping required')
        objects=[]
        for o in scene['objects']:
            b=bindings[o['id']];body=b['body']
            if b['geom']!=body+'_geom':raise ValueError('Registered native cuboid geom naming required')
            objects.append(ObjectSpec(o['id'],body,tuple(object_geometry(scene,o)['size_m']),o['support']))
        surfaces=[SurfaceSpec(s['id'],'transfer_'+s['id'],tuple(s['bounds_xy_m']),s['top_z_m']) for s in scene['surfaces']]
        return cls(objects,surfaces,GoalSpec(scene['goal']['surface'],tuple(scene['goal']['bounds_xy_m'])))

    @classmethod
    def from_legacy_full4(cls,protocol,geometry):
        """Import old geometry without changing its required A-prefix semantics."""
        c=protocol['integrated_case'];lane=c['lane_y_m'];width=c['bank_width_m'];g=geometry
        surfaces=[SurfaceSpec('ground','ground',(-20.,20.,-10.,10.),0.),
            SurfaceSpec('deck1','course_high',(g['high_front'],g['near_edge'],lane-width/2,lane+width/2),.4),
            SurfaceSpec('deck2','course_far_base',(g['far_front'],g['far_deck_front']+3.,lane-width/2,lane+width/2),.4),
            SurfaceSpec('deck3','course_far',(g['far_deck_front'],g['far_deck_front']+3.,lane-width/2,lane+width/2),.6)]
        objects=[ObjectSpec('obj0','push_box',(1.2,1.2,.2),'ground'),
            ObjectSpec('obj1','wm_object_middle',(c['step_length_m'],c['step_width_m'],.2),'ground'),
            ObjectSpec('obj2','wm_object_heavy',(c['bridge_length_m'],c['bridge_width_m'],.2),'deck1')]
        goal=GoalSpec('deck3',(g['finish_x']-.4,g['finish_x']+.4,lane-.45,lane+.45))
        # A is not marked retired at construction. Only an actual completed
        # failure-prefix receipt may establish retired ownership in a live host.
        return cls(objects,surfaces,goal)

    def with_retired(self,refs):
        return SceneRegistry(self.objects.values(),self.surfaces.values(),self.goal,retired_objects=self.retired_objects|set(refs))

    def body_to_candidate(self):
        return {o.body_name:o.ref for o in self.objects.values() if o.ref not in self.retired_objects}

    def verify_compiled(self,model):
        import numpy as np
        for o in self.objects.values():
            b=model.body(o.body_name);g=model.geom(o.body_name+'_geom');j=model.joint(o.body_name+'_free')
            if int(g.bodyid[0])!=b.id or int(g.type[0])!=6 or int(j.bodyid[0])!=b.id or int(j.type[0])!=0:
                raise ValueError('Registry must match an actual free cuboid: '+o.ref)
            if not np.allclose(2*g.size,o.size_m,rtol=0,atol=1e-10):raise ValueError('Declared object dimensions differ: '+o.ref)
        for s in self.surfaces.values():
            g=model.geom(s.geom_name)
            if int(g.bodyid[0])!=0:raise ValueError('Fixed surface cannot refer to movable geom')
            if int(g.type[0])==0:  # native infinite floor: declared rectangle is task-map extent
                if abs(float(g.pos[2])-s.top_z_m)>1e-10:raise ValueError('Plane height differs')
                continue
            if int(g.type[0])!=6:raise ValueError('Only registered plane/box surfaces supported')
            actual=(g.pos[0]-g.size[0],g.pos[0]+g.size[0],g.pos[1]-g.size[1],g.pos[1]+g.size[1])
            if not np.allclose(actual,s.bounds_xy_m,rtol=0,atol=1e-10) or abs(float(g.pos[2]+g.size[2])-s.top_z_m)>1e-10:
                raise ValueError('Declared surface differs from compiled geometry: '+s.ref)
        return dict(objects=len(self.objects),surfaces=len(self.surfaces),compiled_geometry_verified=True)

    def public_geometry(self):
        return dict(objects=[dict(ref=o.ref,size_m=list(o.size_m),initial_support=o.initial_support) for o in self.objects.values()],
            surfaces=[dict(ref=s.ref,bounds_xy_m=list(s.bounds_xy_m),top_z_m=s.top_z_m) for s in self.surfaces.values()],
            goal=dict(surface_ref=self.goal.surface_ref,bounds_xy_m=list(self.goal.bounds_xy_m)))


class RegisteredTerrain:
    """Read-only native geometry queries. No fixed B/C height or goal inference."""
    def __init__(self,registry):self.registry=registry

    def surface_geometry(self,sim,ref):
        import numpy as np
        if ref in self.registry.surfaces:
            s=self.registry.surfaces[ref];x0,x1,y0,y1=s.bounds_xy_m
            return dict(front=x0,length=x1-x0,width=y1-y0,lane_y_m=(y0+y1)/2,top=s.top_z_m)
        o=self.registry.objects[ref];bid=sim.model.body(o.body_name).id;p=sim.data.xpos[bid];R=sim.data.xmat[bid].reshape(3,3)
        # The frozen actors do not support arbitrarily rotated/yawed workpieces.
        if not np.allclose(R,np.eye(3),rtol=0,atol=.08):raise ValueError('Outside original axis-aligned skill domain')
        return dict(front=float(p[0]-o.size_m[0]/2),length=o.size_m[0],width=o.size_m[1],lane_y_m=float(p[1]),top=float(p[2]+o.size_m[2]/2))

    def climb_geometry(self,sim,ref,*,source_surface_height_m):
        g=self.surface_geometry(sim,ref)
        if not math.isfinite(source_surface_height_m) or abs(g['top']-source_surface_height_m-.2)>.01:
            raise ValueError('Original 20cm climb rise required, not a scene-name height table')
        return dict(g,base_height=source_surface_height_m)

    def height_at(self,sim,x,y):
        import numpy as np
        import mujoco
        x,y=np.asarray(x),np.asarray(y)
        if x.shape!=y.shape or not np.isfinite(x).all() or not np.isfinite(y).all():raise ValueError('Matching finite surface coordinates required')
        out=np.empty(x.shape);group=np.array([0,1,0,0,0,0],dtype=np.uint8);hit=np.zeros(1,dtype=np.int32)
        for i,(px,py) in enumerate(zip(x.ravel(),y.ravel())):
            distance=mujoco.mj_ray(sim.model,sim.data,np.array([px,py,3.]),np.array([0.,0.,-1.]),group,1,-1,hit)
            if distance<0:raise ValueError('No actual registered support geometry')
            out.flat[i]=3.-distance
        return out


def declared_push_source(registry,body_name,surface_height_m):
    """Software source declaration only; live four-foot admission is separate."""
    found=[o for o in registry.objects.values() if o.body_name==body_name]
    if len(found)!=1 or type(surface_height_m) not in (int,float) or not math.isfinite(surface_height_m):
        raise ValueError('Unique finite registered object/source declaration required')
    obj=found[0]
    if obj.ref in registry.retired_objects:raise ValueError('Retired object cannot get a new PUSH attempt')
    if registry.surfaces[obj.initial_support].top_z_m!=surface_height_m:raise ValueError('PUSH source differs from declared object support')
    return obj
