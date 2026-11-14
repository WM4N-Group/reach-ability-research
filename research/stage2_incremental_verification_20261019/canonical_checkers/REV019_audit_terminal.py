"""Independent terminal CPU/read-only adjudication. Never SDK/physics or source edit."""
import ast,datetime,hashlib,io,json,os,re,tarfile
from pathlib import Path
OUT=Path(__file__).resolve().parent
BASE=Path('/home/yuanyue/re-nav -piper-deploy/artifacts/go2-piper/sim2sim-current-20261008-a')
SRC=BASE/'wm07-old714-firststep-baseline-v001r3';RUN=BASE/(SRC.name+'-run-preparation-a')
RT=Path('/home/yuanyue/main/work/agent_team_runtime');CTRL=RT/'stage2_joint_gate_20261018/control_dev'
D=CTRL/'old714_v001r3_run_delivery.json';C=CTRL/'old714_v001r3_run_terminal_20261019'
read=lambda p:json.loads(Path(p).read_text());h=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
SID='sim2real-old714-firststep-v001r3-8101-env0';SHA='1fa50a30f008c00e7dde7199a86e283bf854f49e9bfe534fde6fde8295413a8a'
m=read(SRC/'package-manifest.json');p=read(SRC/'protocol.json');snap=read(OUT/'remote_snapshot.json');remote=OUT/'remote_originals'
assert h(SRC/'package-manifest.json')==snap['source_manifest_sha256']==SHA and all(snap['source_member_match'].values())
assert all(h(SRC/n)==s for n,s in m['files_sha256'].items())
with tarfile.open(RUN/'package.tar.gz','r:gz') as archive:
 assert set(archive.getnames())==set(m['files_sha256'])|{'package-manifest.json'}
 for n in archive.getnames():assert hashlib.sha256(archive.extractfile(n).read()).hexdigest()==(SHA if n=='package-manifest.json' else m['files_sha256'][n])
review_path=RT/'stage2_joint_gate_20261018/verification/s2_rev_018_old714_firststep_review/executable_v001r3/REVIEW.json'
auth_path=Path(p['main_authority']);sdk_path=Path(read(auth_path)['sdk_envelope_path'])
review=read(review_path);auth=read(auth_path);sdk=read(sdk_path)
assert h(review_path)==h(remote/'review.json')==auth['review_sha256']=='2fbc16d4a77091ac0b42e87bfdc8063a459f453aedcf7a6281f6ad0b105ad363'
assert h(auth_path)==h(remote/'authority.json')
assert h(sdk_path)==h(remote/'sdk.json')==review['sdk_envelope_sha256']==auth['sdk_envelope_sha256']=='6eb394d66fc9c12510cc848b4de6653ea513774dd2a258bf82adab4cf6e79a44'
assert auth['author']=='main' and auth['decision']=='RUN_AUTHORIZED' and auth['resources']==p['budget'] and auth['historical_baseline_only'] is True
assert review['decision']=='ACCEPTED_FOR_BASELINE_RUN' and review['blocking_findings']==[]
assert sdk['success'] is True and sdk['actual_SDK_AppLauncher'] is True
for obj in (review,auth,sdk):assert obj['source_manifest_sha256']==SHA
assert auth['source_id']==review['source_id']==SID
for k,n in [('result','SDK0env-result.original.json'),('log','SDK0env.original.log')]:assert h(remote/n)==sdk[k]['sha256']==h(sdk[k]['path'])
start=read(RUN/'start.json');term=read(RUN/'terminal.json');closure=read(RUN/'closure.json');process=read(remote/'process.json');progress=read(remote/'attempt/progress.json');log=(remote/'SDK.original.log').read_text()
assert h(RUN/'terminal.json')==h(remote/'terminal.json') and closure['terminal']==term
assert start['source_manifest_sha256']==term['source_manifest_sha256']==SHA and start['source_id']==term['source_id']==closure['source_id']==SID
assert start['remote_origin']==term['origin']==process['origin']
assert not (remote/'attempt/report.json').exists() and snap['files']['attempt/report.json']=={'exists':False}
assert term['returncode']==124 and term['error'] is None and term['environment_created'] is None and term['physics_steps'] is None
assert read(RUN/'dispatch-error.json')['error'].startswith('CalledProcessError(1,')
ledger_rows={};all_active={}
for name in p['local_ledgers']:
 rows=[json.loads(s) for s in Path(name).read_text().splitlines() if s.strip()]
 ledger_rows[name]=[x for x in rows if x.get('source_id')==SID]
 all_active[name]=sorted({x['source_id'] for x in rows if x.get('event')=='start'}-{x['source_id'] for x in rows if x.get('event')=='closed'})
rows=[x for values in ledger_rows.values() for x in values]
assert len(rows)==2 and sum(x['event']=='start' for x in rows)==sum(x['event']=='closed' for x in rows)==1
assert next(x for x in rows if x['event']=='start')==start and next(x for x in rows if x['event']=='closed')==closure
assert all(not x for x in all_active.values()) and closure['retries']==0
assert datetime.datetime.fromisoformat(auth['recorded_at'])<datetime.datetime.fromisoformat(start['at'])<datetime.datetime.fromisoformat(closure['at'])
# Current independent stop inventory; individual command statuses are mandatory.
for k in ('ps','gpu','apps'):assert snap['queries'][k]['returncode']==0 and not snap['queries'][k]['stderr'].strip()
pgid=process['pgid'];psrows=[x.split(None,4) for x in snap['queries']['ps']['stdout'].splitlines() if x.strip()]
assert all(len(x)==5 for x in psrows)
live_group=[x for x in psrows if int(x[2])==pgid and not x[3].startswith('Z')]
live_source=[x for x in psrows if not x[3].startswith('Z') and str(p['formal_remote_package']) in x[4] and 'remote-execute' in x[4]]
uuid=p['CUDA_VISIBLE_DEVICES'];apps=[line for line in snap['queries']['apps']['stdout'].splitlines() if uuid in line]
assert not live_group and not live_source and not apps and not any(snap['recorded_proc_present'].values())
assert ('1, '+uuid) in snap['queries']['gpu']['stdout']
# Read-only local owner and lock observation; do not acquire the shared lock.
owner_pid=read(C/'owner-ledger-final.json')['owner_pid'];owner_present=Path('/proc',str(owner_pid)).exists();lock_path=Path(p['local_owner_lock']);st=lock_path.stat()
locks=[]
for line in Path('/proc/locks').read_text().splitlines():
 for match in re.finditer(r'\b([0-9a-fA-F]+):([0-9a-fA-F]+):(\d+)\b',line):
  if (int(match[1],16),int(match[2],16),int(match[3]))==(os.major(st.st_dev),os.minor(st.st_dev),st.st_ino):locks.append(line)
assert not owner_present and not locks
# Exact persisted prefix and original code order: progress follows env.step return.
events=progress['events'];push=next(e for e in events if e['event']=='push_goal');supported=next(e for e in events if e['event']=='climb_supported');exit_events=[e for e in events if e.get('scope')=='climb_exit_body']
assert push['t']==11.02 and push['box_dx_m']>=.50 and supported['t']==305.98
assert progress['step']==15500 and progress['time_s']==310 and progress['phase']=='climb_exit' and progress['platform_feet']==4
assert events[-1]['event']=='four_support_body_plan' and events[-1]['t']==308 and events[-1]['accepted'] is True
assert not any(e['event']=='first_step_platform_reached' for e in events)
source=(SRC/'source/run_piper_integrated_course_v2.py').read_text();tree=ast.parse(source)
assert 'continue' not in [type(n).__name__.lower() for n in ast.walk(tree)]
assert source.index('observation, _, terminated, truncated, _ = environment.step(action)')<source.index('(args.output / "progress.json").write_text')<source.index('print(f"CHAIN_STEP=')
assert 'for step in range(int(args.max_seconds / env.step_dt)):' in source
checkpoints=[{'step':int(m[1]),'phase':m[2],'line':i} for i,line in enumerate(log.splitlines(),1) for m in [re.search(r'CHAIN_STEP=(\d+) phase=(\S+)',line)] if m]
assert checkpoints[-1]['step']==15500 and checkpoints[-1]['phase']=='climb_exit' and len(checkpoints)==32
assert 'Completed setting up the environment' in log and 'Physics step-size     : 0.005' in log and 'Environment step-size : 0.02' in log
assert 'timeout: the monitored command dumped core' in log and 'Mutex.cpp(103)' in log and 'Recursion not allowed' in log
assert 'status 124' in snap['queries']['timeout_help']['stdout']
cap=float(process['cmd'][process['cmd'].index('--kill-after=2')+1]);elapsed_at_cap_calculation=2340-6-cap
assert process['cmd'][:3]==['timeout','--signal=TERM','--kill-after=2'] and '--preserve-status' not in process['cmd']
assert term['elapsed_wall_s']<2340 and closure['wall_elapsed_s']<2400
mtime=lambda n:datetime.datetime.fromisoformat(snap['files'][n]['mtime_utc'])
progress_gap=(mtime('terminal.json')-mtime('attempt/progress.json')).total_seconds()
startup_marker_after_spawn=(mtime('attempt/audit-only-domain.json')-mtime('process.json')).total_seconds()
assert 0<startup_marker_after_spawn<60 and 0<progress_gap<60
predicted_deadline_marker=mtime('process.json')+datetime.timedelta(seconds=cap)
delivery=read(D);assert delivery['source_id']==SID and delivery['source_manifest_sha256']==SHA
assert h(C/'observed-terminal-summary.json')==delivery['terminal_summary_sha256'] and h(C/'evidence-manifest.json')==delivery['evidence_manifest_sha256']
for row in read(C/'remote-raw-index.original.json')['files']:
 if (remote/row['relative']).exists():assert h(remote/row['relative'])==row['sha256']==h(C/'originals'/row['relative'])
inputs=[D,auth_path,review_path,sdk_path,SRC/'package-manifest.json',RUN/'start.json',RUN/'terminal.json',RUN/'closure.json',RUN/'quiescence.json',RUN/'owner.json',RUN/'preflight.json',RUN/'dispatch-error.json',C/'observed-terminal-summary.json',C/'evidence-manifest.json',C/'owner-ledger-final.json',C/'quiescence.final.json']
result={'schema':'rev019-independent-old714-terminal-audit-v1','at':datetime.datetime.now().astimezone().isoformat(),'source_id':SID,'source_manifest_sha256':SHA,'binding_chain':{'source_local_remote_tar_members_match':True,'review_sha256':h(review_path),'main_authority_sha256':h(auth_path),'SDK_envelope_sha256':h(sdk_path),'remote_copies_match':True,'prestart_authority_chronology':True},'task_outcome':'FAILED_WALL_TIMEOUT_BASELINE_NOT_COMPLETED','scoring':{'attempts':1,'successes':0,'included_in_success_rate_denominator':True,'excluded_as_censored_or_unknown':False,'producer_censored_label_not_adopted':True},'starts':1,'retries':0,'ledger_closed':True,'active_ledgers_empty':True,'timeout_child_returncode':124,'remote_execute_ssh_returncode':1,'original_raw_report_present':False,'original_null_env_physics_not_rewritten':True,'environment_created_independently_observed':True,'actor_loading_and_forward_observed_via_original_execution_path':True,'physics_execution_positive':True,'last_persisted_progress':{k:progress[k] for k in ('step','time_s','phase','base','box_dx_m','box_speed_mps','base_speed_mps','hand_box_contact','platform_feet')},'minimum_environment_step_returns_inferred':15501,'minimum_step_return_inference_basis':'Unbroken range(0,...) loop without continue; progress and CHAIN_STEP printed after environment.step returned. Not exact final count or physical-substep counter.','exact_final_tick':None,'exact_final_sim_time_s':None,'exact_final_physics_substeps':None,'original_final_control_failure_classification':None,'last_persisted_checkpoint_is_not_exact_terminal_tick':True,'events':{'push_goal':push,'climb_supported':supported,'climb_exit_start':{k:v for k,v in exit_events[0].items() if k!='audit_only_planning_inputs'},'last_persisted_event':{k:v for k,v in events[-1].items() if k!='audit_only_planning_inputs'},'first_step_platform_reached_in_saved_prefix':False,'event_count':len(events),'checkpoint_count':len(checkpoints)},'timing':{'wall_clock_timezone':'UTC shown in artifacts; +08:00 is local Shanghai','start_at':start['at'],'closure_at':closure['at'],'local_total_wall_s':closure['wall_elapsed_s'],'remote_terminal_elapsed_s':term['elapsed_wall_s'],'core_cap_s':2340,'outer_cap_s':2400,'child_timeout_s':cap,'remote_origin':term['origin'],'cap_calculation_elapsed_since_origin_s':elapsed_at_cap_calculation,'planned_soft_timeout_since_origin_s':2334,'process_marker_mtime':snap['files']['process.json']['mtime_utc'],'initialized_domain_audit_mtime':snap['files']['attempt/audit-only-domain.json']['mtime_utc'],'domain_audit_after_process_marker_s':startup_marker_after_spawn,'last_progress_mtime':snap['files']['attempt/progress.json']['mtime_utc'],'last_progress_to_terminal_file_s':progress_gap,'approximate_soft_deadline_from_process_marker':predicted_deadline_marker.isoformat(),'deadline_mtime_estimate_not_exact_signal_receipt':True,'log_assertion_at':'2026-10-19T10:55:22Z','log_assertion_kit_uptime_ms':2327248,'per_checkpoint_wall_timestamps_available':False},'mechanism':{'initialization_blockage_ruled_out_for_this_attempt':True,'execution_progressed_to_climb_exit':True,'GNU_timeout_wall_deadline_reached':True,'assertion_at_stop_boundary_observed':True,'assertion_preceded_timeout_or_caused_timeout':'unknown','assertion_caused_by_TERM':'not_proven','last_46s_local_stall':'not_proven; log checkpoints are 500 steps = 10 sim seconds, no per-checkpoint wall profile','old_success_disproved':False,'would_finish_with_more_wall':'not_proven','GPU_bad_state_warning_explains_runtime':'not_proven'},'stop':{'fresh_independent_remote_at':snap['at'],'recorded_pid_present':snap['recorded_proc_present'],'owned_live_group':live_group,'live_source_processes':live_source,'GPU1_compute_apps':apps,'mandatory_queries_succeeded':True,'owner_pid':owner_pid,'local_owner_currently_present':owner_present,'shared_lock_matching_proc_locks':locks,'shared_lock_acquisition_performed':False,'lock_release_supported_by_owner_exit_and_proc_locks':True,'original_quiescence_before_closure_retained':True},'next_action_boundary':'Main only; prioritize executed-stage wall/performance diagnosis rather than another initialization claim. No next RUN/source authorized and no promise that additional wall gives success.','source_or_originals_modified':False,'SDK_or_physics_started_by_verification':False,'input_sha256':{str(x):h(x) for x in inputs},'remote_original_sha256':{str(f.relative_to(remote)):h(f) for f in remote.rglob('*') if f.is_file()}}
(OUT/'terminal_audit_result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:result[k] for k in ['task_outcome','scoring','binding_chain','starts','retries','environment_created_independently_observed','physics_execution_positive','last_persisted_progress','timing','mechanism','stop']},indent=2))
