"""Pure contact arithmetic/clock fixtures; no live MuJoCo or native success."""
from pathlib import Path
import sys,unittest,json
OWN=Path(__file__).resolve().parents[1];sys.path.insert(0,str(OWN));blocked=[]
def fence(event,args):
 if event=='import'and str(args[0]).split('.')[0]in('numpy','torch','mujoco','onnxruntime'):blocked.append(str(args[0]));raise RuntimeError('Pure terminal fixtures only')
 if event in('socket.connect','socket.bind','socket.getaddrinfo','subprocess.Popen'):blocked.append(event);raise RuntimeError('No network/child')
sys.addaudithook(fence)
from elevated_terminal import deck_normal_loads,ElevatedGoalDwell
from v4_native_asset import load_scene
class Tests(unittest.TestCase):
 def setUp(self):self.scene=load_scene();self.mapping={11:0,12:1,13:2,14:3,15:0};self.monitor=ElevatedGoalDwell(self.scene)
 def sample(self,tick,z=.622,support='goal_deck'):
  return dict(time_s=tick*.005,tick=tick,feet_world_m=[[14.,-2.6,z]]*4,foot_normal_N=[12.]*4,foot_speed_m_s=[0.]*4,base_linear_speed_m_s=0.,base_angular_speed_rad_s=0.,tilt_rad=0.,foot_support_refs=[support]*4,role='SOFTWARE_FIXTURE_NOT_PHYSICAL')
 def test_normal_frame_and_reversed_geom_order_same_positive_support(self):
  r=deck_normal_loads(self.mapping,99,[(99,11,[0.,0.,1.],12.),(12,99,[0.,0.,-1.],13.),(99,13,[0.,0.,1.],14.),(14,99,[0.,0.,-1.],15.)]);self.assertEqual(r,[12.,13.,14.,15.])
 def test_other_contacts_and_horizontal_side_normals_do_not_fake_deck_support(self):
  r=deck_normal_loads(self.mapping,99,[(20,11,[0.,0.,1.],100.),(99,12,[1.,0.,0.],100.)]);self.assertEqual(r,[0.]*4)
 def test_multiple_geoms_and_contacts_sum_for_same_actual_foot(self):
  self.assertEqual(deck_normal_loads(self.mapping,99,[(99,11,[0.,0.,1.],6.),(15,99,[0.,0.,-1.],6.)]),[12.,0.,0.,0.])
 def test_invalid_frame_nonfinite_or_tensile_normal_refuse(self):
  for normal,force in [([0.,0.,2.],12.),([0.,0.,1.],float('nan')),([0.,0.,1.],-1.)]:
   with self.assertRaises(ValueError):deck_normal_loads(self.mapping,99,[(99,11,normal,force)])
 def test_actual_contiguous_200Hz_half_second_necessary_dwell_only(self):
  for tick in range(100):self.assertFalse(self.monitor.observe(self.sample(tick)))
  self.assertTrue(self.monitor.observe(self.sample(100)));self.assertFalse(hasattr(self.monitor,'complete'))
 def test_duplicate_clock_cannot_accumulate_dwell_and_load_loss_resets(self):
  for _ in range(101):self.assertFalse(self.monitor.observe(self.sample(0)))
  for tick in range(1,101):self.monitor.observe(self.sample(tick))
  bad=self.sample(100);bad['foot_normal_N'][0]=11.9;self.assertFalse(self.monitor.observe(bad));self.assertFalse(self.monitor.observe(self.sample(101)))
 def test_missing_tick_resets_continuity_not_interpolated(self):
  for tick in range(70):self.monitor.observe(self.sample(tick))
  self.assertFalse(self.monitor.observe(self.sample(100)))
  for tick in range(101,200):self.assertFalse(self.monitor.observe(self.sample(tick)))
  self.assertTrue(self.monitor.observe(self.sample(200)))
 def test_goal_XY_ground_or_wrong_contact_surface_never_starts_dwell(self):
  for tick in range(110):self.assertFalse(self.monitor.observe(self.sample(tick,z=.022)))
  for tick in range(110,220):self.assertFalse(self.monitor.observe(self.sample(tick,support='ground')))
 def test_clock_rewind_refused(self):
  self.monitor.observe(self.sample(100))
  with self.assertRaises(ValueError):self.monitor.observe(self.sample(99))
if __name__=='__main__':
 r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests));print(json.dumps(dict(role='V4_PRIVATE_CONTACT_ARITHMETIC_AND_DWELL_SOFTWARE_ONLY',checks=r.testsRun,failures=len(r.failures),errors=len(r.errors),forbidden_attempts=blocked,actual_Runtime_or_MuJoCo_reader_calls=0)));sys.exit(0 if r.wasSuccessful()and not blocked else 1)
