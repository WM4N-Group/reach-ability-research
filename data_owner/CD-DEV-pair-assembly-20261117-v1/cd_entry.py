"""Data-owned fresh C/D driver assembly ONLY, default OFF.

Reuse the original AINav/Reach method, common FactorJournal and live driver.
No world, backend, credential, API, optimizer evaluation, step or launcher here.
This component does NOT certify a supported task/provider or admit a main.
"""
from pathlib import Path
import hashlib
import importlib
import importlib.util

SOURCE_PINS = {'method_entry': 'a33da3a64ac01ede274d62730f1ee9e6d30efe02497f02d717d627df7fd7fe9e', 'backbone_entry': 'bd3622d0e0c67278e2aa86c155e557a9ec085661c3700ef601a1aa0ce3e7b81c', 'live_driver': 'ca2e147d5c959fbaed533d20feb900cde91f1e57256d2e1073160aea95282475', 'factor_scope': '9c063a391dfb9c44dfa91d0de0f44bc98adb31e3f34639c3c60cb5fd4f39f424', 'v4_native_asset': '41f29eba2c877f8c5ecbdbf5f526f613cd09f2bf0957665210e4c3db833a0d71'}


class AssemblyError(RuntimeError):
    pass


def need(ok, message):
    if not ok:
        raise AssemblyError(message)


def _verified_imports(source_paths):
    need(type(source_paths) is dict and set(source_paths) == set(SOURCE_PINS),
         'Explicit five frozen source paths, no ambient/parallel entry')
    checked = {}
    for name, pin in SOURCE_PINS.items():
        path = Path(source_paths[name])
        need(not path.is_symlink() and path.is_file() and
             hashlib.sha256(path.read_bytes()).hexdigest() == pin,
             'Exact selected source bytes: ' + name)
        checked[name] = path.resolve()
    # Validate ALL direct module resolutions before executing ANY of them.
    for name, path in checked.items():
        spec = importlib.util.find_spec(name)
        need(spec is not None and spec.origin is not None and
             Path(spec.origin).resolve() == path,
             'Foreign/unresolved module before import: ' + name)
    result = {}
    for name, path in checked.items():
        module = importlib.import_module(name)
        need(Path(module.__file__).resolve() == path,
             'Foreign cached/imported module: ' + name)
        result[name] = module
    return result


def build_cd_driver(components=None, *, arm=None, source_paths=None,
                    source_root=None, reach_source_root=None, bundle=None,
                    output_root=None, writer=None, journal=None, guard=None,
                    backend=None, shared_path_cost=None, enabled=False):
    need(type(enabled) is bool, 'Explicit Data assembly opt-in')
    if not enabled:
        return None
    need(arm in ('C', 'D'), 'Only original C versus D, not E/API0')
    need(callable(guard) and callable(journal) and guard() is not False,
         'Actual new owner/lease/resource guard and durable journal')
    need(type(components) is dict, 'Already constructed fresh components')
    runtime = components['runtime']
    need(runtime.step_count == 0 and float(runtime.sim.data.time) == 0. and
         not runtime.sim.queue and getattr(writer, 'steps', None) == 0,
         'Task-zero runtime/queue/writer, never resume or substitute old zero')
    need(callable(getattr(writer, 'append_command', None)) and
         callable(getattr(writer, 'append_visual', None)),
         'Original command/visual writer, direct live video still separately required')
    need((arm == 'C' and shared_path_cost is None) or
         (arm == 'D' and callable(shared_path_cost)),
         'C unchanged; D needs the explicit common B/D cost callable')
    need(not getattr(shared_path_cost, 'software_fixture', False),
         'Fixture cost cannot enter a production C/D driver')
    modules = _verified_imports(source_paths)
    asset, method = modules['v4_native_asset'], modules['method_entry']
    need(components['scene_sha256'] == asset.SCENE_SHA256 and
         components['scene'] == asset.load_scene(),
         'Existing common V4 task only; no silent easier scene/domain change')
    planner = method.build_original_cd_method(enabled=True, arm=arm,
        source_root=source_root, reach_source_root=reach_source_root,
        backend=backend, journal=journal, guard=guard,
        shared_path_cost=shared_path_cost, software_fixture=False)
    cls = modules['live_driver'].driver_class(source_root=source_root, enabled=True)
    driver = cls(components, bundle=bundle, output_root=output_root,
                 writer=writer, planner=planner, journal=journal, guard=guard, arm=arm)
    factor = modules['factor_scope']
    baseline, roles = method._parts(planner)
    need(driver.r is runtime and driver.arm == arm and driver.planner is planner and
         type(driver.journal) is factor.FactorJournal and
         driver.journal.policy == factor.factors(arm) and
         planner.journal is baseline.journal is roles.journal is driver.journal,
         'One original common-H FactorJournal for wrapper/planner/roles, no proxy reset')
    need(driver.loop is None and driver.executor is None and driver.tick == 0 and
         runtime.step_count == 0 and float(runtime.sim.data.time) == 0. and
         not runtime.sim.queue and writer.steps == 0 and
         baseline.calls == roles.calls == backend.calls == backend.total_tokens == 0 and
         baseline.pending is None,
         'Assembly must not select, issue, generate, reset counters or advance native')
    ref = driver.journal(dict(event='Data_original_CD_driver_assembled_NOT_M1_or_native_ready',
        arm=arm, new_successor_optimizer_enabled=(arm == 'D'),
        original_roles_tree_replanning_common_H_kept=True,
        task_domain_backend_complete_cost_still_not_certified=True,
        same_B_D_provider_identity_still_owner_responsibility=True,
        direct_live_1x_video_required_not_certified_by_assembly=True,
        source_assembly_only=True, method_gain_claimed=False,
        model_input=False, physical_action_issued=False))
    need(type(ref) is str and bool(ref) and guard() is not False,
         'Durable assembly evidence/current owner; no silent fallback')
    return driver
