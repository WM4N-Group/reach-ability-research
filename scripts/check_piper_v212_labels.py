"""Focused checks for actual-state ordering, causal eligibility and terminal masks."""
import unittest

from export_piper_v212_labels import normalize, auxiliary_queries, baseline_summary


class Geometry:
    def __init__(self):
        self.calls=[]

    def clearance(self, actual):
        self.calls.append(actual.tolist())
        return 0.06


class V212LabelsChecks(unittest.TestCase):
    def state(self, legal=False, invalid=False):
        return dict(joint_position_rad=list(range(18)),legal_hand_contact=legal,
                    invalid_hand_contact=invalid,forbidden_box_contact=False)

    def test_joint_names_determine_geometry_axes_not_last_six(self):
        names=['joint3','leg0','joint1','joint6','leg1','joint5','joint2','joint4']+[f'leg{i}' for i in range(2,12)]
        geometry=Geometry()
        normalize([dict(before=self.state(),after=self.state())],
                  dict(joint_names=names,control_dt_s=.02),geometry)
        self.assertEqual(geometry.calls,[[2,6,0,7,5,3],[2,6,0,7,5,3]])

    def test_terminal_state_not_extended_as_future(self):
        geometry=Geometry()
        intervals=[dict(before=self.state(),after=self.state()) for _ in range(21)]
        states,rows=normalize(intervals,dict(joint_names=[f'joint{i}' for i in range(1,7)]+[f'leg{i}' for i in range(12)],control_dt_s=.02),geometry)
        qs=auxiliary_queries(states,rows,.02)
        self.assertTrue(qs[0]['targets'][0]['valid'])
        self.assertFalse(qs[0]['targets'][1]['valid'])
        self.assertFalse(qs[-1]['targets'][0]['valid'])
        self.assertEqual(qs[0]['query_event'],'skill_initial')

    def test_future_or_invalid_contact_does_not_change_query_input(self):
        states=[self.state() for _ in range(61)]
        states[10]=self.state(legal=True,invalid=True)
        states[30]=self.state(legal=True)
        rows=[dict(step=i,time_s=i*.02,clearance_m=.06) for i in range(61)]
        qs=auxiliary_queries(states,rows,.02)
        self.assertFalse(qs[4]['inputs']['legal_contact_seen'])
        self.assertTrue(qs[6]['inputs']['legal_contact_seen'])

    def test_baseline_uses_only_post_contact_complete_history_queries(self):
        states=[self.state(legal=i>=30) for i in range(101)]
        rows=[dict(step=i,time_s=i*.02,clearance_m=.06) for i in range(101)]
        queries=auxiliary_queries(states,rows,.02)
        summary=baseline_summary([dict(group_id='g',queries=queries)])
        self.assertEqual(summary[1]['groups'][0]['count'],5) # .6,.7,.8,.9,1.0 -> complete 1s
        self.assertEqual(summary[1]['mean_group_mae_m'],0.)


if __name__=='__main__':
    unittest.main()
