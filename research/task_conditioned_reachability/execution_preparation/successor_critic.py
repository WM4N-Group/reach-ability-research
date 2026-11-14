"""Restricted CPU high-level critic training on future NEW authorized data only.

No actor/WM/physics, automatic collection, broad file discovery or old-data fit.
Success score is UNCALIBRATED and never native feasibility. Cost regressions use
only observed successful endpoints; native failures keep their separate label,
censoring and all spending. Group splits are fixed before fit, never per-frame.
"""
import argparse
import datetime as dt
import hashlib
import json
import math
import time
from pathlib import Path
from .successor_aware_choice import need,number,pin,digest

PURPOSE='NEW_PREREGISTERED_HIGH_LEVEL_SUCCESSOR_CRITIC'
HISTORICAL_SCOPE_FRAGMENTS=('stageB-','stow-choice','full-host-continuation-20261113','first-ground-push-20261113')
SPLITS=('TRAIN','CALIBRATION','VALIDATION')


def timestamp(value):
    need(type(value) is str,'Actual timezone-aware registration/acquisition time')
    parsed=dt.datetime.fromisoformat(value)
    need(parsed.tzinfo is not None,'Timezone-aware provenance, not model feature')
    return parsed


def validate_dataset(data, authorization, protocol):
    need(authorization.get('user_reply')=='运行' and
         authorization.get('permission_for_old_data_relabelling') is False and
         'small high-level candidate-conditioned successor success and duration model' in authorization.get('approved_scope',[]),
         'Explicit restricted user grant, not general research budget')
    cutoff=timestamp(authorization['at'])
    need(data.get('purpose')==PURPOSE and data.get('origin')=='FUTURE_NEW_CAPTURE' and data.get('training_allowed') is True,
         'Only newly captured data under explicit training purpose; audit data never relabelled')
    need(data.get('authorization_sha256')==protocol['authorization_sha256'], 'Same user-grant binding')
    need(data.get('preregistration_sha256')==digest(protocol),'Same frozen collection/model protocol')
    need(data.get('feature_profile_sha256')==protocol['feature_profile_sha256'],'Physical-only feature profile')
    if 'feature_extractor_sha256' in protocol:
        need(data.get('feature_extractor_sha256')==protocol['feature_extractor_sha256'],'Exact physical feature extractor source, not a relabelled table')
    need(protocol.get('qualified_entry_condition_family') is True,
         'Qualified legal entry-state variation required; changing seeds alone is not an information question')
    registered=timestamp(data['preregistered_at'])
    need(registered>=cutoff,'Future preregistration only, not retrospective audit conversion')
    rows=data.get('rows');need(type(rows) is list and 1<=len(rows)<=512,'No new authorized rows available or CPU row cap exceeded')
    unreached=data.get('unreached_decision_attempts',[])
    need(type(unreached) is list and data.get('all_closed_attempts_accounted') is True and
         type(data.get('closed_attempt_count')) is int and
         data['closed_attempt_count']==len(rows)+len(unreached),'All acquisition/prefix failures must remain in the attempt denominator')
    scopes=set()
    for attempt in unreached:
        need(type(attempt.get('scope_id')) is str and bool(attempt['scope_id'].strip()) and not any(s in attempt['scope_id'] for s in HISTORICAL_SCOPE_FRAGMENTS),
             'New predecision scope, not a closed historical attempt')
        need(attempt['scope_id'] not in scopes,'Each closed physical scope counted once across reached/unreached attempts')
        scopes.add(attempt['scope_id'])
        need(attempt.get('data_purpose')==PURPOSE and attempt.get('old_audit_ancestor') is False and
             pin(attempt.get('source_result_sha256')),'New source-bound predecision attempt, not fabricated features')
        need(registered<=timestamp(attempt['captured_at'])<=dt.datetime.now(dt.timezone.utc),'New predecision attempt clock')
        need(attempt.get('decision_reached') is False and attempt.get('physical_features') is None,
             'No-decision attempts never receive invented predictor input or labels')
        need(attempt.get('spent_sim_s') is None or number(attempt['spent_sim_s']) and attempt['spent_sim_s']>=0,'Retain acquisition/prefix costs')
    names=protocol['feature_profile']['names'];need(len(names)==48,'Exact existing physical feature view')
    grouped={};groups={};seen=set();classes=set();state_signatures=set()
    for r in rows:
        need(type(r['sample_id']) is str and r['sample_id'] not in seen,'Unique new sample')
        seen.add(r['sample_id']);scope=r['scope_id']
        need(type(scope) is str and bool(scope.strip()) and not any(s in scope for s in HISTORICAL_SCOPE_FRAGMENTS),
             'Closed/historical scopes cannot become training samples')
        need(scope not in scopes,'Each closed physical scope counted once across reached/unreached attempts')
        scopes.add(scope)
        need(r.get('data_purpose')==PURPOSE and r.get('old_audit_ancestor') is False and
             r.get('guard_and_stream_integrity_verified') is True,
             'New purpose, data ancestry and original stream closure required')
        need(all(pin(r.get(k)) for k in ('source_result_sha256','source_feature_event_sha256','condition_binding_sha256')),
             'Exact recorded result/causal feature event/condition bindings')
        captured=timestamp(r['captured_at']);need(registered<=captured<=dt.datetime.now(dt.timezone.utc),'Fresh post-preregistration acquisition, no future timestamps')
        split=r['split'];group=r['condition_binding_sha256']
        need(split in SPLITS,'Predeclared group split only')
        need(group not in grouped or grouped[group]==split,'Same condition/ancestor group cannot cross train/calibration/validation')
        grouped[group]=split;groups.setdefault(split,set()).add(group)
        x=r['physical_features'];need(type(x) is list and len(x)==48 and all(number(v) and abs(v)<=1e6 for v in x),
            'Complete finite causal physical features, no IDs/labels or silent missing-value imputation')
        need(0<=x[-1]<=.100001,'Fresh measured age, not absolute time/skill clock')
        outcome=r['outcome'];need(outcome in ('SUCCESS','NATIVE_GUARD_FAILURE','CENSORED'),'Separate literal task failure and resource censoring')
        current=r.get('current_READY_s');full=r.get('full_success_s')
        cap=protocol['physical_limits']['max_sim_s']
        need(current is None or number(current) and 0<=current<=cap,'Current endpoint or explicit missing')
        need(current is None or r.get('READY_source_verified') is True,'Recorded READY source, not inferred arrival')
        if outcome=='SUCCESS':
            need(number(full) and current is not None and current<=full<=cap and r.get('successful_task_endpoint_verified') is True,'Success has nested actual current/full endpoints')
        else:
            need(full is None,'Failure/censoring duration is NOT successful completion cost')
        if outcome=='NATIVE_GUARD_FAILURE':need(r.get('native_guard_failure_verified') is True,'Do not turn collector/resource errors into native failures')
        spent=r.get('spent_sim_s');need(spent is None or number(spent) and spent>=0,'Keep failure/censoring cost, missing is not zero')
        if split=='TRAIN' and outcome!='CENSORED':classes.add(outcome=='SUCCESS')
        if split=='TRAIN':state_signatures.add(tuple(round(v,6) for v in x[2:47]))
    for split,minimum in protocol['minimum_groups'].items():
        need(len(groups.get(split,set()))>=minimum,'Insufficient predeclared independent-condition groups: '+split)
    need(len(classes)==2,'No observed success/failure class variation; do not mine seeds/retry until failure')
    need(len(state_signatures)>=2,'No observed entry-state variation beyond action labels/metadata')
    return rows



def attempt_spending(data):
    """All admitted attempts, including prefixes which never reach the decision.

    A missing charge is unknown, never an observed zero. Report observed sums as
    lower bounds until both populations have complete spending. These are sim
    charges only; neither successful completion costs nor wall/GPU accounting.
    """
    def summarize(attempts):
        known=[r['spent_sim_s'] for r in attempts if r.get('spent_sim_s') is not None]
        missing=len(attempts)-len(known)
        total=math.fsum(known)
        need(number(total),'Finite aggregate attempt spending')
        return dict(attempts=len(attempts),known_spent_sim_s=total,
                    missing_spend_attempts=missing,spend_complete=missing==0)
    reached=summarize(data['rows'])
    unreached=summarize(data.get('unreached_decision_attempts',[]))
    overall=summarize(data['rows']+data.get('unreached_decision_attempts',[]))
    return dict(population='ALL_CLOSED_ATTEMPTS',reached_decision=reached,
                unreached_decision=unreached,**overall,
                known_spend_is_lower_bound=not overall['spend_complete'],
                missing_spend_imputed=False)


def _sigmoid(z):
    return 1./(1.+math.exp(-z)) if z>=0 else math.exp(z)/(1.+math.exp(z))


def _solve(matrix,rhs):
    a=[list(row)+[y] for row,y in zip(matrix,rhs)];n=len(rhs)
    for i in range(n):
        pivot=max(range(i,n),key=lambda k:abs(a[k][i]));need(abs(a[pivot][i])>1e-12,'Numerically singular regularized fit')
        a[i],a[pivot]=a[pivot],a[i];scale=a[i][i];a[i]=[x/scale for x in a[i]]
        for j in range(n):
            if j==i:continue
            scale=a[j][i]
            a[j]=[u-scale*v for u,v in zip(a[j],a[i])]
    return [row[-1] for row in a]


def _ridge(x,y,penalty=1.):
    if not y:return None
    size=len(x[0]);matrix=[[sum(row[i]*row[j] for row in x)+(penalty if i==j and i else 0.)
                          for j in range(size)] for i in range(size)]
    return _solve(matrix,[sum(row[i]*value for row,value in zip(x,y)) for i in range(size)])


def _fit_heads(rows):
    """Small deterministic math core; production must call validate_dataset FIRST.

    Software unit tests may exercise this core on explicit abstract fixtures.
    Such in-memory fits are NOT research datasets or exportable native models.
    """
    train=[r for r in rows if r['split']=='TRAIN'];need(train,'Training groups only')
    n=len(train);size=len(train[0]['physical_features'])
    mean=[sum(r['physical_features'][i] for r in train)/n for i in range(size)]
    scale=[max(math.sqrt(sum((r['physical_features'][i]-mean[i])**2 for r in train)/n),1e-6) for i in range(size)]
    vector=lambda r:[1.]+[(v-m)/s for v,m,s in zip(r['physical_features'],mean,scale)]
    known=[r for r in train if r['outcome']!='CENSORED'];x=[vector(r) for r in known];y=[float(r['outcome']=='SUCCESS') for r in known]
    weights=[0.]*(size+1)
    for _ in range(300):
        errors=[_sigmoid(sum(a*b for a,b in zip(row,weights)))-label for row,label in zip(x,y)]
        gradient=[sum(e*row[j] for e,row in zip(errors,x))/len(x)+(0.01*weights[j] if j else 0.) for j in range(size+1)]
        weights=[w-.1*g for w,g in zip(weights,gradient)]
    current=[r for r in train if r.get('current_READY_s') is not None]
    success=[r for r in train if r['outcome']=='SUCCESS']
    return dict(mean=mean,scale=scale,success_weights=weights,
        current_time_weights=_ridge([vector(r) for r in current],[r['current_READY_s'] for r in current]),
        full_success_time_weights=_ridge([vector(r) for r in success],[r['full_success_s'] for r in success]),
        fit_rows=len(train),success_classifier_fit_rows=len(known),current_time_fit_rows=len(current),successful_full_time_fit_rows=len(success),
        baseline_success_score=sum(y)/len(y),
        baseline_current_time_mean_s=None if not current else sum(r['current_READY_s'] for r in current)/len(current),
        baseline_successful_full_time_mean_s=None if not success else sum(r['full_success_s'] for r in success)/len(success),
        model_kind='FIXED_REGULARIZED_LOGISTIC_SCORE_AND_RIDGE_CONDITIONAL_TIMES',
        success_score_is_calibrated_probability=False,deployment_qualified=False)


def predict_offline(model,features):
    need(type(features) is list and len(features)==len(model['mean']) and all(number(v) for v in features),'Complete known physical view only')
    x=[1.]+[(v-m)/s for v,m,s in zip(features,model['mean'],model['scale'])]
    dot=lambda w:sum(a*b for a,b in zip(x,w))
    return dict(uncalibrated_success_score=_sigmoid(dot(model['success_weights'])),
        conditional_current_time_s=None if model['current_time_weights'] is None else max(0.,dot(model['current_time_weights'])),
        conditional_successful_full_time_s=None if model['full_success_time_weights'] is None else max(0.,dot(model['full_success_time_weights'])),
        complete_successor_feasibility='UNKNOWN',execution_authorized=False)



def _score_diagnostics(row_scores):
    """Fixed raw-score diagnostic, NOT calibrated probability or admission.

    This 0.5 diagnostic is conventional logistic sign classification only.
    It is not chosen from heldout/audit outcomes, and cannot change the model,
    UNKNOWN deployment feasibility, or the original native execution gates.
    Resource censoring is excluded from both classes, never treated as failure.
    """
    known=[(r,score) for r,score in row_scores if r['outcome']!='CENSORED']
    successes=sum(r['outcome']=='SUCCESS' for r,_ in known)
    failures=len(known)-successes
    missed_failures=sum(r['outcome']=='NATIVE_GUARD_FAILURE' and score>=.5 for r,score in known)
    refused_successes=sum(r['outcome']=='SUCCESS' and score<.5 for r,score in known)
    predicted_success=sum(score>=.5 for _,score in known)
    return dict(raw_uncalibrated_score_threshold=.5,threshold_is_deployment_rule=False,
        known_outcome_rows=len(known),censored_excluded=len(row_scores)-len(known),
        native_failures=failures,successes=successes,
        native_failures_scored_success=missed_failures,
        native_failure_miss_rate=None if not failures else missed_failures/failures,
        actual_successes_scored_failure=refused_successes,
        success_false_refusal_rate=None if not successes else refused_successes/successes,
        predicted_success_rows=predicted_success,
        failure_fraction_among_scored_success=None if not predicted_success else missed_failures/predicted_success,
        diagnostic_is_not_calibration_or_qualified_safety_test=True)


def fit_and_evaluate(data,authorization,protocol):
    rows=validate_dataset(data,authorization,protocol)
    spending=attempt_spending(data)
    model=_fit_heads(rows);metrics={}
    for split in ('CALIBRATION','VALIDATION'):
        part=[r for r in rows if r['split']==split];known=[r for r in part if r['outcome']!='CENSORED']
        predictions=[(r,predict_offline(model,r['physical_features'])) for r in part]
        full_errors=[abs(p['conditional_successful_full_time_s']-r['full_success_s']) for r,p in predictions if r['outcome']=='SUCCESS']
        current_errors=[abs(p['conditional_current_time_s']-r['current_READY_s']) for r,p in predictions
                        if r.get('current_READY_s') is not None and p['conditional_current_time_s'] is not None]
        baseline_current_errors=[abs(model['baseline_current_time_mean_s']-r['current_READY_s']) for r in part
                                 if r.get('current_READY_s') is not None and model['baseline_current_time_mean_s'] is not None]
        unknown=sum(p['complete_successor_feasibility']=='UNKNOWN' for _,p in predictions)
        log_losses=[];baseline_log_losses=[];baseline_full_errors=[]
        for r,p in predictions:
            if r['outcome']=='CENSORED':continue
            prob=min(1.-1e-12,max(1e-12,p['uncalibrated_success_score']));label=r['outcome']=='SUCCESS'
            log_losses.append(-math.log(prob if label else 1.-prob))
            base=min(1.-1e-12,max(1e-12,model['baseline_success_score']))
            baseline_log_losses.append(-math.log(base if label else 1.-base))
        for row in part:
            if row['outcome']=='SUCCESS':baseline_full_errors.append(abs(model['baseline_successful_full_time_mean_s']-row['full_success_s']))
        metrics[split]=dict(rows=len(part),groups=len({r['condition_binding_sha256'] for r in part}),
            successes=sum(r['outcome']=='SUCCESS' for r in part),guard_failures=sum(r['outcome']=='NATIVE_GUARD_FAILURE' for r in part),
            censored=sum(r['outcome']=='CENSORED' for r in part),
            raw_score_diagnostic=_score_diagnostics([(r,p['uncalibrated_success_score']) for r,p in predictions]),
            train_only_constant_score_diagnostic=_score_diagnostics([(r,model['baseline_success_score']) for r in part]),
            full_successor_feasibility_prediction_rows=len(predictions),
            full_successor_feasibility_UNKNOWN_rows=unknown,
            full_successor_feasibility_UNKNOWN_fraction=None if not predictions else unknown/len(predictions),
            qualified_native_or_execution_PASS_predictions=0,
            current_READY_time_MAE_s=None if not current_errors else sum(current_errors)/len(current_errors),
            train_only_mean_baseline_current_READY_time_MAE_s=None if not baseline_current_errors else sum(baseline_current_errors)/len(baseline_current_errors),
            uncalibrated_log_loss=None if not log_losses else sum(log_losses)/len(log_losses),
            successful_full_time_MAE_s=None if not full_errors else sum(full_errors)/len(full_errors),
            train_only_constant_baseline_log_loss=None if not baseline_log_losses else sum(baseline_log_losses)/len(baseline_log_losses),
            train_only_mean_baseline_full_time_MAE_s=None if not baseline_full_errors else sum(baseline_full_errors)/len(baseline_full_errors),
            used_for_parameter_fit=False,statistical_or_native_qualification_claimed=False)
    return dict(status='OFFLINE_FIT_COMPLETE_NOT_DEPLOYMENT_QUALIFIED',model=model,heldout_metrics=metrics,
        all_rows_and_failures_retained=len(rows),total_closed_attempts=data['closed_attempt_count'],
        unreached_decision_attempts=data.get('unreached_decision_attempts',[]),
        evaluation_population='Reached the preregistered decision; predecision failures separately retained, not fictitious model rows',
        censored_rows=sum(r['outcome']=='CENSORED' for r in rows),
        attempt_spending=spending,
        known_spent_sim_s=spending['known_spent_sim_s'],
        missing_spend_attempts=spending['missing_spend_attempts'],
        missing_spend_rows=spending['reached_decision']['missing_spend_attempts'],
        successful_time_is_conditional_not_failure_penalty=True,post_validation_tuning_allowed=False,execution_authorized=False)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('authorization','protocol','dataset','output'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();started=dt.datetime.now(dt.timezone.utc).isoformat();wall=time.perf_counter();auth_raw=args.authorization.read_bytes();authorization=json.loads(auth_raw)
    protocol=json.loads(args.protocol.read_bytes())
    need(hashlib.sha256(auth_raw).hexdigest()==protocol['authorization_sha256'],'Exact explicit user grant')
    if not args.dataset.exists():
        result=dict(status='WAITING_NEW_AUTHORIZED_DATA_NO_FIT',expected_new_dataset=str(args.dataset.resolve()),
            qualified_new_training_rows=0,model_written=False,training_started=False,
            condition_family_qualified=protocol['qualified_entry_condition_family'],
            missing=['New training-purpose preregistration and original-owner-qualified entry-state conditions',
                     'New Data-collected causal physical features and source-bound labels in fixed group splits'],
            old_audit_data_fallback_allowed=False,physical_dispatch=False)
    else:
        need(not args.dataset.is_symlink() and args.dataset.stat().st_size<=10*1024**2,'Explicit small regular new-dataset file, not a redirected archive')
        try:
            result=fit_and_evaluate(json.loads(args.dataset.read_text()),authorization,protocol)
            result['model_written']=True
            result['source_dataset_sha256']=hashlib.sha256(args.dataset.read_bytes()).hexdigest()
        except ValueError as error:
            result=dict(status='DATA_ADMISSION_REFUSED_NO_FIT',reason=str(error),model_written=False,training_started=False,physical_dispatch=False)
    result.update(training_entry_executed=True,started_at=started,entry_wall_s=time.perf_counter()-wall,
        learner_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        authorization_sha256=hashlib.sha256(auth_raw).hexdigest(),protocol_sha256=digest(protocol),
        no_actor_WM_GPU_or_physics_calls=True)
    with args.output.open('x') as stream:json.dump(result,stream,ensure_ascii=False,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps({k:result[k] for k in ('status',) if k in result},ensure_ascii=False))


if __name__=='__main__':main()
