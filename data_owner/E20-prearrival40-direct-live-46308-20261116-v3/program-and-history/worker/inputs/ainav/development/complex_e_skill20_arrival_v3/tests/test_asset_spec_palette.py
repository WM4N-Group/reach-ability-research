"""Fake fresh spec handles, not MuJoCo imports/model/world/compile qualification."""
from pathlib import Path
from types import SimpleNamespace as NS
from copy import deepcopy
import hashlib,sys,unittest
OWN=Path(__file__).resolve().parents[1];sys.path.insert(0,str(OWN))
blocked=[]
def fence(event,args):
 if event=='import'and str(args[0]).split('.')[0]in('numpy','torch','mujoco','onnxruntime'):
  blocked.append(str(args[0]));raise RuntimeError('Explicit fake spec handles only')
 if event in('socket.connect','socket.bind','socket.getaddrinfo','subprocess.Popen'):
  blocked.append(event);raise RuntimeError('No network/child')
sys.addaudithook(fence)
import v4_native_asset as asset

class Spec:
 def __init__(self):
  self.geoms=[NS(name='ground',rgba=[.7,.7,.7,1.],size=[20.,10.,.1]),NS(name='',rgba=[.1,.2,.3,1.]),NS(name='',rgba=[.2,.3,.4,1.])]
  self.bodies=[NS(name='world')];self.worldbody=self;self.lookup_calls=0
 def geom(self,name):
  self.lookup_calls+=1
  return None  # Uncompiled new-name lookup seam reproduced without MuJoCo.
 def add_geom(self,**kw):
  g=NS(**deepcopy(kw));self.geoms.append(g);return g

class Tests(unittest.TestCase):
 def setUp(self):
  self.scene=asset.load_scene();self.spec=Spec();self.sim=NS(spec=self.spec,data=NS(time=0.),queue=[])
  self.bindings={o['public_ref']:dict(body=o['body_name'],geom=o['body_name']+'_geom')for o in self.scene['objects']}
 def build(self,sim,**kw):
  for o in self.scene['objects']:
   sim.spec.bodies.append(NS(name=o['body_name']))
   sim.spec.add_geom(name=o['body_name']+'_geom',rgba=[.55,.36,.19,1.],mass=o['mass_kg'],size=[v/2 for v in o['size_m']],friction=[o['bottom_mu'],0.,0.])
  return dict(bindings=deepcopy(self.bindings),construction_only=True)
 def construct(self,build=None):
  path=Path(__file__);base=NS(__file__=str(path),validate=lambda s:None,construct_into_native_spec=self.build if build is None else build)
  return asset.construct_into_native_spec(self.sim,scene=self.scene,main_steps=0,base_module=base,expected_base_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),mujoco_api=NS(mjtGeom=NS(mjGEOM_BOX='EXPLICIT_SOFTWARE_BOX')))
 def fresh_built(self):self.build(self.sim)
 def apply(self):return asset._apply_current_spec_palette(self.spec,self.scene,self.bindings)
 def test_whole_constructor_current_handles_not_named_lookup(self):
  result=self.construct();self.assertEqual(self.spec.lookup_calls,0)
  self.assertTrue(result['palette']['all_three_exact_current_handles']);self.assertFalse(result['physical_dispatch_authorized'])
  for o in self.scene['objects']:
   g=next(g for g in self.spec.geoms if g.name==o['body_name']+'_geom')
   self.assertNotEqual(g.rgba,[.55,.36,.19,1.]);self.assertEqual(g.mass,.5)
 def test_all_three_targets_and_bindings_before_first_write(self):
  self.fresh_built();self.spec.geoms.pop();before=[g.rgba[:]for g in self.spec.geoms]
  with self.assertRaises(ValueError):self.apply()
  self.assertEqual([g.rgba for g in self.spec.geoms],before)
 def test_duplicate_named_target_refused_not_largest_or_first(self):
  self.fresh_built();self.spec.geoms.append(deepcopy(self.spec.geoms[-1]));before=[g.rgba[:]for g in self.spec.geoms]
  with self.assertRaises(ValueError):self.apply()
  self.assertEqual([g.rgba for g in self.spec.geoms],before)
 def test_named_lookup_returning_foreign_geom_is_never_used(self):
  self.fresh_built();foreign=NS(rgba=[0.,0.,0.,1.]);self.spec.geom=lambda _:foreign
  self.apply();self.assertEqual(foreign.rgba,[0.,0.,0.,1.])
 def test_unnamed_robot_geoms_preserved_separately(self):
  self.fresh_built();before=[g.rgba[:]for g in self.spec.geoms[:3]];self.apply()
  self.assertEqual([g.rgba for g in self.spec.geoms[:3]],before)
 def test_wrong_source_body_binding_refused(self):
  self.fresh_built();self.bindings['cuboid_b']['body']='some_other_body'
  with self.assertRaises(ValueError):self.apply()
 def test_wrong_source_geom_binding_refused(self):
  self.fresh_built();self.bindings['cuboid_a']['geom']='ground'
  with self.assertRaises(ValueError):self.apply()
 def test_missing_or_extra_binding_refused(self):
  self.fresh_built();self.bindings['extra']=self.bindings['cuboid_a']
  with self.assertRaises(ValueError):self.apply()
 def test_nonbrown_last_target_prevents_all_palette_writes(self):
  self.fresh_built();self.spec.geoms[-1].rgba=[0.,0.,0.,1.];before=[g.rgba[:]for g in self.spec.geoms]
  with self.assertRaises(ValueError):self.apply()
  self.assertEqual([g.rgba for g in self.spec.geoms],before)
 def test_bad_color_last_target_prevents_all_palette_writes(self):
  self.fresh_built();self.scene['objects'][-1]['review_color']='#ZZ0000';before=[g.rgba[:]for g in self.spec.geoms]
  with self.assertRaises(ValueError):self.apply()
  self.assertEqual([g.rgba for g in self.spec.geoms],before)
 def test_repeat_palette_is_refused_not_hot_overwrite(self):
  self.fresh_built();self.apply()
  with self.assertRaises(ValueError):self.apply()
 def test_non_RGBA_metadata_unchanged(self):
  self.fresh_built();before=[{k:deepcopy(v)for k,v in vars(g).items()if k!='rgba'}for g in self.spec.geoms];self.apply()
  self.assertEqual([{k:v for k,v in vars(g).items()if k!='rgba'}for g in self.spec.geoms],before)
 def test_spec_rebinding_by_base_is_refused(self):
  other=Spec()
  def changed(sim,**kw):self.build(sim,**kw);sim.spec=other;return dict(bindings=self.bindings)
  with self.assertRaisesRegex(ValueError,'same fresh spec'):self.construct(changed)
 def test_hot_time_FIFO_or_duplicate_install_refused(self):
  self.sim.data.time=.005
  with self.assertRaises(ValueError):self.construct()
  self.sim.data.time=0.;self.sim.queue=[object()]
  with self.assertRaises(ValueError):self.construct()
  self.sim.queue=[];self.spec.bodies.append(NS(name='complex_box_a'))
  with self.assertRaises(ValueError):self.construct()

if __name__=='__main__':unittest.main(verbosity=2)
