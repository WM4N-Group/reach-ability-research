"""Four new parser/order checks only, no GPU, lock, H edit, native or old auditor."""
from pathlib import Path
import ast,json,sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parent))
from phase_control import require_no_foreign_target_compute,ResourceNotReady
G0='GPU-297c1146-bcec-a8ee-8437-d9603392a2e1'
G1='GPU-6d66aa68-9a3f-fdcf-89b7-f98d4106fa39'
FREE=f'0, {G0}, 24080, 0\n1, {G1}, 23000, 20\n'

class FutureAdmission(unittest.TestCase):
    def test_recorded_failed_main_preflight_would_now_stop_inside_controller(self):
        p=Path('/home/yuanyue/main/work/data-team/manifests/push-standard-parent-20261118-v1/actual-main/predispatch-fresh-remote.json')
        j=json.loads(p.read_bytes())
        self.assertTrue(all(not r['holders']for r in j['locks']))
        # Real fresh_remote inventory has an EXTRA memory.used column; controller
        # asks its four-field schema. Keep the actual target busy row verbatim.
        gpu='\n'.join(', '.join([r[0],r[1],r[3],r[4]])for line in j['gpu'].splitlines()if (r:=[x.strip()for x in line.split(',')]))
        with self.assertRaisesRegex(ResourceNotReady,'another compute PID'):
            require_no_foreign_target_compute(gpu,j['gpu_compute'])

    def test_other_card_busy_does_not_permanently_assign_or_block_this_card(self):
        row=f'12345, {G1}, 1024\n'
        r=require_no_foreign_target_compute(FREE,row)
        self.assertEqual(r['foreign_target_compute_PIDs'],[])
        self.assertTrue(r['later_race_not_excluded'])

    def test_unknown_capacity_UUID_schema_or_own_target_PID_never_defaults_zero(self):
        for gpu,apps in [(FREE.replace('24080','N/A'),''),(FREE+'0, '+G0+', 24080, 0\n',''),
                         (FREE,'unknown'),(FREE,f'123, {G0}, N/A'),(FREE.replace('24080','4095'),'')]:
            with self.assertRaises(ResourceNotReady):require_no_foreign_target_compute(gpu,apps)

    def test_guard_is_on_the_same_path_before_any_authorization_or_child(self):
        tree=ast.parse(Path(__file__).with_name('phase_control.py').read_text())
        fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='execute')
        calls=[(n.lineno,ast.unparse(n.func))for n in ast.walk(fn)if isinstance(n,ast.Call)]
        gate=next(n for n,name in calls if name=='require_no_foreign_target_compute')
        self.assertLess(gate,min(n for n,name in calls if name in ('cas','ControlledProcess')))

    def test_actual_busy_precheck_stops_shell_before_controller_handoff(self):
        import subprocess,tempfile,shlex
        here=Path(__file__).resolve().parent
        snapshot=Path('/home/yuanyue/main/work/data-team/manifests/push-standard-parent-20261118-v1/actual-main/predispatch-fresh-remote.json')
        with tempfile.TemporaryDirectory()as td:
            marker=Path(td)/'controller-was-called'
            precheck=("import sys,json;sys.path.insert(0,"+repr(str(here))+");"
                "from phase_control import require_no_foreign_target_compute;"
                "j=json.load(open("+repr(str(snapshot))+"));"
                "rows=[[v.strip()for v in x.split(',')]for x in j['gpu'].splitlines()if x.strip()];"
                "gpu='\\n'.join(', '.join([r[0],r[1],r[3],r[4]])for r in rows);"
                "require_no_foreign_target_compute(gpu,j['gpu_compute'])")
            controller="from pathlib import Path;Path("+repr(str(marker))+").write_text('NOT_ALLOWED')"
            command=shlex.join([sys.executable,'-c',precheck])+'; '+shlex.join([sys.executable,'-c',controller])
            result=subprocess.run(['bash','-e','-u','-o','pipefail','-c',command],capture_output=True)
            self.assertNotEqual(result.returncode,0)
            self.assertIn(b'ResourceNotReady',result.stderr)
            self.assertIn(b'another compute PID',result.stderr)
            self.assertFalse(marker.exists())

if __name__=='__main__':unittest.main()
