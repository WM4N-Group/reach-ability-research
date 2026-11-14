"""Run frozen host unit regressions, no external network or real dynamics.

The B regression binds the additive hook DISABLED to verify original behavior;
separate PHE tests exercise enabled selection. Native zero/main use enabled B.
"""
import argparse,sys,os,json,time,unittest
from pathlib import Path


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);ap.add_argument('--arm',choices=('A','B'),required=True);ap.add_argument('--out',type=Path,required=True);args=ap.parse_args()
    source=args.source.resolve(strict=True);out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
    sys.path.insert(0,str(source))
    def audit(event,values):
        if event=='socket.connect':
            address=values[1]
            if not (isinstance(address,tuple) and address[0] in ('127.0.0.1','::1','localhost')):
                raise PermissionError('No external/API network in CPU qualification')
        if event=='open' and values and isinstance(values[0],str):
            path=values[0]
            if path.startswith('/mnt/yuanyue/data/') and any(x in path for x in ('5311','5312')):
                raise PermissionError('Reserved outcomes are not CPU-test inputs')
    sys.addaudithook(audit)
    import mujoco
    def no_physics(*a,**k):raise AssertionError('No actual mj_step in CPU host qualification')
    mujoco.mj_step=no_physics;mujoco.mj_step1=no_physics;mujoco.mj_step2=no_physics
    def no_renderer(*a,**k):raise AssertionError('Actual Renderer requires separate native zero admission')
    mujoco.Renderer=no_renderer
    if args.arm=='B':
        import mujoco_zyh.stall_stow as module
        from mujoco_zyh.reach_phe_hook import bind_owned_fork
        bind_owned_fork(module,owned_source_root=source,enabled=False,emit=lambda e:None)
    from mujoco_zyh.deepseek_mission_task_NAV_request_physical_protocol import protocol,validate
    p=protocol();validate(p)
    (out/'validated-protocol.json').write_text(json.dumps(p,ensure_ascii=False,indent=2)+'\n')
    began=time.monotonic()
    loader=unittest.TestLoader();suite=loader.discover(str(source),pattern='test_*.py',top_level_dir=str(source))
    with (out/'tests.log').open('x') as log:
        result=unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
    summary=dict(arm=args.arm,tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),skips=len(result.skipped),
                 passed=result.wasSuccessful(),wall_s=time.monotonic()-began,
                 real_physics_or_renderer_allowed=False,external_API_allowed=False,
                 deployed_model_training_started=False,synthetic_NN_operations_possible=True,
                 B_hook_disabled_for_original_regression=args.arm=='B',source=str(source),
                 failures_text=[text for name,text in result.failures],errors_text=[text for name,text in result.errors])
    (out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:summary[k] for k in ('arm','tests','failures','errors','skips','passed','wall_s')},indent=2))
    sys.exit(0 if result.wasSuccessful() else 1)


if __name__=='__main__':main()
