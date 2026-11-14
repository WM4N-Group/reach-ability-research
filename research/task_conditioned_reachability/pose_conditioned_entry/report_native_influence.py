"""Read-only post-exposure explanation of an already closed native pilot.

Reads only explicitly supplied completed development records. Never invokes FK,
actors, subprocess launchers or a simulator. No new sampling or trial selection.
"""
import argparse
import hashlib
import json
from pathlib import Path

from native_influence import ARMS, compare_requests, describe_request, verify_native_branch, frozen_cloud_translation_window

SOURCE_SHA = '55190212ff9b6cafcd9536a0c6397fc1132b1d9505cde2a6c838b5d9883fd0a1'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def explain(root):
    root = root.resolve()
    manifest_path = root/'source/manifest.json'
    if digest(manifest_path) != SOURCE_SHA:
        raise ValueError('This reporter is restricted to the closed exposed development source')
    manifest = read(manifest_path)
    for name, value in manifest['files'].items():
        if digest(root/'source'/name) != value:
            raise ValueError('Frozen source mismatch: '+name)
    binding = verify_native_branch((root/'source/probe.py').read_text())
    ledger_path = root/'physical_ledger.json'
    ledger = read(ledger_path)
    if ledger.get('status') != 'COMPLETED_REGISTERED_EIGHT':
        raise ValueError('Only the closed eight-cell pilot is eligible')
    protocol = read(root/'source/protocol.json')
    ledger_rows = {(r['seed'], r['arm']): r for r in ledger['entries']}
    rows = []
    inputs = {str(manifest_path): digest(manifest_path), str(ledger_path): digest(ledger_path)}
    for item in protocol['schedule']:
        folder = root/'runs'/item['output_name']
        report_path, geometry_path = folder/'report.json', folder/'entry_geometry.jsonl'
        entry = ledger_rows[(item['seed'], item['arm'])]
        if digest(report_path) != entry['report_sha256']:
            raise ValueError('Report changed: '+item['output_name'])
        report = read(report_path)
        plan = report['prospective_support_plan']
        preview = plan['box_approach_preview']
        matches = []
        with geometry_path.open() as stream:
            for line in stream:
                record = json.loads(line)
                if record.get('event') == 'finite_tip_query' and record.get('query_id') == preview['query_id']:
                    matches.append(record)
        if len(matches) != 1:
            raise ValueError('Expected exactly one same-query planning witness')
        query = matches[0]
        if query.get('evaluation_role') != 'planning' or query.get('arm') != item['arm']:
            raise ValueError('Query role/arm mismatch')
        requests = query['all_planning_requests']
        if set(requests) != set(ARMS):
            raise ValueError('Unmatched factorial request set')
        support = plan['support_only_shift_m']
        certificates = {arm: describe_request(support, requests[arm]['minimum_shift_m']) for arm in ARMS}
        chosen = certificates[item['arm']]
        if requests[item['arm']]['minimum_shift_m'] != preview['minimum_shift_m']:
            raise ValueError('Logged selected request does not match report')
        if chosen['baseline_plan_reused'] is True and plan['shift_m'] != chosen['selected_shift_m']:
            raise ValueError('Observed selection contradicts branch certificate')
        pairs = {right+'-'+left: compare_requests(support, requests[left]['minimum_shift_m'], requests[right]['minimum_shift_m'])
                 for left, right in [('P0','P1'), ('P2','P3')]}
        windows={right+'-'+left: frozen_cloud_translation_window(
            support, requests[left]['maximum_box_local_x'], requests[right]['maximum_box_local_x'],
            query['box_size_m'][0]/2., .015+query['forecast_margin_m'], query['world_x_in_box'][0])
            for left,right in [('P0','P1'),('P2','P3')]}
        rows.append(dict(seed=item['seed'], executed_arm=item['arm'], query_id=query['query_id'],
                         support_only_shift_m=support, observed_selected_shift_m=plan['shift_m'],
                         all_same_query_request_certificates=certificates, same_query_pairs=pairs, conditional_local_box_x_windows=windows))
        for path in (report_path, geometry_path): inputs[str(path)] = digest(path)
    if len(rows) != 8:
        raise ValueError('No filtering or missing registered cell is allowed')
    return dict(schema='native-entry-influence-posthoc-v1', source_manifest_sha256=SOURCE_SHA,
                data_role='already_exposed_development_closed_pilot', branch_binding=binding,
                input_sha256=inputs, rows=rows,
                rows_with_all_four_requests_masked=sum(all(c['baseline_plan_reused'] is True
                                                           for c in r['all_same_query_request_certificates'].values()) for r in rows),
                analysis_scope='new branch-specific software explanation, not new physics, '
                               'calibration, seed selection, independent validation or a success estimate',
                experiments_started=0, execution_authorized=False)


def markdown(result):
    lines = ['# 实际技能入口：公式何时会改变准备动作', '',
             '**范围：**对已曝光、已闭合8格开发记录的新分支级解释；不是新实验或新成功率。', '',
             '## 已绑定原生代码的命题', '',
             '记原支撑准备输出为 d₀，几何请求为 m。原代码不是简单 max(d₀,m)：',
             '- m ≤ d₀：直接复用原支撑计划，入口退让 d(m)=d₀。',
             '- m > d₀：重新运行原支撑搜索（5mm网格、非零点额外5mm且上限40mm，另含条件性PUSH储备）；可能拒绝。',
             '- 所以同一输入下 mₐ,mᵦ ≤ d₀ ⇒ 两者入口退让相同。',
             '- 至少一个请求超过 d₀ 是产生入口退让差异的必要条件，不是任务收益或安全的充分条件。', '',
             '证明：直接代入已绑定AST的条件表达式，两个分支均返回baseline；后续相同字段赋值不改变shift_m。',
             '此命题只对上游FK/source检查已通过且请求在原域内成立；不保证相同耗时、后续状态或动态安全。', '',
             '## 闭合开发记录的应用', '',
             '| seed | 实际执行臂 | 原支撑/mm | P0请求/mm | P1请求/mm | P2请求/mm | P3请求/mm | 已选/mm |',
             '|---|---|---:|---:|---:|---:|---:|---:|']
    for r in result['rows']:
        certs=r['all_same_query_request_certificates']
        numbers=[r['support_only_shift_m']]+[certs[a]['minimum_shift_m'] for a in ARMS]+[r['observed_selected_shift_m']]
        lines.append('| '+str(r['seed'])+' | '+r['executed_arm']+' | '+' | '.join(f'{x*1000:.6f}' for x in numbers)+' |')
    lines += ['', f"全部四项均被原支撑输出覆盖：{result['rows_with_all_four_requests_masked']}/8个已执行查询。",
              '同一查询内的四个数不是四个新反事实执行结局；未执行分支不生成成功标签。', '',
              '## 新增的条件性场景设计，不是新增物理样本', '',
              '在机器人、路径、姿态参考、盒朝向与原支撑结果固定时，仅让盒沿自身局部x方向靠近delta，所选点云最大x增加delta。',
              '记Eᵢ=xmaxᵢ+hₓ+inflation、a=world_x_in_box[0]，则mᵢ(delta)=max(0,(Eᵢ+delta)/a)。',
              '左臂仍复用支撑、右臂触发重算的窗口为a*d₀−E_right < delta ≤ min(a*d₀−E_left, a*40mm−E_right)，另要求delta≥0。',
              '该窗口只指导新初态设计；改变实际初始箱位后机器人轨迹/支撑输入也可能变化，必须在真实决策时刻重验，不能据此宣布新场景有效或标签成功。',
              '窗口按全部既有查询输出，不按成败挑seed；仅已曝光开发几何，非保留集校准。', '',
              '## 下一轮单因素协议（设计，未注册/未启动）', '',
              '只比较P2全路径平移与P3全路径姿态参考，避免再重复四臂分解；保留原支撑、安全门、演员、PD和最终实际full-cloud复核。',
              '候选初态、任务域和预算必须另行冻结；当前没有已闭合的新场景，不自动占用剩余6次。',
              '机制分层仅用决策前观测：支撑覆盖（负对照）、需要原生重算（尚非动作差异）、输入缺失/域外（unknown）。',
              '每个注册初态均保留，不因未触发、拒绝、超时或失败而换seed/删分母；触发率只是机制指标。',
              '如果真实准备阶段没有动作差异，则不为同一姿态退让项继续扩批；不改变支撑要求去造差异。',
              '下一实际接入点为probe.py的prospective_entry及prospective_support_integrated_into_final_center事件；原控制器消费term.prospective_shift_m。',
              '先取得合法新初态在真实决策时刻的共同query与原支撑结果，再验证两方法输出能否形成可执行差异；这一步若需App/物理，也必须先登记预算。',
              '物理比较指标仍是共同目标的全链成功、失败惩罚全耗时、原生安全事件和真实准备选择/控制目标消费；不把分数差替代任务增益。', '',
              '本报告不读取5311/5312，不修改旧raw/source/账本，不启动SDK/训练/物理。']
    return '\n'.join(lines)+'\n'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--completed-root', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args=parser.parse_args()
    result=explain(args.completed_root)
    args.output_dir.mkdir(parents=True, exist_ok=False)
    (args.output_dir/'analysis.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    (args.output_dir/'研究结论与下一轮接口.md').write_text(markdown(result))
    print(json.dumps({k:result[k] for k in ('schema','rows_with_all_four_requests_masked','experiments_started')},ensure_ascii=False))


if __name__ == '__main__': main()
