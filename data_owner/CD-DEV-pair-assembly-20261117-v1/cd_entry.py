"""Data-owned fresh C/D driver assembly ONLY, default OFF.

Reuse the original AINav/Reach method, common FactorJournal and live driver.
No world, backend, credential, API, optimizer evaluation, step or launcher here.
This component does NOT certify a supported task/provider or admit a main.
"""
from dataclasses import dataclass
from pathlib import Path
import hashlib
import importlib
import importlib.util
from source_selection import verify_reach_sources, provider_config

SOURCE_PINS = {'common_nav_prelude': 'c29fe523309299c35ed0620aed285559bde27245a8641b5a6f05b4a1d6c9d202', 'nav_query_boundary': '0dde4a690655507fda0a40f75c84d9a5d64f449851607f42ccdfb333ca46fcf6', 'method_entry': 'b9a3960b56e8c4247d206229fffd65da66e4e29f1591d2f1cacb89a67d10d80a', 'backbone_entry': 'bd3622d0e0c67278e2aa86c155e557a9ec085661c3700ef601a1aa0ce3e7b81c', 'live_driver': 'ca2e147d5c959fbaed533d20feb900cde91f1e57256d2e1073160aea95282475', 'factor_scope': '9c063a391dfb9c44dfa91d0de0f44bc98adb31e3f34639c3c60cb5fd4f39f424', 'v4_native_asset': '41f29eba2c877f8c5ecbdbf5f526f613cd09f2bf0957665210e4c3db833a0d71'}


class AssemblyError(RuntimeError):
    pass


def need(ok, message):
    if not ok:
        raise AssemblyError(message)


def _verified_imports(source_paths, *, reach_source_root=None):
    need(type(source_paths) is dict and set(source_paths) == set(SOURCE_PINS),
         'Explicit selected v3 source paths, no ambient/parallel entry')
    checked = {}
    for name, pin in SOURCE_PINS.items():
        path = Path(source_paths[name])
        need(not path.is_symlink() and path.is_file() and
             hashlib.sha256(path.read_bytes()).hexdigest() == pin,
             'Exact selected source bytes: ' + name)
        checked[name] = path.resolve()
    if reach_source_root is not None:
        verify_reach_sources(reach_source_root)
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
    modules = _verified_imports(source_paths, reach_source_root=reach_source_root)
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


@dataclass(frozen=True)
class NavDevSourceAssembly:
    """In-process source result, NOT a driver accepted by task_loop.run_task."""
    driver: object
    common_caller: object
    cost: object

    @property
    def dispatchable(self):
        return False

    @property
    def DEV_acquisition_and_receipt_terminal_complete(self):
        return False


def assemble_nav_dev_sources(components=None, *, protocol=None, arm=None, enabled=False, **kwargs):
    """Task-zero source assembly in the v3-required order, default OFF.

    This is NOT the independent DEV acquisition/receipt terminal adapter or an
    executable worker. Original V4 driver success is NOT DEV success. Parent must
    finish that adapter and full qualification before any loop may execute.
    No cost evaluation/query/step occurs here; partial failure is never retried.
    """
    need(type(enabled) is bool, 'Explicit new DEV source assembly opt-in')
    if not enabled:
        return None
    need(arm in ('C', 'D'), 'Only declared C/D arms')
    need('shared_path_cost' not in kwargs and 'source_paths' not in kwargs,
         'Selected protocol owns cost and source selection; no alternate provider')
    config = provider_config(protocol)  # Validated for BOTH arms, identical public domain.
    sources = protocol['source_paths']
    modules = _verified_imports(sources, reach_source_root=kwargs['reach_source_root'])
    seam = modules['nav_query_boundary']
    cost = None
    if arm == 'D':
        cost = seam.build_query_bound_nav_cost(enabled=True,
            reach_source_root=kwargs['reach_source_root'], provider_config=config,
            software_fixture=False)
    driver = build_cd_driver(components, arm=arm, source_paths=sources,
                             shared_path_cost=cost, enabled=True, **kwargs)
    caller = modules['common_nav_prelude'].attach_common_nav_prelude(enabled=True,
        driver=driver, reach_source_root=kwargs['reach_source_root'], software_fixture=False)
    if arm == 'D':
        bound = seam.bind_original_d_query_boundary(enabled=True, planner=driver.planner,
                                                   path_cost=cost, common_caller=caller)
        need(bound is driver.planner, 'Original D planner identity retained')
    need(driver.owner_guard() is not False, 'Final source assembly owner guard')
    return NavDevSourceAssembly(driver, caller, cost)
