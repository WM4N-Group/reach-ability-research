"""Persist a clearly labelled synthetic, source-level consumer witness."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import sys
from .test_native_stow_path_binding import NativeSourceBindingTests, SOURCE
from .native_stow_path_binding import transform_stall_source


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True);a=p.parse_args()
    attempts=[]
    def fence(event,values):
        if event in ('socket.connect','socket.getaddrinfo','subprocess.Popen','os.system','os.fork','os.posix_spawn'):
            attempts.append(event);raise RuntimeError('CPU-only source proof fence: '+event)
        if event=='import' and str(values[0]).split('.')[0] in ('numpy','torch','mujoco','scipy','onnxruntime','requests','httpx'):
            attempts.append(str(values[0]));raise RuntimeError('No native numerical/physical/model stack')
    sys.addaudithook(fence)
    t=NativeSourceBindingTests();t.setUp();rows=[]
    try:
        for mode in ('original_source','delta_default_disabled','delta_enabled_direct_open','delta_enabled_direct_blocked','delta_enabled_A_prefix'):
            blocked=mode=='delta_enabled_direct_blocked'
            f=t.fixture(transformed=mode!='original_source',enabled=mode not in ('original_source','delta_default_disabled'),
                        guard=(lambda a,b:'fixture direct blocked' if a[0]==0 and b[0]==.1 else '') if blocked else None)
            if mode=='delta_enabled_A_prefix':f.host.executor.session=None
            f.owner.update();duration=f.owner.segment_duration
            desired=t.command_desired(f)
            rows.append(dict(mode=mode,role='SYNTHETIC_CPU_SOURCE_FIXTURE_NOT_ACTUAL_GEOMETRY',
                original_queue_screen_fixture_called=len(t.queue_calls),
                consumed_waypoints=[list(q) for q in f.owner.waypoints],
                consumed_native_begin_segment_duration_s=duration,
                consumed_original_command_select_reference_desired_at_half_segment=list(desired),
                selector_records=t.emitted,stop_boundary='original select_reference arguments; before real guard/QP/FIFO/motors'))
    finally:t.doCleanups()
    source=SOURCE.read_text();changed=transform_stall_source(source)
    cls=next(n for n in ast.parse(source).body if isinstance(n,ast.ClassDef) and n.name=='ProtectedStow')
    methods={n.name:hashlib.sha256(ast.dump(n,include_attributes=False).encode()).hexdigest()
             for n in cls.body if isinstance(n,ast.FunctionDef) and n.name in ('update','begin_segment','command')}
    result=dict(schema='reach-selected-v6-CPU-source-consumption-proof-v1',
        original_source_sha256=hashlib.sha256(source.encode()).hexdigest(),
        transformed_source_sha256=hashlib.sha256(changed.encode()).hexdigest(),original_method_AST_sha256=methods,
        actual_original_method_code_executed=['update','begin_segment','command prefix through desired/select_reference call'],
        real_NumPy_geometry_support_capture_queue_NN_QP_or_physics_executed=False,
        motors_commands_or_API_issued=0, actual_safety_or_total_cost_bound_proven=False,
        fixtures=rows,fence_attempts=attempts)
    out=Path(a.output);out.mkdir(parents=True,exist_ok=False)
    (out/'CPU_SOURCE_CONSUMPTION_NOT_PHYSICS.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({r['mode']:dict(path_len=len(r['consumed_waypoints']),first_segment_s=r['consumed_native_begin_segment_duration_s']) for r in rows},indent=2))


if __name__=='__main__':main()
