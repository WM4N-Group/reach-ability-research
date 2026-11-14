from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from .native_domain_v0 import load_domain,validate_domain,candidates,optimization_status,OWNER_DOCS


class NativeDomainTests(unittest.TestCase):
    def setUp(self):
        self.contract=json.loads((OWNER_DOCS/'skill_interface_contract_v0.json').read_text())
        self.manifest=json.loads((OWNER_DOCS/'skill_executor_manifest_v0.json').read_text())

    def test_actual_pins_and_discrete_domain(self):
        domain=load_domain();self.assertEqual(domain['decision_variable']['values'],[.2,.4,.6])
        self.assertIsNone(domain['continuous_preparation_domain'])
        self.assertIsNone(domain['independent_exit_domain'])

    def test_only_three_exact_candidates_for_fixed_object(self):
        rows=candidates(load_domain(),'B');self.assertEqual(len(rows),3)
        self.assertEqual([r['parameters']['push_distance_m'] for r in rows],[.2,.4,.6])
        self.assertTrue(all(r['object_ref']=='B' and r['feasible'] is None for r in rows))

    def test_unknown_not_zero_cost_success_or_global_infeasibility(self):
        r=optimization_status(load_domain());self.assertEqual(r['status'],'UNKNOWN')
        self.assertIsNone(r['best_candidate']);self.assertFalse(r['continuous_solver_called'])
        self.assertFalse(r['global_infeasible']);self.assertFalse(r['execution_authorized'])

    def test_lower_consumer_point_eight_not_exposed(self):
        c=deepcopy(self.contract);c['actions']['PUSH']['parameters']['push_distance_m']['enum'].append(.8)
        with self.assertRaises(ValueError):validate_domain(c,self.manifest)

    def test_continuous_freedom_refused(self):
        c=deepcopy(self.contract);c['actions']['PUSH']['continuous_optimization']=True
        with self.assertRaises(ValueError):validate_domain(c,self.manifest)

    def test_independent_exit_refused(self):
        c=deepcopy(self.contract);c['phases']['EXIT']['requestable']=True
        with self.assertRaises(ValueError):validate_domain(c,self.manifest)

    def test_executor_version_refused(self):
        m=deepcopy(self.manifest);m['executor_version']='another'
        with self.assertRaises(ValueError):validate_domain(self.contract,m)

    def test_unsupported_object_refused(self):
        with self.assertRaises(ValueError):candidates(load_domain(),'A')

    def test_changed_file_requires_explicit_rebinding(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'changed.json';p.write_text(json.dumps(self.contract)+' ')
            with self.assertRaises(ValueError):load_domain(contract_path=p)

    def test_dispatch_or_gpu_permission_not_inherited(self):
        for field in ('physical_dispatch_allowed','GPU_HOLD'):
            m=deepcopy(self.manifest);m[field]=not m[field]
            with self.assertRaises(ValueError):validate_domain(self.contract,m)


if __name__=='__main__':unittest.main()
