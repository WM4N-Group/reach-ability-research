"""New static-case declarations only; no model/world/Actor or old suites."""
import importlib.util
from pathlib import Path
import subprocess
import sys
import unittest

D=Path(__file__).parent
sys.path.insert(0,str(D))
import standard_asset

class StandardBoundaries(unittest.TestCase):
    def test_default_off_never_constructs(self):
        self.assertIsNone(standard_asset.build(enabled=False))
        self.assertIsNone(standard_asset.declaration(enabled=False))
        out=subprocess.run([sys.executable,'-I','-B',str(D/'asset_worker.py')],capture_output=True,check=True)
        self.assertEqual((out.stdout,out.stderr),(b'',b''))

    def test_actual_generic_registry_standard_one_box(self):
        P=Path('/home/yuanyue/main/work/ainav/src/ainav/native/scene_registry.py')
        spec=importlib.util.spec_from_file_location('_std_actual_scene_registry',P)
        module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
        reg=standard_asset.declaration(module,enabled=True)
        self.assertEqual(reg.objects['sdk_box'].size_m,(1.2,1.2,.2))
        self.assertEqual(len(reg.objects),1)
        self.assertEqual(standard_asset.CASE['box_mass_kg'],1.)
        self.assertEqual(standard_asset.CASE['native_drive_goal_xy_m'],[1.7,0.])

    def test_v4_validator_remains_strict_not_repurposed(self):
        P=Path('/home/yuanyue/main/work/ainav/development/complex_dual_route_v1/complex_scene.py')
        spec=importlib.util.spec_from_file_location('_std_unchanged_v4_scene',P)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        scene=dict(schema='AINav-T-COMPLEX-01-native-scene-v1',seed=4301,robot_initial_yaw_rad=0.,objects=[dict(public_ref='sdk_box')])
        with self.assertRaisesRegex(ValueError,'Two/three distinct'):
            module.validate(scene)

if __name__=='__main__':unittest.main()
