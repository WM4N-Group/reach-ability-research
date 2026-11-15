"""Read-only decision accounting: alternatives are not proof of model necessity."""
from collections import Counter
import hashlib
import json


def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,allow_nan=False,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()


def read_journal(path):
    previous='0'*64;events=[]
    with open(path) as file:
        for sequence,line in enumerate(file):
            row=json.loads(line);claimed=row.pop('sha256')
            if row['sequence']!=sequence or row['previous_sha256']!=previous or digest(row)!=claimed:
                raise ValueError('Actual event-chain mismatch')
            previous=claimed;events.append(row['payload'])
    return events,previous


def summarize(events,report):
    choices=[x for x in events if x['event']=='ainav_tree_selection']
    admissions=[x for x in events if x['event']=='ainav_native_admitted']
    by_sha={x['receipt']['option_sha256']:x for x in admissions}
    receipts=[x['receipt'] for x in events if x['event']=='ainav_native_receipt']
    calls=[x for x in events if x['event']=='vlm_response']
    rows=[];counts=Counter()
    for choice in choices:
        h=choice['selected_option_sha256']
        if h not in by_sha:raise ValueError('Selected action lacks actual native admission')
        a=by_sha[h];option=a['option'];native_count=choice['admitted_first_action_count'];tree_count=choice['tree_first_action_count']
        if not 1<=tree_count<=native_count:raise ValueError('Invalid candidate/branch counts')
        category=('native_single_candidate' if native_count==1 else
            'multiple_native_but_single_tree_candidate' if tree_count==1 else 'multiple_current_tree_candidates')
        counts[category]+=1
        ends=[r for r in receipts if r['option_sha256']==h and r['status'] in ('succeeded','failed','hard_stop','budget_expired','protected_exit_complete')]
        if len(ends)>1:raise ValueError('Ambiguous terminal receipts')
        start=a['receipt']['time_s'];end=ends[0]['time_s'] if ends else report['sim_seconds']
        status=ends[0]['status'] if ends else 'no_terminal_receipt_before_global_stop'
        rows.append(dict(skill=option['skill'],target_ref=option['target_ref'],parameters=option['parameters'],
            start_sim_s=start,end_sim_s=end,duration_including_preparation_and_exit_s=end-start,
            actual_status=status,admitted_candidates=native_count,retained_tree_candidates=tree_count,
            decision_category=category,selected_option_sha256=h,time_budget_s=option['budget_s']))
    if len(choices)!=len(admissions):raise ValueError('Account separately for nonplanner admissions before attributing decisions')
    return dict(schema='ainav-measured-decision-attribution-v1',choices=len(choices),categories=dict(counts),decisions=rows,
        real_API_calls=len(calls),API_roles=dict(Counter(c['role'] for c in calls)),
        actual_API_wall_seconds=sum(c['elapsed_wall_s'] for c in calls),
        completed_skills=dict(Counter(r['skill'] for r in rows if r['actual_status']=='succeeded')),
        original_prefix_counted_as_model_decision=False,
        full_course_passed=report['full_course_passed'],actual_sim_seconds=report['sim_seconds'],wall_seconds=report['wall_seconds'],
        model_is_causally_necessary_established=False,vision_contribution_established=False,
        comparison_baseline_executed=False,generalization_established=False,
        meaning='Multiple candidate counts establish choices existed, NOT that VLM was necessary or superior.',
        physics_steps_by_audit=0,model_calls_by_audit=0)


def audit_support_frame_records(events):
    """Only command-height coordinates may differ between raw and actor inputs."""
    import math
    indices={191,198,205};checked=0
    for e in events:
        if e.get('event')!='registered_NAV_actual_actor_forward' or 'raw_world_frame_observation' not in e:continue
        raw=e['raw_world_frame_observation'];policy=e['observation'];height=e['policy_support_height_m']
        if len(raw)!=210 or len(policy)!=210 or not all(math.isfinite(v) for v in [*raw,*policy,height]):
            raise ValueError('Finite exact original 210D actor observations required')
        for i,(a,b) in enumerate(zip(raw,policy)):
            if i in indices:
                if abs(b-(a-height))>2e-7:raise ValueError('Policy support-height translation differs')
            elif a!=b:raise ValueError('Non-command observation field changed')
        checked+=1
    return dict(checked_actor_forwards=checked,translated_indices=sorted(indices),
        only_three_command_Z_fields_changed=True,measured_robot_state_fields_unchanged=True,
        physics_steps=0,actor_forwards=0)
