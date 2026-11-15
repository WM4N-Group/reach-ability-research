"""Bounded software checks only, no actual GPU/world/lock acquisition."""
from pathlib import Path
import sys,copy,unittest,json
sys.path.insert(0,str(Path(__file__).resolve().parent))
from per_gpu_lease import PROFILES,OWNER,ROOT,ResourceStop,check_binding,parse_gpu,PerGpuLease
from gpu_observation import own_memory_bytes
class PerGPU(unittest.TestCase):
 def payload(self,index):
  p=PROFILES[index];return dict(owner=OWNER,GPU_UUID=p['UUID'],GPU_physical_index=index,Actor_logical_device='cuda:0',MUJOCO_EGL_DEVICE_ID=str(index),locks=[dict(path=str(ROOT/f'resource-locks/native-observer-{kind}-gpu{index}.lock'),device=ident[0],inode=ident[1])for kind,ident in zip(('physics','sdk'),p['locks'])])
 def test_two_profiles_same_owner_not_shared_lock_inode(self):
  for i in(0,1):self.assertEqual(check_binding(i,self.payload(i)),PROFILES[i])
  self.assertTrue(set(PROFILES[0]['locks']).isdisjoint(PROFILES[1]['locks']))
 def test_cross_device_uuid_refused(self):
  p=self.payload(0);p['GPU_UUID']=PROFILES[1]['UUID']
  with self.assertRaises(ResourceStop):check_binding(0,p)
 def test_wrong_inode_refused(self):
  p=self.payload(0);p['locks'][0]['inode']+=1
  with self.assertRaises(ResourceStop):check_binding(0,p)
 def test_logical_actor_and_physical_EGL_not_conflated(self):
  p=self.payload(1);p['MUJOCO_EGL_DEVICE_ID']='0'
  with self.assertRaises(ResourceStop):check_binding(1,p)
 def test_other_GPU_or_bool_index_not_accepted(self):
  for index in(2,True):
   with self.assertRaises(ResourceStop):PerGpuLease(physical_index=index,authority_check=lambda:None)
 def test_gpu_snapshot_and_unknown(self):
  self.assertEqual(parse_gpu('0, '+PROFILES[0]['UUID']+', 24080, 0',index=0)['free_MiB'],24080)
  with self.assertRaises(ResourceStop):parse_gpu('0, '+PROFILES[0]['UUID']+', N/A, 0',index=0)
 def test_initialized_PID_unknown_not_zero(self):
  with self.assertRaises(ValueError):own_memory_bytes('',pid=17,uuid=PROFILES[0]['UUID'],initialized=True)
  self.assertIsNone(own_memory_bytes('',pid=17,uuid=PROFILES[0]['UUID'],initialized=False))
 def test_duplicate_PID_rows_one_observation_not_sum(self):
  row='17, 512, '+PROFILES[0]['UUID'];self.assertEqual(own_memory_bytes(row+'\n'+row,pid=17,uuid=PROFILES[0]['UUID'],initialized=True),512*1024**2)
if __name__=='__main__':unittest.main()
