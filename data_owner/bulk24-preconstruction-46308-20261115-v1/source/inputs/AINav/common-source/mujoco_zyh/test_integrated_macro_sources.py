import unittest
from mujoco_zyh.audit_integrated_macro_sources import code_fingerprints,horizon_changes

class MacroSourceAuditTests(unittest.TestCase):
    def test_AST_control_fingerprints_separate_revision_labels_from_control_code(self):
        a='REVISION=15\ndef install(r):\n def command():\n  return r+1\n return command\n'
        b=a.replace('REVISION=15','REVISION=16')
        self.assertEqual(code_fingerprints(a),code_fingerprints(b))
        c=a.replace('return r+1','return r+2')
        self.assertNotEqual(code_fingerprints(a)['install.command'],code_fingerprints(c)['install.command'])
    def test_horizon_transition_is_retrospective_and_censored_without_future(self):
        times=[0.,.5,1.,1.5,2.];labels=['nav','nav','prepare','climb','climb']
        self.assertIs(horizon_changes(times,labels,0,.5),False)
        self.assertEqual(horizon_changes(times,labels,0,2.),1.)
        self.assertIsNone(horizon_changes(times,labels,3,1.))
