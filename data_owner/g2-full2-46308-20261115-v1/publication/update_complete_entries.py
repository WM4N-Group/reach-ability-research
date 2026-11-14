from pathlib import Path
import os,json,datetime,hashlib,fcntl,tempfile,stat,re,ast,subprocess,shlex,base64
B=Path('/home/yuanyue/main/work/data-team');M=Path(__file__).resolve().parent;S=Path('/home/yuanyue/main/汇总/各小组进展汇总.md');now=datetime.datetime.now().astimezone().isoformat();sha=lambda b:hashlib.sha256(b).hexdigest();h=json.loads((B/'registry/handoff_46308_current_status_20261115.json').read_bytes());assert not h['active_g2_full2_scope']['active'];assert h['g2_full2_cohort']['status']=='CLOSED_DEV_SOURCE_GATE_ONE_CHAIN_PASS_ONE_PREDECESSOR_ERROR_NO_RETRY'
D=B/'consumer-deliveries/AINAV-DATA-G2-46308-FULL2-TWO-PREFIX-ACTUAL-20261115-v1';v=json.loads((D/'actual-cohort-summary.json').read_bytes());assert v['main_attempts']==2 and v['whole_chain_PASS']==v['whole_chain_execution_error']==1;T=B/'manifests/g2-full1-source-intake-20261115-v1';source=json.loads((T/'SOURCE_INTAKE_NO_SCOPE_NO_DISPATCH.json').read_bytes());assert not source['scope_ids_allocated']and not source['physical_dispatch']
body=f'''更新：{now}（北京时间；G2 full-2两唯一main均closed/九流cold：left PASS、right原PUSH卸载异常且未达CLIMB；完整2attempt/7原query交付，转一次具体full-1新源准入准备）

**当前状态**
- **本gate完整结果为1成功＋1前驱执行异常，不是两成功或仍在途。** left exact3 PASS：119.000sim/23800步/1191 RGBD及review帧、5options/10literal回执，first CLIMB PREPARE95.605sim/frame-000004。right在64.170sim由原moving_push_exit→unload_reference_binding→reconciled_unload抛 **reconciled_reference_FF_intersection_empty**；12834实际记录command步、642帧、2options/3回执；PUSH53.230sim只有started，**无terminal回执，未达CLIMB请求/首次PREPARE**。完整链FAILED_NO_RETRY，但不能伪造PUSH failed receipt或把未执行CLIMB标负类/补准备帧/成功成本。
- **两支原流均完整可审，不以cold PASS洗成native成功：** 九流cold全过，FIFO/PD/hardclip复现误差0，同各自zero/main numeric93869e1a…、teardown无误；right legacy失败result原本没有task_physics_steps字段，保None，command数12834从原cold明确另报。首次只读发布器因缺字段KeyError留下partial/stdio；增量v2按SHA验证相同已拷原件后完成元数据，未改raw result/ledger、未重采或重跑物理。
- **完整原始交付与真实费用已齐：** 组合release **9be124b3…** 引left3b5e9a9f…/right68339f4c…两个原子包，原query **5＋2＝7**，必要public/metadata约1.75MB，source bytes/clock/实际Host Observation语义SHA/record-chain不变；完整attempt/unreached/censor在组合索引，evidence可含私有后果仅审计、整包不入模型/fit。两scope含自身zero/4aux共 **209.190sim / 1287.339338ledger wall / 290578607bytes独立scope高水位和**；right77.180sim/450.701685wall/116112415bytes为失败已花，不冒成功cost/全项目费用。旧失联UNKNOWN/新v1 XML失败/G1原账另保。
- **权威已收束：** 两支zero/main各1已耗、active=false/dispatch=null，cohort明确ONE_CHAIN_PASS_ONE_PREDECESSOR_ERROR_NO_RETRY；远端H SHA **a8cd8a05…**已CAS镜像，本组native进程0/规范锁释放（不是未来lease）。fresh整个Data根19886205440bytes/40GiB，provider quota未知。G1/旧scope不重开，不换seed/goal补full-2 right，不改原Actor/init/4301/12N/4s/stop/QP/FIFO/FF门或已冻结helper。

**正在做／下一项／独立备选**
- **G2下一有具体源码源，不再泛等第三scene：** 已接AINav03:13给的原registered **full-1 left单prefix**选项，另做无world源准入：原protocol canonical **7492762c…**/源pins/精确请求与device-only overlay核合。它lane=-1.8/PUSH(2.3,-1.8,0)/NAV_y=-1.6500000000000001；原C质量1.0kg、mu.3（不是full-2/4的.5kg/.6），明确是多因素registered场景，非几何-only。**现仅SOURCE_INTAKE、0scope/0authority/0dispatch**；现full-2 helper仍拒绝full-1，绝不放宽或热改。下一新独立Data caller/事前范围/完整freeze/自身zero/fresh lease后至多1main；保失败/缺PREPARE，不借新ID追跑full-2，不重复问预算/已授权高层用途。
- **评价/训练接续：** 开发组已独立消费full-2 left真实公开差；现在可直接消费right失败与缺CLIMB分母补全四格，不需Data代评价或等回执才能发布。full-2只有一个scene且入口覆盖有限，不把prefix/arm/reset伪拆TRAIN/CAL/VAL；full-1尚未动态/信息资格，正式新用途/whole-scene split/样本功效及停止规则未齐，训练行/fit仍0。本批不是长期完成，按合格新源/新cohort→G3critic及简单基线→G4三策略→G5多决策/未见→G6继续。
- **边界保持：** center/upper-entry旧备选仍派发前暂停0scope/0main，不与新源并跑。科学21/3650/strict3/TEST0与原Stage-B两PASS/一stop保持；G1/G2 DEV/旧audit/GT不fit，Actor/WM/DINO/真机/第二owner不开，自动化未改；仅代码/小必要元数据在本地与GitHub，大数组/环境/权重/视频留46308。

**入口**：[G2完整两attempt原件]({D}/release.json) · [实际结果与费用]({D}/actual-cohort-summary.json) · [失败/未达CLIMB分母]({D}/attempts-and-unreached-censor.json) · [谱系及发布修正]({D}/all-attempts-lineage-and-costs.json) · [full-1源准入、未派发]({T}/SOURCE_INTAKE_NO_SCOPE_NO_DISPATCH.json) · [当前权威镜像]({B}/registry/handoff_46308_current_status_20261115.json) · [G2详细]({M}/README.md)
'''
banner=f'''## 当前最高执行入口：G2 full-2两支closed，保一PASS/一原PUSH异常；转具体full-1新源准备（{now}）

**当前native队列0/规范锁已释放，G2 full-2 left/right各zero1/main1已耗，均closed、dispatch=null，禁止重跑。** left exact3 PASS，119.000sim/23800步；right64.170sim/12834实际command步，在原PUSH卸载reference发生reconciled_reference_FF_intersection_empty；只有PUSH started无terminal回执，CLIMB未请求/first PREPARE缺失，不作CLIMB负标签或补帧。两支九流cold PASS只证记录完整。组合release9be124b3…保2attempt/7原query、费用/censor/原字节时钟；`{D}/release.json`。

真实owner仍01a1d3aa-a0d5-7de0-b886-9d92ed5f1480；当前权威active_g2_full2_scope/g2_full2_cohort，H已收束镜像a8cd8a05…。当前计算仅46308独立根/GPU1 UUID6d66aa68…/device51两规范锁inode3428459217、3428459218；新执行仍自身新程序/zero/fresh lease。原Actor/init/4301/私有Expat2.8.1单进程loader/全部原门不改。

**下一具体源已接，但尚无新scope/派发：** AINav原registered full-1 left单prefixsource，protocol7492762c…已CPU source核合；明确C质量1kg/mu.3与几何/目标变化，不冒geometry-only，不修改仍拒绝full-1的旧full-2 helper。需新独立Data caller/完整freeze/自身zero后有限至多1main，不重跑full-2追胜；详细`{T}/SOURCE_INTAKE_NO_SCOPE_NO_DISPATCH.json`。center/upper-entry仍暂停，不并行多个gate。

G1两closed/旧新v1失败/旧46174一次行政UNKNOWN及全部旧账保持，不连旧端追查。全部DEV gate/旧audit/GT禁止fit；第三scene/正式新用途cohort仍未合格，训练0，Actor/WM/DINO/真机/第二owner不开，自动化未改。长期G1—G6继续，以下旧条目只是历史。

'''
remote=[];proof=[]
def edit(p,new,label,peer=False):
 old=p.read_bytes();d=os.open(p.parent,os.O_RDONLY|os.O_DIRECTORY)
 try:
  fcntl.flock(d,fcntl.LOCK_EX)
  with p.open('rb')as f:
   fcntl.flock(f,fcntl.LOCK_EX);got=f.read();st=os.fstat(f.fileno());assert got==old and(p.stat().st_dev,p.stat().st_ino)==(st.st_dev,st.st_ino);(M/(label+'-before-G2-complete.md')).write_bytes(old);fd,t=tempfile.mkstemp(prefix='.'+p.name+'.G2-complete-',dir=p.parent)
   try:
    with os.fdopen(fd,'wb')as o:o.write(new);o.flush();os.fchmod(o.fileno(),stat.S_IMODE(st.st_mode));os.fsync(o.fileno())
    assert p.read_bytes()==old;os.replace(t,p);os.fsync(d)
   finally:
    if os.path.exists(t):os.unlink(t)
 finally:os.close(d)
 proof.append(dict(path=str(p),before=sha(old),after=sha(new),peer_bytes_exact=peer))
 if p.parent==B:remote.append(dict(name=p.name,expected_sha256=sha(old),bytes=base64.b64encode(new).decode()))
s=S.read_bytes();i=s.index('## Data组'.encode());end=s.find(b'\n## ',i+1);end=len(s)if end<0 else end;new=s[:i]+('## Data组\n\n'+body).encode()+s[end:];assert new[:i]==s[:i];edit(S,new,'shared-Data',True)
for name in('AGENTS.md','README.md'):
 p=B/name;s=p.read_text();i=s.index('## 当前最高执行入口');j=s.index('## 最新用户服务器',i);edit(p,(s[:i]+banner+s[j:]).encode(),name[:-3])
p=B/'STATUS.md';s=p.read_text();a='<!-- NEXT_QUESTION_SAMPLING_CURRENT_BEGIN -->';b='<!-- NEXT_QUESTION_SAMPLING_CURRENT_END -->';i=s.index(a)+len(a);j=s.index(b,i);s=s[:i]+'\n'+body+'\n'+s[j:];s=re.sub(r'更新：[^\n]+',f'更新：{now}（北京时间；G2 full-2两支closed：一PASS/一前驱异常，完整原件齐，full-1仅source intake）。',s,count=1);edit(p,s.encode(),'STATUS')
edit(M/'README.md',('# G2 original registered full-2 complete DEV gate\n\n'+body).encode(),'detailed-README')
(T/'README.md').write_text('# Original full-1 finite source intake, not dispatch\n\nAINav03:13 source option has been pinned and its original protocol/validator/device overlay/exact task floats verified without Runtime/Actor/renderer. Original full2 helper is unmodified and still rejects full1. This is a different registered case with explicit C material changes (1kg,mu.3), not geometry-only. Current source question may proceed only as a NEW independent Data-owned caller/protocol/freeze/own-zero/fresh lease, at most1main, no automatic retry. No scope/authority/physical admission/training split is allocated by this intake. Full2 right predecessor error remains closed/censored; do not replay it. First intake software import-path failure and correction retained in this directory; no physical calls in either.\n')
tree=ast.parse((M/'publish_current_progress.py').read_bytes());code=next(ast.literal_eval(n.value)for n in tree.body if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='code'for t in n.targets));code=code.replace('before-full2-live','before-full2-complete');r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','-p','46308','root@180.97.68.228','/mnt/yuanyue/data-team/env-native-v1/bin/python -I -B -c '+shlex.quote(code)],input=json.dumps(remote),capture_output=True,text=True,timeout=90)
for suffix,text in [('stdout',r.stdout),('stderr',r.stderr),('exit',str(r.returncode)+'\n')]:(M/('complete-entry-mirror.'+suffix)).write_text(text)
(M/'both-closed-next-source-CAS-peer-proof.json').write_text(json.dumps(dict(at=now,local=proof,remote_exit=r.returncode,all_peer_bytes_preserved=True),indent=2)+'\n');assert r.returncode==0,r.stderr
print('G2 complete failure-preserving current entries published; other groups exactly preserved')
