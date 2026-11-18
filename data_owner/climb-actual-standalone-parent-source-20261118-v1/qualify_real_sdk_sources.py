"""Actual private CPU SOURCE import prepare, NOT a full program/native prepare.

No mock SDK/module table, Model/MjData/Actor/Stop construction, GPU/lease/physics.
"""
from pathlib import Path
import datetime,hashlib,importlib.util,json,resource,sys,time
START=time.perf_counter();HERE=Path(__file__).resolve().parent
SDK,OWNER,INTERVAL=map(Path,sys.argv[1:4])
spec=importlib.util.spec_from_file_location('_actual_climb_standalone_parent_source',HERE/'standalone_parent.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
assert m.prepare(enabled=False)is None
assembly=m.prepare(SDK,owner_source=OWNER,interval_source=INTERVAL,enabled=True)
assert assembly.model is assembly.sim is assembly.actor is assembly.stop is None
assert not assembly.construct_started and not assembly.construct_completed
assert assembly.construct(enabled=False)is None
# No fake native class substitutions: wrong/closed PUSH context is rejected by
# the real source parent's gate before ALL native constructors and Actor load.
try:assembly.construct(context=dict(question='PUSH_PREPARED_L0_REGISTERED_ARM_LIVE_BIAS_ONLY_FIRST_BOUNDARY'),lease=None,parent_check=lambda:True,enabled=True)
except ValueError:pass
else:raise AssertionError('Source fixture/old PUSH must never grant CLIMB native context')
assert not assembly.construct_started and not any(assembly.flags.values())
expected=assembly.expected_original_rng()
assert expected['xyz'].shape==(3,)and expected['joints'].shape==(18,)and len(expected['group_delays'])==7
assert not assembly.torch.cuda.is_initialized()
assert assembly.bridge.ClimbBridge.__init__.__code__.co_filename==str(SDK/'climb/bridge.py')
assert assembly.stop_module.StopController.__init__.__code__.co_filename==str(SDK/'climb/stop.py')
print(json.dumps(dict(at=datetime.datetime.now().astimezone().isoformat(),**assembly.receipt,
 cpu_source_wall_s=time.perf_counter()-START,process_maxrss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
 exact_case_source_only_not_authorization=m.CASE,
 expected_seeded_initial_conditions_NOT_NATIVE_OBSERVATIONS=dict(root_xyz_m=expected['xyz'].tolist(),quaternion_wxyz=expected['quaternion'].tolist(),
  original_group_delays_before_override=expected['group_delays'].tolist(),original_joint_initial_rad=expected['joints'].tolist(),prospective_override_delays_physics_ticks=[4]*18,
  computed_from_original_seeded_draw_order_no_world=True),
 real_SDK_classes=dict(bridge_module_file=assembly.bridge.__file__,Stop_module_file=assembly.stop_module.__file__,
  bridge_constructor_filename=assembly.bridge.ClimbBridge.__init__.__code__.co_filename,
  Stop_constructor_filename=assembly.stop_module.StopController.__init__.__code__.co_filename),
 rejected_non_CLIMB_context_before_construction=True,construction_flags=assembly.flags,partial_snapshot=assembly.partial_snapshot(),
 tested_source_SHA256={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in(HERE/'standalone_parent.py',HERE/'qualify_real_sdk_sources.py',OWNER,INTERVAL)},
 complete_native_parent_auth_registered_safety_IO_finally_qualification=False),ensure_ascii=False,indent=2))
