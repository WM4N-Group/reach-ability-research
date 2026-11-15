from pathlib import Path
import sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parent))
from same_clock_pair import source_active
class Clock(unittest.TestCase):
 def test_shorter_source_ends_no_final_frame_hold(self):
  self.assertTrue(source_active(1,count=2,end_tick=25,stride=20));self.assertFalse(source_active(2,count=2,end_tick=25,stride=20))
 def test_missing_original_epoch_not_padded(self):
  with self.assertRaises(ValueError):source_active(1,count=1,end_tick=25,stride=20)
 def test_exact_grid_end_included(self):
  self.assertTrue(source_active(2,count=3,end_tick=40,stride=20));self.assertFalse(source_active(3,count=3,end_tick=40,stride=20))
if __name__=='__main__':unittest.main()
