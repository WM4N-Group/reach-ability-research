"""An actual preparation-path optimizer, not an entry classifier.

Choose an ordered subsequence of ORIGINAL native arm waypoints. All candidate
edges use the supplied ORIGINAL finite path guard. The compact endpoint, native
reference law and final four-second verification are not decision variables.
No WM, old outcome labels, training, invented base motion or safety certificate.
"""
import math


def need(ok, message):
    if not ok:
        raise ValueError(message)


def vector(value):
    value=tuple(value)
    need(len(value)==6 and all(type(x) in (int,float) and math.isfinite(x) for x in value),
         'Finite six-joint reference only')
    return value


def native_seconds(delta):
    need(type(delta) in (int,float) and math.isfinite(delta) and delta>=0,
         'Nonnegative finite joint reference displacement')
    return max(.6,1.875*delta/.40,math.sqrt(5.78*delta/.80))


def reference_edge_interval(start, end, *, uncertain_origin=False):
    """Native duration assignment, not measured motion/completion duration.

    Subsequent original segments start when issued reference is within .002rad
    of the preceding waypoint; use that SOURCE condition, not observed peaks.
    It bounds the assigned schedule only if the native transition occurs.
    Tracking/settling delay and successor repair time remain UNKNOWN.
    """
    start,end=vector(start),vector(end)
    need(type(uncertain_origin) is bool, 'Explicit native origin condition')
    d=max(abs(a-b) for a,b in zip(start,end));eps=.002 if uncertain_origin else 0.
    return dict(nominal_s=native_seconds(d),lower_s=native_seconds(max(0.,d-eps)),
                upper_s=native_seconds(d+eps),source_reference_origin_tolerance_rad=eps,
                actual_completion_time_upper_s=None)


def path_sum(path, edges):
    selected=[edges[(a,b)] for a,b in zip(path,path[1:])]
    if any(not e['guard_pass'] for e in selected):
        return None
    return dict(lower_s=sum(e['timing']['lower_s'] for e in selected),
                nominal_s=sum(e['timing']['nominal_s'] for e in selected),
                upper_s=sum(e['timing']['upper_s'] for e in selected))


def all_subsequences(n):
    # SOFTWARE baseline: exhaustive finite domain, no unexecuted dynamics.
    need(type(n) is int and 1 <= n <= 16, 'Bounded nonempty waypoint domain')
    for mask in range(1 << (n-1)):
        yield (0,)+tuple(i for i in range(1,n) if mask & (1 << (i-1)))+(n,)


def optimize(reference, actual_q, waypoints, *, guard_segment, compare_exhaustive=False):
    """Minimize conservative native reference schedule over one finite DAG.

    Domain: ordered subsequences, not arbitrary q or continuous goal search.
    First edges check both the actual q -> target (original caller recheck)
    and issued reference -> target (nominal segment to be consumed). Other
    edges check the waypoint pair. A guard failure is local, not task failure.
    """
    reference,actual_q=vector(reference),vector(actual_q)
    waypoints=tuple(vector(q) for q in waypoints)
    need(1<=len(waypoints)<=16 and callable(guard_segment), 'Bounded original waypoint domain')
    need(type(compare_exhaustive) is bool,'Explicit software baseline toggle')
    points=(reference,)+waypoints;n=len(waypoints);edges={};cache={}
    def guard(a,b):
        key=(a,b)
        if key not in cache:
            reason=guard_segment(a,b)
            need(type(reason) is str,'Original guard reason must be literal string; unknown is not pass')
            cache[key]=reason
        return cache[key]
    for i in range(n):
        for j in range(i+1,n+1):
            reasons=[guard(points[i],points[j])]
            if i==0:reasons.append(guard(actual_q,points[j]))
            edges[(i,j)]=dict(guard_pass=all(not r for r in reasons),
                guard_reasons=[r for r in reasons if r],
                timing=reference_edge_interval(points[i],points[j],uncertain_origin=i!=0))
    original=tuple(range(n+1));original_timing=dict(
        lower_s=sum(edges[(i,i+1)]['timing']['lower_s'] for i in range(n)),
        nominal_s=sum(edges[(i,i+1)]['timing']['nominal_s'] for i in range(n)),
        upper_s=sum(edges[(i,i+1)]['timing']['upper_s'] for i in range(n)))
    # Standard DAG shortest path; no claim of a new search algorithm.
    best={0:(0.,(0,))}
    for j in range(1,n+1):
        candidates=[(best[i][0]+edges[(i,j)]['timing']['upper_s'],best[i][1]+(j,))
                    for i in range(j) if i in best and edges[(i,j)]['guard_pass']]
        if candidates:best[j]=min(candidates,key=lambda v:(v[0],v[1]))
    chosen=best[n][1] if n in best else None
    # Do not introduce a new path for a numerically indistinguishable benefit.
    if chosen is not None and path_sum(original,edges) is not None and math.isclose(
            best[n][0],original_timing['upper_s'],rel_tol=0.,abs_tol=1e-12):
        chosen=original
    if chosen is not None and best[n][0]>original_timing['upper_s']+1e-12:
        chosen=None
    chosen_timing=path_sum(chosen,edges) if chosen is not None else None
    baselines=dict(original_guarded_path=path_sum(original,edges),direct_same_endpoint=path_sum((0,n),edges))
    if compare_exhaustive:
        eligible=[(path_sum(p,edges)['upper_s'],p) for p in all_subsequences(n) if path_sum(p,edges) is not None]
        enumeration=min(eligible,key=lambda v:(v[0],v[1])) if eligible else None
        need((enumeration is None)==(n not in best),'Enumeration/DP coverage disagrees')
        if enumeration is not None:need(math.isclose(enumeration[0],best[n][0],abs_tol=1e-12,rel_tol=0.),'Same-problem optimum disagrees')
        baselines['exhaustive_subsequence_optimum']=None if enumeration is None else dict(path=list(enumeration[1]),upper_s=enumeration[0])
        baselines['exhaustive_paths_evaluated']=1 << (n-1)
    changed=chosen is not None and chosen!=original
    return dict(schema='reach-native-terminal-preserving-stow-path-choice-v1',
        status='OPTIMIZED_REFERENCE_PATH' if changed else 'ORIGINAL_PATH_UNCHANGED_FOR_NATIVE_RECHECK',
        guarded_candidate_found=chosen is not None,
        equivalent_to_direct_baseline=chosen == (0,n),
        distinct_from_original_and_direct=changed and chosen != (0,n),
        assigned_reference_upper_bound_reduction_s=(
            original_timing['upper_s']-chosen_timing['upper_s']
            if chosen_timing is not None and path_sum(original,edges) is not None else None),
        chosen_path_indices=list(chosen or original),changed=changed,
        original_reference_duration_interval_s=original_timing,
        chosen_reference_duration_interval_s=chosen_timing,
        chosen_waypoints=[list(points[i]) for i in (chosen or original)[1:]],
        same_original_compact_endpoint=list(waypoints[-1]),
        unchanged_original_final_verify_min_s=4.,
        objective='upper bound on assigned reference schedule, conditional on original segment transitions',
        actual_total_completion_cost_s=None,actual_successor_repair_cost_s=None,
        native_guard_queries=len(cache),finite_DAG_edges=len(edges),
        edge_witnesses=[dict(source=i,target=j,**e) for (i,j),e in edges.items()],
        baselines=baselines,
        original_runtime_full_path_recheck_required=True,
        original_per_step_support_effort_geometry_and_four_second_verification_required=True,
        later_segment_origin_guard_neighborhood_certified=False,
        finite_guard_pass_is_not_a_continuous_or_dynamic_certificate=True,
        actual_physical_safety_certificate=False,execution_authorized=False)
