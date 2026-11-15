"""Data-only original delivery update, no H/native/fit calls."""
from pathlib import Path
import os,json,datetime,hashlib,fcntl,stat,tempfile,subprocess,shlex,base64,ast,re
B=Path('/home/yuanyue/main/work/data-team');M=Path(__file__).resolve().parent;T=B/'manifests/T-COMPLEX-observability-study-46308-20261115-v1';S=Path('/home/yuanyue/main/汇总/各小组进展汇总.md');now=datetime.datetime.now().astimezone().isoformat();sha=lambda b:hashlib.sha256(b).hexdigest()
assert sha(Path('/home/yuanyue/main/汇总/各小组下一步研究计划.md').read_bytes())=='26b67d55d0d8d8a6312ac8e19ec85de50f3f753bc8e503aaef8fb0eed20a7e9d'
idx=json.loads((M/'closed05to08-original-release-index.json').read_bytes());assert len(idx['releases'])==4;rows=[];members=0
for ordinal,v in zip((5,6,7,8),idx['releases']):
 D=B/'consumer-deliveries'/Path(v['release_path']).parent.name;r=json.loads((D/'release.json').read_bytes());assert r['ordinal']==ordinal and sha((D/'release.json').read_bytes())==v['release_sha256'];summary=r['actual_summary']
 for name,pin in r['files'].items():assert sha((D/name).read_bytes())==pin;members+=1
 rows.append(dict(ordinal=ordinal,release_sha256=v['release_sha256'],public_query_count=summary['public_query_count'],passed=summary['source_result_passed'],first_CLIMB_boundary=summary['first_CLIMB_boundary']))
assert [r['passed']for r in rows]==[True,False,False,False]and sum(r['public_query_count']for r in rows)==12
assert rows[0]['first_CLIMB_boundary']['status']=='FIRST_PREPARE_EXACT_PUBLIC_QUERY_BOUND'and all(r['first_CLIMB_boundary']['status']=='NO_CLIMB_JUDGMENT_RECORDED'for r in rows[1:])
s=S.read_text();i=s.index('## Data组');j=s.find('\n## ',i+1);j=len(s)if j<0 else j;body=s[i:j];peer=(s[:i].encode(),s[j:].encode());d=json.loads((M/'unstarted-suffix20-driver-status.json').read_bytes());assert not d['status'].startswith('STOPPED')and not d['global_stop']
line=f'''- **05—08正式原件已补齐（{now}，纯只读不重跑）：** releases **05=9115fcb3…、06=acc5be91…、07=5da55074…、08=70857034…**，原public query分母**5/2/3/2，共12**，非11或4独立留出；第5条首CLIMB PREPARE **97.760sim**，actual Observation SHA**0e788fc1…**精确绑定原journal line3890/原intent观测，不以97.8最近grid/未来帧代输入。06—08均无CLIMB judgment，features/label仍None，原settle超时/FF拒绝不补成CLIMB负例；4份原release全部**{members}小成员**逐SHA核回，完整原journal链再核、四branch前后不变。raw/MJB/大数组/视频仍新端，本机仅少数原query/小metadata；不写H、不造新query/标签或调用fit。入口 `{M}/closed05to08-original-release-index.json`。\n'''
p=body.index('- **正式原件和历史不回写');body=body[:p]+line+body[p:];body=body.replace('bulk01—04 release已逐成员SHA核完','bulk01—08 release已逐成员SHA核完').replace('02—04新增11实际public queries、连01共16，非16独立样本；04/06不是CLIMB负例','01—08已交28个实际原public queries（前01—04的16＋本05—08的12），不是28独立场景；04/06/07/08未到CLIMB，不是CLIMB负例')
body=body.replace('01—04原件索引','01—08原件索引').replace('`'+str(M/'closed02to04-original-release-index.json')+'`及01独立release','`'+str(M/'closed02to04-original-release-index.json')+'`、`'+str(M/'closed05to08-original-release-index.json')+'`及01独立release')
# Refresh only an as-of finite-driver snapshot, never write its H or controls.
body=re.sub(r'PID\d+、snapshot `[^`]+`，zero派\d+/main派\d+/终态\d+（\d+PASS/\d+失败），余\d+条完全未启动；当前 `[^`]+` / \*\*[^*]+\*\*',f"PID{d['driver_PID']}、snapshot `{d['at']}`，zero派{d['zero_dispatches']}/main派{d['main_dispatches']}/终态{d['closed_main']}（{d['conditional_PASS']}PASS/{d['closed_native_failed']}失败），余{d['remaining_not_started']}条完全未启动；当前 `{d['current_scope']}` / **{d['current_phase']}**",body,count=1)
entry='## 当前最高执行入口：用户箱参数授权已消费，V4五组接缝准备；bulk01—08原件齐、既有driver继续\n'+body.split('\n',1)[1]+'\n';proof=[];remote=[];p=B/'manifests/T-COMPLEX-01-full-program-46308-20261115-v1/publish_full_program_current.py';tree=ast.parse(p.read_text());node=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='update');src=ast.get_source_segment(p.read_text(),node).replace('.before-full-program-A-main','.before-closed05to08-release').replace('.T-full-A-','.closed05to08-release-').replace('（北京时间；T完整程序A自身zero/cold通过、唯一main实派，B0/0；不是已完成对照）。','（北京时间；bulk01—08原件齐，现有driver继续；箱参数授权已消费，V4真实main仍0）。');exec(compile(src,'Data-only05to08-updater','exec'),globals());update(S,True);assert S.read_bytes().startswith(peer[0])and S.read_bytes().endswith(peer[1])
for name in('STATUS.md','AGENTS.md','README.md'):update(B/name)
for folder in(M,T):
 with(folder/'README.before-closed05to08-release.md').open('xb')as f:f.write((folder/'README.md').read_bytes())
 (folder/'README.md').write_text('# bulk01—08原件已交，原driver继续；箱参数授权已消费\n'+body.split('\n',1)[1])
code=next(ast.literal_eval(n.value)for n in tree.body if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='code'for t in n.targets));r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','-p','46308','root@180.97.68.228','/mnt/yuanyue/data-team/env-native-v1/bin/python -I -B -c '+shlex.quote(code)],input=json.dumps(remote),capture_output=True,text=True,timeout=90)
for suffix,text in [('stdout',r.stdout),('stderr',r.stderr)]:
 with(M/('closed05to08-entry-mirror.'+suffix)).open('x')as f:f.write(text)
with(M/'closed05to08-publication-CAS-peer-proof.json').open('x')as f:json.dump(dict(at=now,proof=proof,remote_exit=r.returncode,all_non_Data_peer_bytes_preserved=True,H_not_written=True,no_native_source_count_cap_or_original_change=True,all_small_members_SHA_checked=members,raw_datasets_not_downloaded=True),f,indent=2);f.write('\n')
assert r.returncode==0,r.stderr;print('Published original05..08, 12 actual public queries, missing labels None; peers/H preserved')
