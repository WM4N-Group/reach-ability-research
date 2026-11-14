"""Read selected release and consume only its ORIGINAL pure entry/support math."""
import argparse
import ast
import importlib
import json
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--package', required=True)
    parser.add_argument('--previous-current-manifest')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    out = Path(args.output); out.mkdir(parents=True, exist_ok=False)
    attempts = []
    def fence(event, values):
        if event in ('socket.connect','socket.getaddrinfo','subprocess.Popen','os.system','os.fork','os.posix_spawn'):
            attempts.append(event); raise RuntimeError('Offline fence: '+event)
        if event == 'import' and str(values[0]).split('.')[0] in ('torch','mujoco','numpy','scipy','onnxruntime','requests','httpx'):
            attempts.append(str(values[0])); raise RuntimeError('No native/model/numeric library import')
    sys.addaudithook(fence)
    from .selected_ainav_baseline import inspect_release, contains, direct_entry_pullback, sha
    result = inspect_release(args.package, previous_current_manifest=args.previous_current_manifest)
    source = Path(args.package)/'reference-source'
    assert 'ainav' not in sys.modules
    sys.path.insert(0, str(source))
    # These original modules contain no runtime/dynamic imports. Never import or
    # instantiate ExecutionJudgedFullCourse, Runtime, planner or old launcher.
    entry = importlib.import_module('ainav.native.execution_judge')
    support = importlib.import_module('ainav.native.push_support_gate')
    pins = {str(Path(p['path']).resolve()):p['sha256'] for p in result['selected_source_subset_pins']}
    for name,module in tuple(sys.modules.items()):
        if name == 'ainav' or name.startswith('ainav.'):
            path = str(Path(module.__file__).resolve())
            assert path in pins and sha(path) == pins[path], 'Unpinned selected dependency'
    host_path = source/'ainav/native/execution_judged_course.py'
    tree = ast.parse(host_path.read_text())
    node = next(n for n in ast.walk(tree) if isinstance(n,ast.Compare) and ast.unparse(n) == '0 < delta <= 0.8')
    expression = compile(ast.Expression(node), str(host_path)+'[original-scalar-stroke-only]', 'eval')
    examples = []
    for x,base in ((1.7,[-.08,-2.]),(1.7,[-1.,-2.]),(2.5,[.72,-2.]),(1.7,[-.08,-1.7])):
        spec = entry.EntrySpec('PUSH','EXPLICIT_FUNCTION_TEST_NOT_ACTUAL_TARGET',(x-1.2-.58,-2.),0.)
        state = entry.EntryState(0.,'0'*64,tuple(base),0.,True,True)
        original = entry.judge_entry(spec,state)
        native_numeric = eval(expression,{'__builtins__':{}},{'delta':2.3+.11-x})
        joint = direct_entry_pullback(2.3,box_length=2.4,lane_y=-2.,base_xy=base)
        ours = joint['joint_direct_box_center_interval'] is not None and contains(joint['joint_direct_box_center_interval'],x)
        expected = original.status == 'READY' and native_numeric
        assert ours == expected
        examples.append(dict(role='EXPLICIT_SOFTWARE_FUNCTION_CHECK_NOT_OBSERVED_STATE',
            center_x_m=x,base_xy_m=base,original_pure_entry_status=original.status,
            original_scalar_numeric_stroke=native_numeric,pullback_direct_numeric_match=ours,
            equality_verified=True,physical_steps=0))
    feet=[[-.2,-.2,.022],[.2,-.2,.022],[-.2,.2,.022],[.2,.2,.022]]
    pass12=support.require_push_source_support([-1.,1.,-1.,1.],0.,feet,[12.]*4)
    rejected=False
    try: support.require_push_source_support([-1.,1.,-1.,1.],0.,feet,[11.9]*4)
    except ValueError: rejected=True
    assert rejected
    result['original_pure_source_function_checks']=examples
    result['original_support_threshold_consumption']=dict(role='EXPLICIT_SOFTWARE_FUNCTION_CHECK',
        original_returned_minimum_load_N=pass12['minimum_load_N'],below12_rejected=rejected,
        old_v9_fourN_threshold_reused=False,actual_support_receipt_produced=False)
    result['fence_attempts']=attempts
    (out/'selected-demand.json').write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    print(json.dumps(dict(baseline=result['baseline'],goals=result['goals'],
        previous_source_relations={kind:sum(v['relation']==kind for v in result['previous_current_source_comparison'])
             for kind in ('IDENTICAL','ABSENT_FROM_SELECTED_BASELINE','DIFFERENT')},
        original_pure_checks=len(examples),fence_attempts=attempts),ensure_ascii=False))


if __name__=='__main__': main()
