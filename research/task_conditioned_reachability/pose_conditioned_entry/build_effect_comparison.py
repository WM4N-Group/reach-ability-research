"""Render all registered actual outcomes; NEVER manufacture a positive effect.

Reads frozen reports/control/query records only. No App, actor, FK, rollout or
seed selection. Figures are descriptive development evidence, not confirmation.
"""
import argparse,html,importlib.util,json,math,hashlib
from pathlib import Path


def read(path):return json.loads(path.read_text())
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def numbers(value,scale=1):return '—' if value is None else f'{value*scale:.3f}'
LABELS={'nav_push_stow_nav_target_stable':'成功','entry_final_preview_refused':'最终预览拒绝','runtime_error':'技术失败','missing_report':'缺报告'}


def case_details(root,item,entry,classification):
    d=dict(classification,source_id=item['source_id'],sim_s=None,wall_s=None,tip_request_m=None,support_only_shift_m=None,selected_shift_m=None,
        extra_selected_shift_m=None,geometry_binding=None,controller_target_consumed=None,preparation_s=None,forecast_to_activation_s=None,
        penalty96_s=None,technical=False,raw_hashes_verified=None,recorded_query_input_sha256=None)
    if entry is None:return d
    out=root/'runs'/item['output_name'];file=out/'report.json';d.update(sim_s=entry.get('end_sim_s'),wall_s=entry.get('wall_s'),technical=bool(entry.get('severe')))
    if not file.exists():return d
    r=read(file);hash_checks=[]
    for name,key in [('report.json','report_sha256'),('control.jsonl','control_sha256')]:
        if entry.get(key):hash_checks.append(sha(out/name)==entry[key])
    if hash_checks and not all(hash_checks):raise ValueError('Terminal raw SHA mismatch: '+item['output_name'])
    d['raw_hashes_verified']=all(hash_checks) if hash_checks else None
    plan=r.get('prospective_support_plan',{});preview=plan.get('box_approach_preview',{})
    minimum=preview.get('minimum_shift_m');support=plan.get('support_only_shift_m');selected=plan.get('shift_m')
    d.update(tip_request_m=minimum,support_only_shift_m=support,selected_shift_m=selected,
        extra_selected_shift_m=None if support is None or selected is None else selected-support,
        geometry_binding=None if minimum is None or support is None else minimum>support)
    events=r.get('control_events',[]);activation=r.get('push_activation_time_s')
    braking=next((e['time_s'] for e in events if e.get('event')=='entry_supported_braking_started_not_ready'),None)
    if activation is not None and braking is not None:d['preparation_s']=activation-braking
    query_path=out/'entry_geometry.jsonl';plan_query=None
    if query_path.exists():
        for line in query_path.read_text().splitlines():
            q=json.loads(line)
            if q.get('event')=='finite_tip_query' and q.get('query_id')==preview.get('query_id'):plan_query=q;break
    if plan_query is not None:
        keys=['joint_names','q_rad','dq_rad_s','root_position_w','root_quaternion_wxyz','box_position_w','box_quaternion_wxyz','box_size_m',
            'waypoints_rad','residual_limit_rad','nominal_translation_w','forecast_margin_m','reference_quaternion_wxyz']
        d['recorded_query_input_sha256']=hashlib.sha256(json.dumps({k:plan_query.get(k) for k in keys},sort_keys=True).encode()).hexdigest()
    if activation is not None and plan_query is not None:d['forecast_to_activation_s']=activation-plan_query['time_s']
    # Expected target is derived from actual same-query nominal translation and
    # target, not a guessed zero world origin or a net measured retreat claim.
    control=out/'control.jsonl';planning_row=None;activation_row=None
    if control.exists():
        for line in control.read_text().splitlines():
            row=json.loads(line)
            if plan_query and row.get('step')==plan_query['step']:planning_row=row
            if activation is not None and row.get('time_s')==activation:activation_row=row
    if (plan_query and planning_row and activation_row and selected is not None
            and plan_query.get('nominal_translation_w') is not None and planning_row.get('stance_position_target') is not None
            and activation_row.get('stance_position_target') is not None):
        origin=plan_query['nominal_translation_w'][0]+planning_row['stance_position_target'][0]
        expected=origin-selected;actual=activation_row['stance_position_target'][0]
        d.update(controller_target_consumed=abs(expected-actual)<=1e-6,expected_target_x_m=expected,observed_target_x_m=actual,
            measured_root_x_at_planning=planning_row['root_position'][0],measured_root_x_at_activation=activation_row['root_position'][0])
    if d['primary_success'] is not None:d['penalty96_s']=d['sim_s'] if d['primary_success'] is True else 96.
    d['report_path']=str(file.resolve());return d


def analyze(root):
    source=root/'source';p=read(source/'protocol.json');manifest=read(source/'manifest.json')
    for name,h in manifest['files'].items():
        if sha(source/name)!=h:raise ValueError('Frozen comparison source changed: '+name)
    spec=importlib.util.spec_from_file_location('frozen_pose_evaluator',source/'evaluate_pose_pilot.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    ledger=read(root/'physical_ledger.json') if (root/'physical_ledger.json').exists() else None
    reports={}
    for item in p['schedule']:
        path=root/'runs'/item['output_name']/'report.json'
        if path.exists():reports[item['seed'],item['arm']]=read(path)
    evaluation=module.summarize(p,ledger,reports)
    entries={} if ledger is None else {(e['seed'],e['arm']):e for e in ledger.get('entries',[])}
    rows=[]
    for item,row in zip(p['schedule'],evaluation['rows']):rows.append(case_details(root,item,entries.get((item['seed'],item['arm'])),row))
    pairs=[]
    for left,right in [('P0','P1'),('P2','P3')]:
        for seed in p['seeds']:
            a=next(r for r in rows if r['seed']==seed and r['arm']==left);b=next(r for r in rows if r['seed']==seed and r['arm']==right)
            known=a['primary_success'] is not None and b['primary_success'] is not None
            pairs.append(dict(seed=seed,baseline=left,pose=right,observed_pair=known,
                success_delta=None if not known else int(b['primary_success'])-int(a['primary_success']),
                common_success_sim_delta_s=b['sim_s']-a['sim_s'] if a['primary_success'] is True and b['primary_success'] is True else None,
                penalty96_delta_s=None if not known else b['penalty96_s']-a['penalty96_s'],
                selected_shift_delta_m=None if a['selected_shift_m'] is None or b['selected_shift_m'] is None else b['selected_shift_m']-a['selected_shift_m'],
                recorded_query_inputs_equal=None if a['recorded_query_input_sha256'] is None or b['recorded_query_input_sha256'] is None else a['recorded_query_input_sha256']==b['recorded_query_input_sha256']))
    complete=all(r['primary_success'] is not None for r in rows)
    conclusion='注册配对不完整：只报告已知成功、失败与未运行，不能估计完整方法增益。'
    if complete:
        effect=sum(x['success_delta'] for x in pairs)/len(pairs)
        if effect>0:conclusion='本批开发先导观察到姿态分支的完成改善线索；每臂仅2个初态，不能作为独立泛化结论。'
        elif effect<0:conclusion='本批姿态分支完成表现更差，不支持当前实现带来导航完成增益。'
        else:conclusion='本批没有观察到姿态分支的新增完成收益；耗时和机制是否触发需分别看，不能把全部成功当作公式有效。'
    if complete and any(r['technical'] for r in rows):
        conclusion='本批包含技术或严重安全中止；结果全部保留，但不能把完成差异直接归因于公式有效。'
    valid_binding=[r for r in rows if r['geometry_binding'] is not None]
    mechanism_note=''
    if valid_binding and not any(r['geometry_binding'] for r in valid_binding):mechanism_note='所有已观察规划均由原支撑需求覆盖，几何项没有成为新增退让的约束；本批未充分触发所研究的机制。'
    observed_choices=[pair['selected_shift_delta_m'] for pair in pairs if pair['selected_shift_delta_m'] is not None]
    no_pose_choice_change=len(observed_choices)==len(pairs) and all(delta==0 for delta in observed_choices)
    if complete and no_pose_choice_change:
        conclusion='本批姿态分支没有改变所记录的准备退让选择；完整结果照报，但不能仅凭完成或耗时差异认定姿态公式有效。'
    return dict(schema='pose-entry-morning-effect-comparison-v1',source_manifest_sha256=sha(source/'manifest.json'),
        ledger_status=None if ledger is None else ledger['status'],starts=0 if ledger is None else ledger['starts'],
        registered=8,complete=complete,conclusion=conclusion,mechanism_note=mechanism_note,evaluation=evaluation,rows=rows,pairs=pairs,
        pose_pair_preparation_choices_unchanged=no_pose_choice_change,
        original_case_ledger_untouched=True,independent_generalization_claim=False,full_obstacle_navigation_claim=False,
        safety_note='原安全条件、失败和unknown保留；SDK/CPU/日志重建视频不是物理收益。')


def write_report(root,out):
    if out.exists():raise FileExistsError('Comparison already generated; never overwrite evidence')
    report=analyze(root);out.mkdir(parents=True)
    (out/'comparison.json').write_text(json.dumps(report,indent=2)+'\n')
    rows=report['rows'];lines=['# 姿态条件入口：研究效果对比','',report['conclusion'],'',report['mechanism_note'],'',
        f"- 实际启动：{report['starts']}/8；状态：`{report['ledger_status']}`。旧2次与旧14个unknown不重评分。",
        '- P0：端点＋平移；P1：端点＋姿态参考；P2：全路径＋平移；P3：全路径＋姿态参考。所有最终复核相同。',
        '- 完成必须是共同目标的实际原生完成；每臂仅2个新初态，是开发先导，不是完整穿障碍导航或确认性实验。','',
        '## 全部注册结果（不删失败）','',
        '| seed | 变体 | 结果 | sim/s | wall/s | 几何需求/mm | 原支撑/mm | 选择退让/mm | 几何项绑定 | 目标被控制器消费 |',
        '|---|---|---|---:|---:|---:|---:|---:|---|---|']
    def label(r):
        if r['status']=='not_run':return '未运行'
        if r['status']=='in_flight':return '进行中'
        if r['primary_success'] is True:return '已核验成功'
        if r['primary_success'] is None:return '未知／未通过独立核验'
        return LABELS.get(r.get('native_outcome'),r.get('native_outcome') or '失败')
    flag=lambda v:'未知' if v is None else '是' if v else '否'
    for r in rows:lines.append(f"| {r['seed']} | {r['arm']} | {label(r)} | {numbers(r['sim_s'])} | {numbers(r['wall_s'])} | {numbers(r['tip_request_m'],1000)} | {numbers(r['support_only_shift_m'],1000)} | {numbers(r['selected_shift_m'],1000)} | {flag(r['geometry_binding'])} | {flag(r['controller_target_consumed'])} |")
    lines+=['','## 同初态有／无姿态预测的配对差异','','负的耗时差表示姿态分支更快；只有共同成功对才比较成功耗时。失败惩罚时长为96秒；缺失不填。','',
        '| seed | 对比（姿态−基线） | 成功差 | 共同成功sim差/s | 失败惩罚时长差/s | 实际准备选择差/mm | 已记录查询输入一致 |','|---|---|---:|---:|---:|---:|---|']
    for pair in report['pairs']:lines.append(f"| {pair['seed']} | {pair['pose']}−{pair['baseline']} | {numbers(pair['success_delta'])} | {numbers(pair['common_success_sim_delta_s'])} | {numbers(pair['penalty96_delta_s'])} | {numbers(pair['selected_shift_delta_m'],1000)} | {flag(pair['recorded_query_inputs_equal'])} |")
    lines+=['','## 该怎样读这份报告','',
        '1. 完成率没提高，就是没有观察到完成收益；不能拿多拒绝或更多样点替代效果。',
        '2. 几何需求小于原支撑需求时，公式可能没有改变实际动作；需要看“几何项绑定”和新增退让。',
        '3. “目标被消费”检查原控制器实际记录的准备目标，不是只看规划函数返回了一个数；也不是声称跟踪误差有界。',
        '4. 准备时间、App启动和共同观察开销都不能隐藏；完整数据见comparison.json。',
        '5. 本协议依然是局部NAV→PUSH→收臂→共同目标，不是推开路障后穿过去的完整任务。','',
        '## 证据','',f"- 冻结源码SHA：`{report['source_manifest_sha256']}`",f'- 原始case目录：`{str((root/"runs").resolve())}`',
        '- 自动报告只读日志，不启动仿真、模型或新采集。','']
    md='\n'.join(lines);(out/'研究效果对比.md').write_text(md)
    headers=['seed','变体','结果','sim/s','wall/s','几何需求/mm','原支撑/mm','选择退让/mm','几何项绑定','控制消费']
    body=[]
    for r in rows:
        cells=[str(r['seed']),r['arm'],label(r),numbers(r['sim_s']),numbers(r['wall_s']),numbers(r['tip_request_m'],1000),numbers(r['support_only_shift_m'],1000),numbers(r['selected_shift_m'],1000),flag(r['geometry_binding']),flag(r['controller_target_consumed'])]
        cls='ok' if r['primary_success'] is True else 'bad' if r['primary_success'] is False else 'unknown'
        body.append('<tr class="'+cls+'">'+''.join('<td>'+html.escape(c)+'</td>' for c in cells)+'</tr>')
    page='''<!doctype html><meta charset="utf-8"><title>研究效果对比</title><style>body{font-family:system-ui,sans-serif;background:#f3f6fa;color:#20344b;max-width:1400px;margin:36px auto;padding:0 24px}section{background:white;border-radius:14px;padding:24px;margin:20px 0}h1{font-size:32px}table{border-collapse:collapse;width:100%;font-size:14px}th,td{padding:12px 8px;border-bottom:1px solid #dde4ec;text-align:left}tr.ok td:nth-child(3){color:#087d58;font-weight:bold}tr.bad td:nth-child(3){color:#b13c35;font-weight:bold}tr.unknown{color:#777}.warn{border-left:5px solid #cd9145;padding:14px;background:#fff6e9}pre{white-space:pre-wrap;line-height:1.65}</style>'''
    page+='<h1>姿态条件入口：研究效果对比</h1><section><h2>'+html.escape(report['conclusion'])+'</h2><p>'+html.escape(report['mechanism_note'])+'</p><p class="warn">开发先导，每臂2个初态。没有自动宣称正增益；缺失不填成功。</p></section>'
    page+='<section><h2>全部8个注册结果</h2><table><thead><tr>'+''.join('<th>'+h+'</th>' for h in headers)+'</tr></thead><tbody>'+''.join(body)+'</tbody></table></section>'
    page+='<section><h2>配对结果与解释</h2><pre>'+html.escape(md[md.index('## 同初态'):])+'</pre></section>'
    (out/'研究效果对比.html').write_text(page)
    return report


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=write_report(a.root,a.output);print(r['conclusion'])

if __name__=='__main__':main()
