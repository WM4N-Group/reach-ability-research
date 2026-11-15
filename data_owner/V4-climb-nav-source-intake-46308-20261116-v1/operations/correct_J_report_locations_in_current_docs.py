"""Correct report location/count wording after matching local7/remote5 metadata. Data-only CAS; no scientific data changes."""
from pathlib import Path
import json,hashlib,datetime,os,fcntl,stat,tempfile
B=Path('/home/yuanyue/main/work/data-team');M=Path(__file__).resolve().parent;J=B/'manifests/V-JEPA-J1-resource-response-46308-20261116-v1';S=Path('/home/yuanyue/main/汇总/各小组进展汇总.md');v=json.loads((J/'Data-J1-completed-CPU-technical-window-consumed.json').read_bytes());assert len(v['local_original_metadata_pins_verified'])==7 and len(v['remote_original_metadata_pins_verified'])==5
old='和远端**7份小metadata报告SHA**逐一核同';new='对**7份本机原件metadata和5份远端metadata SHA**逐一核同';sha=lambda b:hashlib.sha256(b).hexdigest();proof=[]
for p in [S,B/'STATUS.md',B/'AGENTS.md',B/'README.md',J/'README.md']:
 before=p.read_bytes();text=before.decode();mode=stat.S_IMODE(p.stat().st_mode)
 if p==J/'README.md':text=text.replace('并与远端**7份本机原件metadata及5份远端metadata SHA**逐一核同','并对**7份本机原件metadata和5份远端metadata SHA**逐一核同')
 else:assert old in text;text=text.replace(old,new)
 after=text.encode()
 if p==S:
  a=before.index('## Data组\n'.encode());b=before.find(b'\n## ',a+1);b=len(before)if b<0 else b;a2=after.index('## Data组\n'.encode());b2=after.find(b'\n## ',a2+1);b2=len(after)if b2<0 else b2;assert before[:a]==after[:a2]and before[b:]==after[b2:]
 backup=M/(('J-resource-'if p.parent==J else'')+p.name+'.before-report-locations-correction')
 with backup.open('xb')as f:f.write(before)
 dfd=os.open(p.parent,os.O_RDONLY|os.O_DIRECTORY)
 try:
  fcntl.flock(dfd,fcntl.LOCK_EX)
  with p.open('rb')as f:
   fcntl.flock(f.fileno(),fcntl.LOCK_EX);assert p.read_bytes()==before;fd,tmp=tempfile.mkstemp(prefix='.'+p.name+'.cas.',dir=p.parent)
   try:
    with os.fdopen(fd,'wb')as out:os.fchmod(out.fileno(),mode);out.write(after);out.flush();os.fsync(out.fileno())
    assert p.read_bytes()==before;os.replace(tmp,p);os.fsync(dfd)
   finally:
    if os.path.exists(tmp):os.unlink(tmp)
 finally:os.close(dfd)
 proof.append(dict(path=str(p),before_sha256=sha(before),after_sha256=sha(after),mode_preserved=stat.S_IMODE(p.stat().st_mode)==mode,peer_bytes_preserved=p==S))
p=M/'publish_current_source32_and_J_report.py';s=p.read_text();p.write_text(s.replace(old,new));p=M/'consume_J_completed_cpu_window.py';s=p.read_text();p.write_text(s.replace('并与远端**7份本机原件metadata及5份远端metadata SHA**逐一核同','并对**7份本机原件metadata和5份远端metadata SHA**逐一核同'))
oldtext=(M/'README.md').read_bytes();(M/'README.md.before-final-J-technical-stage').write_bytes(oldtext);(M/'README.md').write_text('''# 当前增量：J完整技术结果已消费，不再把下载阶段restore0当当前\n\n04:12计划22f570c1仅更新J实际技术进度。Data已核7份本机原件metadata和5份远端metadata SHA（两个初始远端报告是未加initial_failed后缀的原名；diagnosis/provenance是本机公布原件，不谎称全在远端）；J最终strict CPU restore2/合成encoder forward2/随机head1、真数据forward/fit/EVAL/GPU/物理0，全部04:02:26结束、总CPU技术phase315.303s<900且资源cap内，原slot04:15到期不延长。Data没有重复模型、权重或原fixture计算。\n\n首次元数据checker误以7个本机report basename都在远端root，失败后改为已观察的精确位置/别名逐SHA核；短暂发布的“7远端”措辞已CAS纠正为7本机/5远端，前后文本/错误原记录保留。不改原J报告或科学数据/H/任何进程。\n\n新32源source reader依旧只是必要source observation，不是active NAV handoff/准入，不新跑native/借zero。以下03:56下载阶段报告的model0只是历史，实际后续技术结果以上述完整milestone为准。\n\n---\n\n'''+oldtext.decode())
with(M/'Data-only-report-location-correction-proof.json').open('x')as f:json.dump(dict(at=datetime.datetime.now().astimezone().isoformat(),proof=proof,all_shared_peer_bytes_preserved=True,local7_and_remote5_metadata_SHA_verified=True,original_first_plan_SHA_guard_correctly_stopped_before_any_write=True,report_path_assumption_failure_preserved=True,no_native_model_or_H_or_original_report_changes=True),f,ensure_ascii=False,indent=2);f.write('\n')
print('Corrected report wording: seven local originals, five remote originals; no model/native rerun')
