"""Software causality/sampling checks; importing renderer does not load simulators."""
import unittest
from render_logged_state_video import row_at,box_at,box_observations

class ReplayTests(unittest.TestCase):
    def test_row_selection_never_interpolates_or_reads_future(self):
        rows=[dict(step=0,time_s=0),dict(step=1,time_s=.02)]
        i,r,ended=row_at(rows,.019);self.assertEqual(i,0);self.assertFalse(ended)
        self.assertEqual(row_at(rows,.02)[0],1)
    def test_terminal_freeze_is_explicit(self):
        i,r,ended=row_at([dict(step=1,time_s=.02)],1)
        self.assertTrue(ended);self.assertEqual(r['time_s'],.02)
        self.assertTrue(row_at([dict(step=1,time_s=.02)],.02)[2])
    def test_missing_early_box_pose_is_not_filled_from_future(self):
        obs=box_observations([], [dict(event='finite_tip_query',time_s=18.42,box_position_w=[1,0,.1])])
        self.assertIsNone(box_at(obs,18.4));self.assertEqual(box_at(obs,18.42)['position'],[1,0,.1])
    def test_control_center_updates_never_claim_orientation(self):
        rows=[dict(time_s=22,push=dict(box_position=[1.1,0,.1]))]
        v=box_at(box_observations(rows,[]),22)
        self.assertIn('NOT_measured',v['orientation']);self.assertEqual(v['time_s'],22)

    def test_renderer_has_no_physics_integration_or_actor_import(self):
        import ast,inspect
        import render_logged_state_video as module
        tree=ast.parse(inspect.getsource(module))
        calls={n.func.attr for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute)}
        self.assertFalse(calls & {'mj_step','mj_step1','mj_step2'})
        modules={alias.name for n in ast.walk(tree) if isinstance(n,ast.Import) for alias in n.names}
        self.assertFalse(modules & {'torch','gymnasium','isaacsim','isaaclab'})

if __name__=='__main__':unittest.main()
