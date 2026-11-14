"""Finite local CPU package. No robot imports, network, GPU, API or subprocess.

Run once into a NEW evidence directory, protocol/source pins written before
results. Failed/UNKNOWN instances retained. No automatic tuning or re-running.
"""
import argparse
import csv
from datetime import datetime
import hashlib
import json
from pathlib import Path
import platform
import sys
import time
import numpy as np
import scipy
from scipy.optimize import minimize_scalar
from .model import cases, SCALES, MARGIN_SCALE, MODE
from .solvers import solve

METHODS=('joint_sqp','alternating_sqp','random_search','local_projection','linearized_feedback')


def write(path, value):
    with path.open('x') as stream:
        json.dump(value,stream,ensure_ascii=False,indent=2,allow_nan=False)
        stream.write('\n')


def reference(problem):
    """Independent 1D elimination for these monotone convex analytic cases only.

    At given r, f increases in d,p. Set both to smallest legal values. Bounded
    scalar solve plus endpoints/kink candidate gives a feasible numerical
    reference, NOT a claimed globally certified numerical optimality gap.
    Never used as method start or online feedback.
    """
    evaluations=[]
    def point(r):
        d=max(0.,problem.support_need+problem.drag*r+problem.drag_quadratic*r*r)
        p=max(0.,(problem.clearance_need-(1-problem.drag)*r+problem.drag_quadratic*r*r)/problem.prep_gain)
        return np.array([d,p,r])/SCALES
    def cost(r):
        u=point(r);value=problem.values(u);evaluations.append((float(r),value[0]))
        return value[0]
    result=minimize_scalar(cost,bounds=(0.,problem.retreat_upper),method='bounded',options={'xatol':1e-12})
    candidates=[0.,problem.retreat_upper,float(result.x)]
    # Separation slack kink p=0 may be interior.
    roots=np.roots([problem.drag_quadratic,-(1-problem.drag),problem.clearance_need])
    candidates += [float(x.real) for x in roots if abs(x.imag)<1e-12 and 0<=x.real<=problem.retreat_upper]
    values=[(cost(r),r) for r in candidates]
    _,r=min(values);u=point(r)
    assert problem.feasible(u)
    return dict(u=u.tolist(),parameters_m=(u*SCALES).tolist(),cost_s=problem.values(u)[0],
                separate_reference_value_calls=len(evaluations)+2,
                numerical_reference_not_robot_or_certified_global_gap=True)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--calls',type=int,default=96);parser.add_argument('--wall',type=float,default=3.)
    args=parser.parse_args()
    out=args.output;out.mkdir(parents=True,exist_ok=False)
    started=time.perf_counter();problems=cases();seeds=(0,1)
    pins={str(p.relative_to(Path.cwd())):hashlib.sha256(p.read_bytes()).hexdigest()
          for p in sorted(Path(__file__).resolve().parent.glob('*.py'))}
    parent=Path(__file__).resolve().parent.parent/'handover_envelope.py'
    pins[str(parent.relative_to(Path.cwd()))]=hashlib.sha256(parent.read_bytes()).hexdigest()
    protocol=dict(at=datetime.now().astimezone().isoformat(),scope='ANALYTIC_CPU_ONLY_NOT_executor_or_WM_data',
                  robot_shared_executor_manifest='NOT_READY_not_received_at_local_group_entry',
                  physical_lowering_for_p_and_r='NOT_READY; analytic assumptions only',
                  problems=[dict(**p.__dict__,fingerprint=p.fingerprint,mode=MODE,
                                 initial_normalized=p.initial.tolist(),lower=p.lower.tolist(),upper=p.upper.tolist()) for p in problems],
                  variable_scales_m=SCALES.tolist(),margin_scale_m=MARGIN_SCALE,
                  seeds=list(seeds),methods=METHODS,full_evaluation_budget=args.calls,wall_budget_s=args.wall,
                  common_eight_starts=True,common_exact_value_gradient_Hessian_information_available=True,
                  method_order='rotate all five by problem index plus seed',
                  cache='per method exact point bytes; combined objective/constraints/Jacobian evaluation',
                  internal_algebra_LP_QP_calls_separately_counted=True,
                  reference_not_used_as_start_or_feedback=True,
                  derivative_and_LP_cost_included_in_wall=True,
                  missing_feasible_is_UNKNOWN_not_INFEASIBLE=True,
                  novelty_claim=False,source_sha256=pins,
                  python=platform.python_version(),numpy=np.__version__,scipy=scipy.__version__)
    write(out/'protocol.json',protocol)
    # Independent numerical reference costs are never put into method budgets/inputs.
    references={p.name:reference(p) for p in problems}
    write(out/'reference.json',references)
    rows=[];raw=[]
    with (out/'raw-results.jsonl').open('x') as stream:
        for index,p in enumerate(problems):
            for seed in seeds:
                order=list(METHODS);shift=(index+seed)%len(order);order=order[shift:]+order[:shift]
                for method in order:
                    result=solve(p,method,seed=seed,max_calls=args.calls,max_wall_s=args.wall)
                    rawrow=dict(problem=p.name,family=p.family,seed=seed,**result)
                    stream.write(json.dumps(rawrow,ensure_ascii=False,allow_nan=False)+'\n');stream.flush()
                    raw.append(rawrow)
                    best=result['best']
                    row=dict(problem=p.name,family=p.family,seed=seed,method=method,status=result['status'],
                             cost_s=best['cost_s'] if best else None,
                             excess_over_numerical_reference_s=best['cost_s']-references[p.name]['cost_s'] if best else None,
                             first_feasible_call=result['first_feasible_call'],
                             first_feasible_s=result['first_feasible_s'],full_evaluations=result['full_evaluations'],
                             wall_s=result['wall_s'],derivative_requests=result['derivative_requests'],
                             internal_solves=result['internal_solves'],reason=result['reason'])
                    rows.append(row)
    with (out/'per-instance.csv').open('x') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    summary=[]
    for method in METHODS:
        selected=[r for r in rows if r['method']==method];ok=[r for r in selected if r['cost_s'] is not None]
        events=[e for r in raw if r['method']==method for e in r['algorithm_events'] if 'predicted_feasible' in e]
        summary.append(dict(method=method,instances=len(selected),feasible=len(ok),unknown=len(selected)-len(ok),
                            median_first_feasible_call=float(np.median([r['first_feasible_call'] for r in ok])) if ok else None,
                            median_full_evaluations=float(np.median([r['full_evaluations'] for r in selected])),
                            median_excess_reference_s=float(np.median([r['excess_over_numerical_reference_s'] for r in ok])) if ok else None,
                            total_wall_s=sum(r['wall_s'] for r in selected),
                            predicted_feasible_proposals=sum(e['predicted_feasible'] for e in events),
                            predicted_feasible_but_actual_infeasible=sum(e['predicted_feasible'] and not e['actual_feasible'] for e in events),
                            actual_false_feasible_outputs=sum(not problems[next(i for i,p in enumerate(problems) if p.name==r['problem'])].feasible(r['best']['u']) for r in raw if r['method']==method and r['best'])))
    validation=dict(raw_rows=len(raw),expected_rows=len(problems)*len(seeds)*len(METHODS),
                    all_evaluation_budgets_respected=all(r['full_evaluations']<=args.calls for r in rows),
                    all_finite_validated_incumbents=all(x['actual_false_feasible_outputs']==0 for x in summary),
                    total_script_wall_s=time.perf_counter()-started,
                    GPU_physics_Actor_WM_API_render_training_invocations=0,
                    all_data_analytic_not_18_robot_scenes=True,
                    local_projection_is_standard_conservative_SLP_application=True,
                    new_algorithm_advantage_established=False,
                    executable_robot_problem_ready=False)
    write(out/'summary.json',dict(methods=summary,validation=validation))
    print(json.dumps(dict(methods=summary,validation=validation),indent=2))


if __name__=='__main__':
    def no_network_or_child(event, args):
        if event in ('socket.connect','subprocess.Popen'):
            raise PermissionError('This bounded CPU fixture forbids network and child processes')
    sys.addaudithook(no_network_or_child)
    main()
