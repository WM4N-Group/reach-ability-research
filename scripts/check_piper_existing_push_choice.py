"""Synthetic native/event/efficiency checks for the adopted fast/slow full-call pilot."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from label_piper_existing_push_choice import (
    ACTOR, EVALUATORS, INITIAL_KEYS, ROLE, STUDY, TERMS, evaluate, flags_label,
    report_label, reset_fingerprint, sequence_events, sha, summarize,
)


def flags(**values):
    return {name:values.get(name,False) for name in sorted(TERMS)}


def report(arm='fast',success=True,seconds=20.):
    names=sorted(TERMS);f=flags(box_settled=success,invalid_hand_contact=not success)
    return dict(evaluation_sha256=EVALUATORS[arm],checkpoint_sha256=ACTOR,
        num_envs=1,episodes_per_env=1,requested_episodes=1,completed_episodes=1,incomplete_episodes=0,
        successful_episodes=int(success),episode_length_s=48,box_mass=1,box_friction=.15,
        termination_flag_names=names,terminal_states=[dict(env_id=0,episode=1,elapsed_seconds=seconds,
                                                         termination_flags=[f[n] for n in names])])


def cases():
    return [dict(episode_id=f'{seed}-{arm}',arm=arm,seed=seed) for seed in (1,2) for arm in ('slow','fast')]


def rows(values=(True,True,True,True),times=(40.,16.,42.,18.)):
    out=[]
    for c,value,t in zip(cases(),values,times):
        out.append(dict(episode_id=c['episode_id'],arm=c['arm'],seed_audit_only=c['seed'],started=True,
            group_id='g'+str(c['seed']),source_valid=True,joint_names=['joint1'],
            initial_before={k:[0.] for k in INITIAL_KEYS},
            task=dict(value=value,valid=value is not None,successful_completion_seconds=t if value is True else None,program_error=False)))
    return out


class ExistingPushChoiceChecks(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)

    def test_original_goal_and_timeout_simultaneously_is_success(self):
        x=flags_label(flags(box_settled=True,time_out=True),48.)
        self.assertIs(x['value'],True)

    def test_native_safety_vetoes_same_frame_goal(self):
        x=flags_label(flags(box_settled=True,arm_effort_safety=True),14.)
        self.assertIs(x['value'],False);self.assertIsNone(x['successful_completion_seconds'])

    def test_report_goal_survives_later_program_error(self):
        x=report_label(report(), 'fast', 1)
        self.assertIs(x['value'],True);self.assertTrue(x['program_error'])

    def test_native_timeout_is_negative_not_unknown(self):
        x=flags_label(flags(time_out=True),48.)
        self.assertIs(x['value'],False);self.assertEqual(x['execution_status'],'normal_timeout')

    def test_missing_terminal_is_unknown_not_failure(self):
        r=report();r['terminal_states']=[];r['completed_episodes']=0;r['incomplete_episodes']=1;r['successful_episodes']=0
        x=report_label(r,'fast',1);self.assertIsNone(x['value']);self.assertFalse(x['valid'])

    def test_empty_native_outcome_flags_do_not_imply_failure(self):
        self.assertIsNone(flags_label(flags(),1.)['value'])

    def test_no_extension_of48s_budget(self):
        x=flags_label(flags(box_settled=True),48.02)
        self.assertIsNone(x['value']);self.assertFalse(x['original48s_clock_compatible'])
        self.assertIs(flags_label(flags(box_settled=True),48.000004)['value'],True)

    def test_flag_array_order_uses_explicit_native_names(self):
        r=report();r['termination_flag_names'].reverse();r['terminal_states'][0]['termination_flags'].reverse()
        self.assertIs(report_label(r,'fast')['value'],True)

    def test_missing_or_duplicate_term_mapping_rejected(self):
        r=report();r.pop('termination_flag_names')
        with self.assertRaises(KeyError):report_label(r,'fast')
        r=report();r['termination_flag_names'][-1]=r['termination_flag_names'][0]
        with self.assertRaises(ValueError):report_label(r,'fast')

    def test_numeric_native_bool_and_wrong_arm_source_rejected(self):
        r=report();r['terminal_states'][0]['termination_flags'][0]=0
        with self.assertRaises(ValueError):report_label(r,'fast')
        with self.assertRaises(ValueError):report_label(report('slow'),'fast')
        r=report();r['box_mass']=True
        with self.assertRaises(ValueError):report_label(r,'fast')

    def test_multiple_terminals_or_wrong_identity_rejected(self):
        r=report();r['terminal_states']*=2
        with self.assertRaises(ValueError):report_label(r,'fast')
        r=report();r['terminal_states'][0]['env_id']=1
        with self.assertRaises(ValueError):report_label(r,'fast')

    def test_source_native_success_counter_conflict_visible(self):
        r=report();r['successful_episodes']=0
        with self.assertRaisesRegex(ValueError,'predicate'):report_label(r,'fast')

    def test_same_success_fast_time_gain_does_not_need_binary_reversal(self):
        s=summarize(rows(),cases())
        self.assertEqual(s['arms']['fast']['native_success'],2)
        self.assertEqual(s['common_success_pairs'],2);self.assertEqual(s['paired_fast_time_gain_s'],[24.,24.])
        self.assertEqual(s['hindsight_added_completions_over_best_fixed'],0)
        self.assertTrue(s['success_reversal_is_not_required_for_this_adopted_efficiency_pilot'])

    def test_failed_fast_not_counted_as_quick_success(self):
        s=summarize(rows((True,False,True,True)),cases())
        self.assertEqual(s['arms']['fast']['native_failure'],1);self.assertEqual(s['slow_rescue_pairs'],1)
        self.assertEqual(s['common_success_pairs'],1);self.assertIsNone(s['pairs'][0]['fast_time_gain_s'])
        self.assertEqual(s['pairs'][1]['fast_time_gain_s'],24.)

    def test_unknown_keeps_full_denominator(self):
        s=summarize(rows((True,None,True,True)),cases())
        self.assertEqual(s['planned_slots'],4);self.assertEqual(s['actual_started'],4)
        self.assertEqual(s['arms']['fast']['unknown'],1);self.assertEqual(s['comparable_known_pairs'],1)

    def test_unrun_not_actual_charge_or_failure(self):
        r=rows((True,None,None,None))
        for item in r[1:]:item.update(started=False,source_valid=False,initial_before=None)
        s=summarize(r,cases());self.assertEqual(s['actual_started'],1)
        self.assertEqual(s['arms']['fast']['native_failure'],0);self.assertEqual(s['arms']['fast']['not_started'],2)

    def test_missing_or_nonidentical_reset_kept_but_not_paired(self):
        r=rows();r[1]['initial_before']['box_position_xyz']=[1.]
        s=summarize(r,cases());self.assertEqual(s['actual_started'],4);self.assertEqual(s['comparable_known_pairs'],1)
        self.assertFalse(s['pairs'][0]['comparable']);self.assertEqual(s['arms']['fast']['native_success'],2)

    def test_joint_name_identity_not_just_same_array_values(self):
        r=rows();r[1]['joint_names']=['different_joint']
        self.assertFalse(summarize(r,cases())['pairs'][0]['comparable'])

    def test_different_actions_after_reset_are_allowed(self):
        r=rows();r[0]['post_decision_action']=[0.];r[1]['post_decision_action']=[1.]
        self.assertEqual(summarize(r,cases())['comparable_known_pairs'],2)

    def test_identical_measured_reset_groups_do_not_inflate_independent_count(self):
        r=rows()
        for x in r:x['group_id']='same_actual_group'
        s=summarize(r,cases());self.assertEqual(s['distinct_measured_pair_groups'],1)

    def test_duplicate_slot_or_wrong_arm_not_silently_accepted(self):
        r=rows();r[1]['episode_id']=r[0]['episode_id']
        with self.assertRaises(ValueError):summarize(r,cases())
        r=rows();r[0]['arm']='fast'
        with self.assertRaises(ValueError):summarize(r,cases())

    def test_stage_observations_survive_bad_suffix_without_negative_fill(self):
        state=dict(controller_observed={'safe_approach_complete':True},legal_hand_contact=True,
                   invalid_hand_contact=False,forbidden_box_contact=False)
        p=self.root/'seq';p.write_text(json.dumps(dict(index=0,env_id=0,interval_start_s=0.,before=state,terminal=False))+'\n'+
                                       json.dumps(dict(index=2,env_id=0,interval_start_s=.04,before=state,terminal=False))+'\n')
        x=sequence_events(p,dict(num_envs=1,control_dt_s=.02))
        self.assertEqual(x['first_legal_contact_s'],0.);self.assertEqual(x['first_approach_flag_s'],0.)
        self.assertIsNotNone(x['prefix_stop_reason'])

    def test_terminal_after_is_observation_not_new_decision_or_bridge(self):
        before=dict(controller_observed={},legal_hand_contact=False,invalid_hand_contact=False,forbidden_box_contact=False)
        after=dict(before,legal_hand_contact=True)
        p=self.root/'seq';p.write_text(json.dumps(dict(index=0,env_id=0,interval_start_s=0.,before=before,after=after,
                terminal=True,after_captured_before_reset=True))+'\n')
        x=sequence_events(p,dict(num_envs=1,control_dt_s=.02))
        self.assertEqual(x['first_legal_contact_s'],.02);self.assertEqual(x['valid_prefix_intervals'],1)
        self.assertEqual(x['initial_before'],before)

    def test_started_owner_slot_counts_even_before_physical_record_closed(self):
        cases0=cases();protocol=dict(study_id=STUDY,role=ROLE,decision_event='original_reset_before_first_skill_action',
          maximum_new_attempts=6,automatic_retry=False,training_enabled=False,model_action_authority=False,cases=cases0,
          arms={arm:dict(skill_version='push-entry-retreat-v209' if arm=='slow' else 'push-direct-approach-v212',
                         evaluator_sha256=EVALUATORS[arm],actor_sha256=ACTOR) for arm in ('slow','fast')})
        pp=self.root/'protocol.json';pp.write_text(json.dumps(protocol))
        split=dict(measured_groups={});sp=self.root/'group_split.json';sp.write_text(json.dumps(split))
        manifest=dict(skill_choice_studies={STUDY:dict(protocol=dict(path=str(pp),sha256=sha(pp)))},
          group_split={'sha256':sha(sp)},physical_episodes=[],planned_episodes=[dict(**c,study_id=STUDY,role=ROLE,
          status='started' if i==0 else 'reserved_not_started') for i,c in enumerate(cases0)])
        (self.root/'batch_manifest.json').write_text(json.dumps(manifest));(self.root/'collection_ledger.jsonl').write_text('')
        value=evaluate(self.root,pp)
        self.assertEqual(value['summary']['actual_started'],1);self.assertIsNone(value['records'][0]['task']['value'])
        self.assertEqual(value['records'][0]['owner_status'],'started')


    def test_bad_optional_phase_log_does_not_block_report_and_startup_pair(self):
        planned=cases();protocol=dict(study_id=STUDY,role=ROLE,decision_event='original_reset_before_first_skill_action',
          maximum_new_attempts=6,automatic_retry=False,training_enabled=False,model_action_authority=False,cases=planned,
          code_sha256={'v212_sequence_recording.py':'frozen-recorder'},
          arms={arm:dict(skill_version='push-entry-retreat-v209' if arm=='slow' else 'push-direct-approach-v212',
                         evaluator_sha256=EVALUATORS[arm],actor_sha256=ACTOR) for arm in ('slow','fast')})
        def write(name,data):
            p=self.root/name;p.write_text(json.dumps(data));return {'path':str(p),'sha256':sha(p)}
        pp=self.root/'protocol.json';pp.write_text(json.dumps(protocol));physical=[]
        initial={k:[0.] for k in INITIAL_KEYS}
        domain=dict(initial_states=[initial],robot_body_masses_kg=[[1.]],box_mass_kg=[1.],box_material_properties=[[[.15,.15]]])
        gid=reset_fingerprint(domain)
        for i,c in enumerate(planned[:2]):
            r=report(c['arm'],True,40. if c['arm']=='slow' else 16.);r.update(seed=1,joint_names=['joint1'])
            # Phase stream is unusable but independently hashed startup/report are intact.
            sequence=write('bad-seq'+str(i),{'not':'an interval'})
            physical.append(dict(episode_id=c['episode_id'],seed_audit_only=1,arm=c['arm'],study_id=STUDY,role=ROLE,
                skill_version=protocol['arms'][c['arm']]['skill_version'],protocol_sha256=sha(pp),status='closed',group_id=gid,
                task_scope='original_reset_complete_push_skill_choice',model_action_authority=False,
                allowed_for_model_training=False,allowed_for_independent_model_validation=False,returncode=0,
                report=write('report'+str(i),r),startup=write('startup'+str(i),domain),sequence=sequence,
                metadata=write('meta'+str(i),dict(num_envs=1,control_dt_s=.1,evaluator_sha256=EVALUATORS[c['arm']],recorder_sha256='frozen-recorder'))))
        split=dict(measured_groups={gid:dict(role=ROLE,episodes=[x['episode_id'] for x in planned[:2]])})
        sp=self.root/'group_split.json';sp.write_text(json.dumps(split))
        manifest=dict(skill_choice_studies={STUDY:dict(protocol={'path':str(pp),'sha256':sha(pp)})},group_split={'sha256':sha(sp)},
          physical_episodes=physical,planned_episodes=[dict(**c,study_id=STUDY,role=ROLE,status='closed' if i<2 else 'reserved_not_started') for i,c in enumerate(planned)])
        write('batch_manifest.json',manifest);(self.root/'collection_ledger.jsonl').write_text('')
        evaluated=evaluate(self.root,pp)
        self.assertTrue(all(x['task']['value'] is True for x in evaluated['records'][:2]))
        self.assertTrue(all(x['stage_error'] for x in evaluated['records'][:2]))
        self.assertEqual(evaluated['summary']['common_success_pairs'],1)
        self.assertEqual(evaluated['summary']['paired_fast_time_gain_s'],[24.])


    def test_known_native_success_and_recording_error_are_separate_counts(self):
        r=rows();r[0].update(owner_status='runtime_or_recording_failure',source_valid=False,
                              canonical_source={'postprocessing_error':{'type':'AuditError'}})
        s=summarize(r,cases())
        self.assertEqual(s['arms']['slow']['native_success'],2)
        self.assertEqual(s['arms']['slow']['recording_or_postprocessing_errors'],1)
        self.assertEqual(s['comparable_known_pairs'],1)


if __name__=='__main__':unittest.main()
