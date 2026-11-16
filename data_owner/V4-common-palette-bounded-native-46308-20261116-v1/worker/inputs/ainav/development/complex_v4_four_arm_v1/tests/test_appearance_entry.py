"""NEW palette source/spec/model-array METADATA fixtures, not native/rendered.
No NumPy/MuJoCo/Actor/world/renderer/model restore, old MJB or scene edit.
"""
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch
import ast,copy,json,hashlib,struct,sys,unittest
OWN=Path(__file__).resolve().parents[1];ROOT=OWN.parents[1]
sys.path.insert(0,str(OWN));blocked=[]
def fence(event,args):
    if event=='import'and str(args[0]).split('.')[0]in('numpy','torch','mujoco','onnxruntime'):
        blocked.append(str(args[0]));raise RuntimeError('Appearance metadata fixture only')
    if event in('socket.connect','socket.bind','socket.getaddrinfo','subprocess.Popen'):
        blocked.append(event);raise RuntimeError('No network/child/probe')
sys.addaudithook(fence)
import appearance_entry as a
import native_entry

class Array:
    def __init__(self,values,shape):self.values=list(values);self.shape=shape;self.dtype='float32'
    def tobytes(self):return struct.pack('<'+'f'*len(self.values),*self.values)
    def __iter__(self):return iter(self.values)
    def __getitem__(self,i):
        if len(self.shape)==2:return Array(self.values[i*self.shape[1]:(i+1)*self.shape[1]],(self.shape[1],))
        return self.values[i]
class Model:
    def __init__(self):
        for name in a.COUNTS:setattr(self,name,4)
        self.names=b'EXPLICIT_SOFTWARE_names';self.paths=b'EXPLICIT_SOFTWARE_paths'
        self.opt=NS(timestep=.005,gravity=Array([0.,0.,-9.81],(3,)),iterations=100)
        self.ids={name:index for index,name in enumerate(a.palette(a.contract()),1)}
        self.geom_rgba=Array([.1,.1,.1,1.]+a.contract()['old_all_box_rgba']*3,(4,4))
        self.geom_size=Array([1.,1.,1.]*4,(4,3));self.body_mass=Array([1.,.5,.5,.5],(4,))
        self.pair_friction=Array([.8]*4,(4,));self.cam_pos=Array([0.,0.,0.]*4,(4,3))
    def geom(self,name):return NS(id=self.ids[name])

class ExplicitOptionEnum:
    def __init__(self,name,value):self.name=name;self.value=value
    def __int__(self):return self.value

class Tests(unittest.TestCase):
    def setUp(self):self.c=a.contract();self.scene=a.load_scene()
    def spec(self):
        geoms=[NS(name='EXPLICIT_SOFTWARE_floor',rgba=(.1,.2,.3,1.),mass=0.,size=[1.,1.,1.],friction=[.7,0.,0.])]
        for name in a.palette(self.c):geoms.append(NS(name=name,rgba=tuple(self.c['old_all_box_rgba']),mass=.5,size=[1.2,.7,.1],friction=[.4,0.,0.]))
        return NS(data=NS(time=0.),queue=[],spec=NS(geoms=geoms))
    def revised(self):
        before=Model();after=copy.deepcopy(before)
        for name,rgba in a.palette(self.c).items():i=after.ids[name];after.geom_rgba.values[4*i:4*i+4]=rgba
        return before,after
    def test_defaults_off_read_no_contract_source_asset_or_native(self):
        with patch.object(a,'contract',side_effect=AssertionError('No IO')):
            self.assertIsNone(a.apply_fresh_spec_palette(None));self.assertIsNone(a.compile_new_shared_palette_asset())
        self.assertFalse(blocked)
    def test_review_palette_is_explicit_NEW_shared_revision_not_old_approval(self):
        self.assertEqual(self.c['shared_arms'],list('ABCDE'))
        self.assertTrue(self.c['colors_from_existing_review_palette_are_new_NATIVE_appearance_not_previous_approval_claim'])
        self.assertFalse(self.c['physical_success_or_current_visual_association_claimed'])
        self.assertTrue(self.c['all_five_must_freeze_same_new_asset_before_main_not_compare_old_brown_as_same_environment'])
    def test_declared_hues_use_original_distinct_ranges_not_rendered_guarantee(self):
        self.assertEqual(set(a.declared_hue_families(self.c).values()),{'warm','green','violet'})
        bad=copy.deepcopy(self.c);bad['body_geom_review_hex']['complex_box_b_geom']='#e6a23c'
        with self.assertRaises(ValueError):a.declared_hue_families(bad)
    def test_only_three_fresh_spec_rgba_fields_changed_no_material_geometry(self):
        sim=self.spec();old=copy.deepcopy(sim);report=a.apply_fresh_spec_palette(sim,enabled=True,scene=self.scene,guard=lambda:None)
        for before,after in zip(old.spec.geoms,sim.spec.geoms):
            wanted=a.palette(self.c).get(before.name,before.rgba)
            self.assertEqual(after.rgba,wanted)
            self.assertEqual({k:v for k,v in vars(before).items()if k!='rgba'},{k:v for k,v in vars(after).items()if k!='rgba'})
        self.assertFalse(report['compiled_mechanics_or_render_or_native_qualified'])
    def test_missing_or_changed_old_box_validated_before_any_color_write(self):
        for kind in ('missing','wrong_rgba'):
            sim=self.spec()
            if kind=='missing':sim.spec.geoms.pop()
            else:sim.spec.geoms[-1].rgba=(1.,0.,0.,1.)
            before=copy.deepcopy(sim)
            with self.assertRaises(ValueError):a.apply_fresh_spec_palette(sim,enabled=True,guard=lambda:None)
            self.assertEqual([g.rgba for g in sim.spec.geoms],[g.rgba for g in before.spec.geoms])
    def test_live_fifo_scene_edit_or_repeated_revision_refuse(self):
        for kind in ('live','counter','fifo','scene'):
            sim=self.spec();scene=copy.deepcopy(self.scene)
            if kind=='live':sim.data.time=.005
            elif kind=='counter':sim.step_count=1
            elif kind=='fifo':sim.queue.append(object())
            else:scene['objects'][0]['mass_kg']=.6
            with self.assertRaises(ValueError):a.apply_fresh_spec_palette(sim,enabled=True,scene=scene,guard=lambda:None)
        sim=self.spec();a.apply_fresh_spec_palette(sim,enabled=True,guard=lambda:None)
        with self.assertRaises(ValueError):a.apply_fresh_spec_palette(sim,enabled=True,guard=lambda:None)
    def test_second_owner_refusal_leaves_all_spec_colors_untouched(self):
        sim=self.spec();before=[g.rgba for g in sim.spec.geoms];calls=iter([None,False])
        with self.assertRaises(ValueError):a.apply_fresh_spec_palette(sim,enabled=True,guard=lambda:next(calls))
        self.assertEqual(before,[g.rgba for g in sim.spec.geoms])
    def test_original_compiler_code_preserved_private_constructor_only_no_monkeypatch(self):
        previous=native_entry._v4_construct;bound,original=a._bound_palette_compiler(lambda:None)
        self.assertIs(bound.__code__,original.__code__);self.assertIs(native_entry._v4_construct,previous)
        self.assertIsNot(bound.__globals__,original.__globals__)
        self.assertEqual([k for k in original.__globals__ if bound.__globals__[k]is not original.__globals__[k]],['construct_into_native_spec'])
        self.assertEqual(bound.__kwdefaults__,original.__kwdefaults__)
    def test_compiled_metadata_only_rgba_rows_positive_and_readonly(self):
        before,after=self.revised();before.opt.integrator=ExplicitOptionEnum('EULER',0);after.opt.integrator=ExplicitOptionEnum('EULER',0);old=before.geom_rgba.tobytes();out=a.verify_compiled_render_only_delta(before,after)
        self.assertEqual(out['only_changed_array'],'geom_rgba');self.assertEqual(len(out['only_changed_rows']),3)
        self.assertEqual(out['unchanged_nonRGBA_array_count'],4);self.assertEqual(before.geom_rgba.tobytes(),old)
        self.assertFalse(out['actual_render_or_current_association_or_native_admission'])
    def test_nonrgba_mass_contact_calibration_or_engine_option_delta_rejects(self):
        for name in ('body_mass','pair_friction','cam_pos','options','enum','opaque'):
            before,after=self.revised()
            if name=='options':after.opt.timestep=.01
            elif name=='enum':
                before.opt.integrator=ExplicitOptionEnum('EULER',0);after.opt.integrator=ExplicitOptionEnum('RK4',1)
            elif name=='opaque':
                before.opt.unknown=object();after.opt.unknown=object()
            else:getattr(after,name).values[0]+=.01
            with self.assertRaises(ValueError):a.verify_compiled_render_only_delta(before,after)
    def test_fourth_rgba_bad_alpha_dtype_or_row_ids_rejects(self):
        for kind in ('fourth','alpha','dtype','ids'):
            before,after=self.revised()
            if kind=='fourth':after.geom_rgba.values[0]=.2
            elif kind=='alpha':after.geom_rgba.values[7]=.5
            elif kind=='dtype':after.geom_rgba.dtype='float64'
            else:after.ids['complex_box_a_geom']=2
            with self.assertRaises(ValueError):a.verify_compiled_render_only_delta(before,after)
    def test_array_domain_shape_topology_names_or_paths_drift_rejects(self):
        for kind in ('domain','shape','count','names','paths'):
            before,after=self.revised()
            if kind=='domain':after.extra=Array([1.],(1,))
            elif kind=='shape':after.geom_rgba.shape=(4,3)
            elif kind=='count':after.nbody=5
            else:setattr(after,kind,b'EXPLICIT_SOFTWARE_CHANGED')
            with self.assertRaises(ValueError):a.verify_compiled_render_only_delta(before,after)
    def test_new_compiler_guard_refusal_before_reference_or_native_import(self):
        with self.assertRaises(ValueError):a.compile_new_shared_palette_asset(enabled=True,guard=lambda:False)
        self.assertFalse(blocked)
    def test_exact_old_constructor_all_brown_versus_declared_review_palette_source_evidence(self):
        p=OWN.parent/'complex_dual_route_v1/complex_scene.py';raw=p.read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),'613a18e735addf31edfe448e6f46e58ad0c130f4066c9b4393a8720d686d78c0')
        tree=ast.parse(raw);calls=[n for n in ast.walk(tree)if isinstance(n,ast.Call)and any(k.arg=='rgba'and ast.literal_eval(k.value)==[.55,.36,.19,1.]for k in n.keywords if k.arg=='rgba')]
        self.assertEqual(len(calls),1);self.assertNotEqual(len(set(self.c['body_geom_review_hex'].values())),1)
    def test_original_current_detector_and_ambiguity_thresholds_not_modified(self):
        p=ROOT/'consumer-deliveries/AINAV-CLIMB-PREPARATION-CANDIDATES-20261113-v1/common-source/visual_box_proposals.py';raw=p.read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),'837e95ecd7bc3249154b8a53097f71fd90974a2df9fb4a35d87116d0254af304')
        self.assertIn(b'if len(siblings)!=1:raise ValueError',raw);self.assertIn(b'minimum_pixels: int = 64',raw)

if __name__=='__main__':
    r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
    print(json.dumps(dict(role='NEW_SHARED_PALETTE_SOURCE_SPEC_MODEL_ARRAY_METADATA_FIXTURES_NOT_RENDERED_NATIVE_OR_ADOPTED',checks=r.testsRun,failures=len(r.failures),errors=len(r.errors),forbidden_attempts=blocked,actual_MJB_MjModel_MjData_Runtime_renderer_Actor_WM_API_or_physics_calls=0)))
    sys.exit(0 if r.wasSuccessful()and not blocked else 1)
