"""Frozen heldout assembly SOFTWARE tests: no data, fit, native calls or files."""
from copy import deepcopy
import unittest
from unittest.mock import patch
from .test_staged_successor_critic import staged_fixture,stage
from .successor_aware_choice import digest
from .successor_critic import _training_rows_digest
from .frozen_heldout_dataset import assemble_frozen_heldout,ROW_STATUS,UNREACHED_STATUS


class FrozenHeldoutAssemblyTests(unittest.TestCase):
    def setUp(self):
        data,self.auth,self.protocol=staged_fixture()
        self.protocol['feature_extractor_sha256']='e'*64
        for i,r in enumerate(self.protocol['attempt_schedule'],1):r['ordinal']=i
        data['feature_extractor_sha256']='e'*64;data['preregistration_sha256']=digest(self.protocol)
        self.train=stage(data,'TRAIN_ONLY');self.train['unreached_decision_attempts']=[]
        model={'SOFTWARE_FIXTURE_NOT_FIT_MODEL':True}
        self.artifact=dict(status='TRAIN_ONLY_FIT_FROZEN_HELDOUT_NOT_COLLECTED',model=model,
            model_sha256=digest(model),preregistration_sha256=digest(self.protocol),
            training_rows_sha256=_training_rows_digest(self.train['rows']))
        self.reports=[self.report(r)for r in data['rows']if r['split']!='TRAIN']
        guard=patch('research.task_conditioned_reachability.execution_preparation.successor_critic._fit_heads',
                    side_effect=AssertionError('NO FITTER IN ASSEMBLY'))
        guard.start();self.addCleanup(guard.stop)
    def report(self,row):
        row=deepcopy(row);row['source_journal_sha256']='f'*64
        return dict(role='NEW_PURPOSE_EXTRACTED_ATTEMPT_NOT_BATCH_FIT_PERMISSION',fit_allowed=False,
            actual_research_model_fits=0,new_physics_or_capture=False,
            collection_protocol_file_sha256='f'*64,feature_profile_sha256=self.protocol['feature_profile_sha256'],
            feature_extractor_sha256='e'*64,status=ROW_STATUS,sample=row,unreached_decision_attempt=None,
            inventory={**row,'decision_reached':True})
    def assemble(self,reports=None,phase='CALIBRATION'):
        return assemble_frozen_heldout(self.train,self.auth,self.protocol,self.artifact,
            deepcopy(self.reports[:3])if reports is None else reports,phase=phase)
    def test_exact_cal_phase_preserves_TRAIN_model_and_inputs_without_fit(self):
        before=deepcopy((self.train,self.artifact,self.reports,self.protocol));data=self.assemble()
        self.assertEqual(data['closed_attempt_count'],9);self.assertEqual(data['rows'][:6],self.train['rows'])
        self.assertEqual(_training_rows_digest(data['rows']),self.artifact['training_rows_sha256'])
        self.assertEqual(before,(self.train,self.artifact,self.reports,self.protocol))
        self.assertNotIn('VALIDATION',{r['split']for r in data['rows']})
    def test_full_phase_requires_all_six_heldout_not_only_VAL(self):
        out=self.assemble(self.reports,phase='FULL_COHORT');self.assertEqual(out['closed_attempt_count'],12)
        with self.assertRaisesRegex(ValueError,'Complete closed heldout'):
            self.assemble(self.reports[3:],phase='FULL_COHORT')
    def test_partial_or_duplicate_CAL_is_not_a_phase_or_a_new_sample(self):
        with self.assertRaisesRegex(ValueError,'Complete closed heldout'):self.assemble(self.reports[:1])
        with self.assertRaisesRegex(ValueError,'once'):self.assemble([self.reports[0]]*3)
    def test_later_VAL_and_TRAIN_report_never_relabelled_as_CAL(self):
        with self.assertRaisesRegex(ValueError,'no TRAIN/duplicate/replacement'):self.assemble(self.reports[3:])
        with self.assertRaisesRegex(ValueError,'no TRAIN/duplicate/replacement'):
            self.assemble([self.report(self.train['rows'][0]),*self.reports[:2]])
    def test_frozen_train_change_refused(self):
        self.train['rows'][0]['physical_features'][2]+=.1
        with self.assertRaisesRegex(ValueError,'TRAIN rows changed'):self.assemble()
    def test_frozen_model_change_refused(self):
        self.artifact['model']['changed']=True
        with self.assertRaisesRegex(ValueError,'model content changed'):self.assemble()
    def test_derived_protocol_cannot_be_rewritten_after_fit(self):
        self.protocol['changed_after_fit']='SOFTWARE_ONLY'
        self.train['preregistration_sha256']=digest(self.protocol)
        with self.assertRaisesRegex(ValueError,'Original frozen fit/protocol'):self.assemble()
    def test_extraction_abi_or_inventory_drift_refused(self):
        reports=deepcopy(self.reports[:3]);reports[0]['feature_extractor_sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'48-slot ABI'):self.assemble(reports)
        reports=deepcopy(self.reports[:3]);reports[0]['inventory']['spent_sim_s']=0.
        with self.assertRaisesRegex(ValueError,'inventory must agree'):self.assemble(reports)
    def test_unknown_postdecision_exception_cannot_be_dropped_or_labelled(self):
        reports=deepcopy(self.reports[:3]);reports[0].update(sample=None,
            status='POSTDECISION_FAILURE_UNCLASSIFIED_NO_FIT_NO_FABRICATED_LABEL')
        with self.assertRaisesRegex(ValueError,'UNKNOWN is not a label'):self.assemble(reports)
    def test_unreached_keeps_attempt_spend_without_successor_label_or_features(self):
        reports=deepcopy(self.reports[:3]);r=reports[0];row=r.pop('sample')
        for k in ('physical_features','outcome','current_READY_s','full_success_s'):row.pop(k,None)
        row.update(decision_reached=False,physical_features=None,spent_sim_s=51.)
        r.update(sample=None,unreached_decision_attempt=row,status=UNREACHED_STATUS,
                 inventory={**row,'decision_reached':False})
        out=self.assemble(reports)
        self.assertEqual(out['closed_attempt_count'],9);self.assertEqual(len(out['rows']),8)
        self.assertEqual(out['unreached_decision_attempts'][0]['spent_sim_s'],51.)
        self.assertIsNone(out['unreached_decision_attempts'][0]['physical_features'])
    def test_censoring_not_changed_to_failure_or_success_cost(self):
        reports=deepcopy(self.reports[:3]);r=reports[0]['sample']
        r.update(outcome='CENSORED',full_success_s=None,successful_task_endpoint_verified=False)
        out=self.assemble(reports);self.assertEqual(out['rows'][6]['outcome'],'CENSORED')
        self.assertIsNone(out['rows'][6]['full_success_s'])
    def test_shuffled_reports_are_assembled_in_original_ordinal_order(self):
        out=self.assemble(list(reversed(self.reports[:3])))
        self.assertEqual([r['attempt_key']for r in out['rows'][6:]],
                         [r['sample']['attempt_key']for r in self.reports[:3]])


if __name__=='__main__':unittest.main()
