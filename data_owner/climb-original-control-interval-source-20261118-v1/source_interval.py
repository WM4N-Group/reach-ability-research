"""Source-only CLIMB interval adapter, no world/Actor/native import/dispatch on import.

The future parent must keep original constructor/RNG/initial observation and
supply real external physical issue+ACK at each yield. This module is NOT that
owner, registered 12N admission, safety wrapper, finally or complete program.
"""
import ast
import copy
import hashlib
from pathlib import Path

PLAY_SHA256='8fe257c698152785e07a4a0e61e77474cb76ba7382a6da028d008539fc46f0df'


def derive(play_path=None,*,enabled=False):
    if type(enabled)is not bool:raise ValueError('Explicit source-only opt-in')
    if not enabled:return None
    p=Path(play_path);raw=p.read_bytes()
    if p.is_symlink()or hashlib.sha256(raw).hexdigest()!=PLAY_SHA256:
        raise ValueError('Exact original CLIMB play source bytes required')
    tree=ast.parse(raw)
    main=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='main')
    outer=next(n for n in ast.walk(main)if isinstance(n,ast.For)and isinstance(n.target,ast.Name)and n.target.id=='step'and 'episode_seconds' in ast.unparse(n.iter))
    body=outer.body
    infer=next(n for n in body if isinstance(n,ast.With)and ast.unparse(n.items[0].context_expr)=='torch.inference_mode()')
    set_action=next(n for n in body if isinstance(n,ast.Expr)and isinstance(n.value,ast.Call)and ast.unparse(n.value.func)=='sim.set_action')
    physical=next(n for n in body if isinstance(n,ast.For)and ast.unparse(n.iter)=="range(cfg['decimation'])")
    if (len(physical.body)!=4 or ast.unparse(physical.body[1])!='sim.physics_step(command)'or
        ast.unparse(physical.body[2])!='if stop is not None:\n    stop.after_step()'):
        raise ValueError('Original physical/after_step/trace shape changed')
    # Retain the exact ORIGINAL command expression, including None meaning
    # physics_step's own default policy command in original ascent-only mode.
    inner=copy.deepcopy(physical)
    inner.body=copy.deepcopy(physical.body[:3])
    inner.body[1]=ast.copy_location(ast.Expr(ast.Yield(ast.Name('command',ast.Load()))),physical.body[1])
    finite=next(n for n in body if isinstance(n,ast.If)and 'np.isfinite(sim.data.qpos)' in ast.unparse(n.test))
    status=next(n for n in body if isinstance(n,ast.Assign)and ast.unparse(n.value)=='sim.status()')
    stop_status=next(n for n in body if isinstance(n,ast.If)and ast.unparse(n)=='if stop is not None:\n    state, reason = stop.status(state, reason)')
    observation=next(n for n in body if isinstance(n,ast.Assign)and ast.unparse(n.value)=='sim.observation()')
    parts=[copy.deepcopy(n)for n in (infer,set_action)]+[inner]+[copy.deepcopy(n)for n in (finite,status,stop_status,observation)]
    function=ast.FunctionDef(name='original_control_interval_requests',
        args=ast.arguments(posonlyargs=[],args=[ast.arg(arg=x)for x in ('sim','actor','args','cfg','stop','obs')],kwonlyargs=[],kw_defaults=[],defaults=[]),
        body=parts+[ast.Return(ast.Tuple([ast.Name(x,ast.Load())for x in ('state','reason','obs')],ast.Load()))],decorator_list=[])
    module=ast.fix_missing_locations(ast.Module(body=[function],type_ignores=[]))
    # Prove exact retained control AST, rather than claim to run original main.
    proof=dict(original_play_SHA256=PLAY_SHA256,
        original_actor_infer_and_set_action_AST_unchanged=True,
        original_command_expression_and_after_step_AST_unchanged=True,
        original_finite_status_stop_status_and_observation_AST_unchanged=True,
        sole_physics_call_replaced_by_external_command_yield=True,
        original_trace_viewer_capture_print_sleep_IO_omitted_not_algorithm_equivalence_of_full_main=True,
        control_interval_only_not_outer_loop_or_terminal_success=True,
        caller_must_start_with_original_initial_observation=True,
        caller_must_ack_each_yield_and_drain_final_return_without_extra_physics_or_new_Actor=True,
        no_world_or_registered_owner_safety_finally_or_complete_program=True,
        source_only_not_execution_permission=True)
    for original,generated in zip((infer,set_action,finite,status,stop_status,observation),
                                 (parts[0],parts[1],parts[3],parts[4],parts[5],parts[6])):
        if ast.dump(original,include_attributes=False)!=ast.dump(generated,include_attributes=False):
            raise ValueError('Retained original algorithm AST changed')
    text=ast.unparse(module)+'\n';compile(text,str(p)+'[one-control-interval-external-physics-requests]','exec',dont_inherit=True)
    proof['generated_control_source_SHA256']=hashlib.sha256(text.encode()).hexdigest()
    return text,proof
