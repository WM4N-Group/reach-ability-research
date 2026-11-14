"""Read-only action/consumption/cost evidence from registered real-skill trials.

A changed command or larger finite-cloud surplus is not task-success evidence.
This consumes completed rows only, without filtering any registered case, and
never reconstructs unexecuted physical outcomes or loads a simulator/actor.
"""
import argparse
import html
import json
import math
from pathlib import Path
import sys
import time

from evaluate_followup import evaluate, sha
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'pose_conditioned_entry'))
from build_effect_comparison import case_details


def read(path):return json.loads(path.read_text())

def directional_surplus(query):
    """Signed local-box-x slack of the SAME final finite selected sample set.

    This is NOT global Euclidean clearance, a tracking bound, physical contact
    clearance or a sufficient dynamic safety condition. No selected yz samples
    means unknown, not infinite clearance.
    """
    unknown=dict(value_m=None,unit='m',status='unknown',safety_certificate=False,
                 scope='final measured-pose finite-cloud fixed-yz box-local-x directional surplus')
    if not query or query.get('evaluation_role')!='final_actual' or query.get('criterion')!='COMMON_original_full_cloud_fixed_yz':
        return unknown
    if query.get('nominal_translation_w') is not None or query.get('forecast_margin_m')!=0.:
        return unknown
    maximum=query.get('maximum_box_local_x');size=query.get('box_size_m');count=query.get('samples_in_expanded_yz')
    if (isinstance(maximum,bool) or not isinstance(maximum,(int,float)) or not math.isfinite(maximum)
            or not isinstance(size,list) or len(size)!=3
            or not all(isinstance(x,(int,float)) and not isinstance(x,bool) and math.isfinite(x) and x>0 for x in size)
            or isinstance(count,bool) or not isinstance(count,int) or count<=0):return unknown
    # Native actual inflation: 10mm tip radius + 5mm original planning margin.
    surplus=-(maximum+size[0]/2.+.015)
    return dict(unknown,value_m=surplus,status='observed_finite_model_value',
                selected_samples=count,inflation_m=.015)


def pair_record(seed,left,right,matched):
    known=left['primary_success'] is not None and right['primary_success'] is not None
    def delta(key):
        a,b=left.get(key),right.get(key)
        return None if a is None or b is None else b-a
    shift=delta('selected_shift_m')
    consumed=(left.get('controller_target_consumed') is True and right.get('controller_target_consumed') is True)
    both=left['primary_success'] is True and right['primary_success'] is True
    a=left.get('final_directional_surplus',{}).get('value_m')
    b=right.get('final_directional_surplus',{}).get('value_m')
    return dict(seed=seed,completed_outcome_pair=known,common_input_witnesses_equal=matched,
                observed_success_delta=int(right['primary_success'])-int(left['primary_success']) if known else None,
                selected_shift_delta_m=shift,
                controller_consumption_verified=consumed,
                action_contrast_observed=shift is not None and shift!=0.,
                matched_consumed_action_contrast=matched is True and consumed and shift is not None and shift!=0.,
                common_success_sim_delta_s=delta('sim_s') if both else None,
                common_success_wall_delta_s=delta('wall_s') if both else None,
                penalty96_delta_s=delta('penalty96_s') if known else None,
                preparation_delta_s=delta('preparation_s'),
                final_directional_surplus_delta_m=None if a is None or b is None else b-a,
                scope='observed P3 minus P2; not safety proof or independent generalization')


def analyze(root):
    root=Path(root);base=evaluate(root);protocol=read(root/'source/protocol.json')
    ledger=read(root/'physical_ledger.json') if (root/'physical_ledger.json').exists() else None
    entries={} if ledger is None else {(e['seed'],e['arm']):e for e in ledger.get('entries',[])}
    rows=[];inputs={str(root/'source/manifest.json'):sha(root/'source/manifest.json')}
    if ledger is not None:inputs[str(root/'physical_ledger.json')]=sha(root/'physical_ledger.json')
    for item,classification in zip(protocol['schedule'],base['native_evaluation']['rows']):
        key=item['seed'],item['arm'];entry=entries.get(key)
        row=case_details(root,item,entry,classification)
        row['final_directional_surplus']=directional_surplus(None)
        folder=root/'runs'/item['output_name']
        if entry is not None:
            for filename,hash_key in [('control.jsonl','control_sha256'),('report.json','report_sha256'),
                                      ('entry_geometry.jsonl','geometry_sha256'),('actual-initial-state.json','initial_state_sha256')]:
                p=folder/filename
                if p.exists():
                    digest=sha(p)
                    if entry.get(hash_key) and digest!=entry[hash_key]:raise ValueError('Raw hash mismatch: '+str(p))
                    inputs[str(p)]=digest
            if (folder/'report.json').exists():
                report=read(folder/'report.json')
                final=report.get('measured_final_support_verification',{}).get('box_approach_preview',{})
                query_id=final.get('query_id');path=folder/'entry_geometry.jsonl'
                matches=[]
                if query_id and path.exists():
                    with path.open() as stream:
                        for line in stream:
                            q=json.loads(line)
                            if q.get('event')=='finite_tip_query' and q.get('query_id')==query_id:matches.append(q)
                if len(matches)==1:
                    q=matches[0]
                    if q.get('minimum_shift_m')!=final.get('minimum_shift_m'):raise ValueError('Final witness/report disagree')
                    row['final_directional_surplus']=directional_surplus(q)
        rows.append(row)
    pairs=[]
    for witness in base['input_pairs']:
        seed=witness['seed']
        left=next(x for x in rows if x['seed']==seed and x['arm']=='P2')
        right=next(x for x in rows if x['seed']==seed and x['arm']=='P3')
        pairs.append(pair_record(seed,left,right,witness['common_input_witnesses_equal']))
    return dict(schema='actual-skill-six-action-mechanism-v1',source_manifest_sha256=base['source_manifest_sha256'],
                ledger_status=base['state'],starts=base['native_evaluation']['starts'],registered=6,
                complete=all(row['primary_success'] is not None for row in rows),
                registered_success_delta=base['descriptive_success_delta'],
                matched_input_success_delta=base['matched_input_success_delta'],
                closed_pairs=sum(x['completed_outcome_pair'] for x in pairs),
                matched_consumed_action_contrast_pairs=sum(x['matched_consumed_action_contrast'] for x in pairs),
                rows=rows,pairs=pairs,input_sha256=inputs,
                original_source_and_raw_modified=False,registered_cases_filtered=0,
                positive_task_gain_claim=False,scope='development mechanism/cost report; partial pairs do not estimate the complete registered effect')


def markdown(report):
    def num(value,scale=1):return '—' if value is None else f'{value*scale:.3f}'
    lines=['# 实际技能：动作改变、控制器消费与任务效果','',
           f"状态`{report['ledger_status']}`，已启动{report['starts']}/6，闭合配对{report['closed_pairs']}/3。",'',
           '**必须分开：**公式数值变化、实际准备动作变化、任务收益。有限点云余量不是物理安全证明。','',
           '| seed | 方法 | 实际结局 | sim/s | wall/s | 几何请求/mm | 原支撑/mm | 已选/mm | 控制器使用 | 最终模型方向余量/mm |',
           '|---|---|---|---:|---:|---:|---:|---:|---|---:|']
    for x in report['rows']:
        lines.append(f"|{x['seed']}|{x['arm']}|{x.get('native_outcome') or x['status']}|{num(x['sim_s'])}|{num(x['wall_s'])}|"
                     f"{num(x['tip_request_m'],1000)}|{num(x['support_only_shift_m'],1000)}|{num(x['selected_shift_m'],1000)}|"
                     f"{x['controller_target_consumed']}|{num(x['final_directional_surplus']['value_m'],1000)}|")
    lines+=['','## 同初态P3−P2配对','',
            '| seed | 共同输入匹配 | 退让差/mm | 双方目标消费已核 | 成功差 | 共同成功sim差/s | 最终模型方向余量差/mm |',
            '|---|---|---:|---|---:|---:|---:|']
    for x in report['pairs']:
        lines.append(f"|{x['seed']}|{x['common_input_witnesses_equal']}|{num(x['selected_shift_delta_m'],1000)}|"
                     f"{x['controller_consumption_verified']}|{num(x['observed_success_delta'])}|"
                     f"{num(x['common_success_sim_delta_s'])}|{num(x['final_directional_surplus_delta_m'],1000)}|")
    lines+=['',f"完整注册成功率差：{report['registered_success_delta']}；共同输入匹配口径：{report['matched_input_success_delta']}。",
            '未完整闭合为None/—，不把缺证补零、不按触发或成败删案例。',
            '原生控制器实际目标消费检查来自同query/同step的control.jsonl，不把函数返回值当已执行。',
            '方向余量为共同final_actual有限采样、固定yz门内的−(max_box_local_x+half_x+15mm)，不是全身欧氏净空/动态稳定/独立安全界。',
            'wall包含实际进程成本，sim与准备耗时分开；不以多退让或余量增加替代任务收益。',
            '本报告只消费已闭合记录，不启动任务、改参数或重算未执行结局。']
    return '\n'.join(lines)+'\n'


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True);p.add_argument('--output-dir',type=Path,required=True)
    p.add_argument('--wait-for-comparison',action='store_true');p.add_argument('--max-wait-s',type=float,default=14400);a=p.parse_args()
    if a.output_dir.exists():raise FileExistsError('Never overwrite an earlier mechanism report')
    if not 0<a.max_wait_s<=14400:raise ValueError('Read-only wait may not exceed four hours')
    if a.wait_for_comparison:
        began=time.monotonic()
        while not (a.root/'comparison/comparison.json').exists():
            if time.monotonic()-began>=a.max_wait_s:raise TimeoutError('No final comparison; do not invent a final outcome')
            time.sleep(30)
    result=analyze(a.root);a.output_dir.mkdir(parents=True,exist_ok=False)
    text=markdown(result)
    (a.output_dir/'mechanism.json').write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    (a.output_dir/'实际技能机制与效果.md').write_text(text)
    (a.output_dir/'实际技能机制与效果.html').write_text('<!doctype html><html lang="zh"><meta charset="utf-8"><title>实际技能机制与效果</title><style>body{max-width:1200px;margin:32px auto;padding:0 18px;font:16px/1.7 sans-serif}pre{white-space:pre-wrap;overflow-wrap:anywhere}</style><body><pre>'+html.escape(text)+'</pre></body></html>')
    print(json.dumps({k:result[k] for k in ['ledger_status','starts','closed_pairs','matched_consumed_action_contrast_pairs','registered_success_delta']},ensure_ascii=False))


if __name__=='__main__':main()
