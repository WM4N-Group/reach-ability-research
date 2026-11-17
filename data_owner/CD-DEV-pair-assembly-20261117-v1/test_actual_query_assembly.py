"""New Data source delta/order checks; stub assembly is NOT a native backend.

Do not repeat AINav's original roles/query suite. Real selected source bytes are
read on CPU; all factory-order tests use explicit synthetic factories/drivers.
"""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parent))
import cd_entry as entry
import prepare_pair
import source_selection as selection
HERE = Path(__file__).resolve().parent


def protocol():
    return json.loads((HERE/'CD_DEV_PROTOCOL_DRAFT.json').read_text())


class SourceDelta(unittest.TestCase):
    def test_selected_real_7_plus_5_bytes_and_declarations_without_import(self):
        with patch.object(entry.importlib, 'import_module', side_effect=AssertionError('no import')):
            r = prepare_pair.preview(protocol(), enabled=True)
        self.assertEqual(len(r['source_pins']), 12)
        self.assertFalse(r['dispatchable'])
        self.assertFalse(r['full_native_import_closure_qualified'])
        self.assertTrue(r['DEV_task_and_RNG_and_caps_prospectively_selected'])

    def test_old_v2_same_other_direct_sources_is_refused_before_import(self):
        p = protocol(); p['source_paths']['method_entry'] = str(Path(p['source_paths']['method_entry']).parent.parent/'complex_v4_method_current_reach_v2/method_entry.py')
        with patch.object(entry.importlib, 'import_module', side_effect=AssertionError), self.assertRaises(prepare_pair.ProtocolError):
            prepare_pair.preview(p, enabled=True)

    def test_Reach_drift_refused_even_all_seven_direct_sources_match(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); base=root/selection.REACH_PACKAGE.replace('.', '/');base.mkdir(parents=True)
            real = Path(protocol()['common']['reach_source_root_reference'])/selection.REACH_PACKAGE.replace('.', '/')
            for name in selection.REACH_PINS:
                (base/name).write_bytes((real/name).read_bytes())
            (base/'v4_reference_cost.py').write_bytes(b'# drift, do not execute\n')
            p = protocol();p['common']['reach_source_root_reference']=td
            with patch.object(entry.importlib, 'import_module', side_effect=AssertionError), self.assertRaises(prepare_pair.ProtocolError):
                prepare_pair.preview(p, enabled=True)

    def test_selected_transitive_drift_before_any_direct_import(self):
        with patch.object(entry, 'verify_reach_sources', side_effect=ValueError('drift')), patch.object(entry.importlib, 'import_module') as imp, self.assertRaises(ValueError):
            entry._verified_imports(protocol()['source_paths'], reach_source_root='no read')
        imp.assert_not_called()

    def test_task_seed_caps_or_command_budget_change_refused(self):
        mutations=[lambda c:c['supported_DEV_task_and_initialization']['initialization'].update(Python_random_seed=3),
                   lambda c:c['task_wall_sim_caps'].update(task_sim_s_each=61),
                   lambda c:c['task_loop_limits'].update(max_commands=12001),
                   lambda c:c['supported_DEV_task_and_initialization']['public_domain'].update(goal='V4')]
        for mutate in mutations:
            p=protocol();mutate(p['common'])
            with self.subTest(p=p['common']['task_loop_limits']), self.assertRaises(prepare_pair.ProtocolError):
                prepare_pair.preview(p, enabled=True)

    def test_declaration_drift_and_symlink_refused_without_live_file_changes(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'declaration.json';p.write_text('{}')
            with self.assertRaises(ValueError):selection.checked_bytes(p, selection.DECLARATION_PINS['NAV_DEV_DECLARATION.json'])
            alias=Path(td)/'alias.json';alias.symlink_to(p)
            with self.assertRaises(ValueError):selection.checked_bytes(alias,hashlib.sha256(p.read_bytes()).hexdigest())

    def test_provider_is_declaration_only_not_initial_state_or_private_pose(self):
        c=selection.provider_config(protocol())
        self.assertEqual(c['required_visit_refs'],('v4-ground-nav-008','v4-ground-nav-001'))
        self.assertEqual(c['declared_bounds_xyxy'],(-1.,-3.4,.75,3.4))
        self.assertNotIn('initial_state', c); self.assertNotIn('initial_reference_source_ref', c)
        self.assertTrue(c['public_map_source_ref'].startswith('declared:'))
        self.assertEqual(protocol()['common']['supported_DEV_task_and_initialization']['initialization']['Python_random_seed'],2026111701)


class OrderDelta(unittest.TestCase):
    def fixture(self, arm):
        log=[];p=protocol();cost=object();planner=object();caller=object()
        driver=NS(planner=planner,owner_guard=lambda:True)
        def cost_factory(**kw):
            log.append(('cost',kw));return cost
        def original_driver(*args,**kw):
            log.append(('driver',kw));return driver
        def attach(**kw):
            log.append(('prelude',kw));return caller
        def bind(**kw):
            log.append(('boundary',kw));return planner
        modules={'nav_query_boundary':NS(build_query_bound_nav_cost=cost_factory,bind_original_d_query_boundary=bind),
                 'common_nav_prelude':NS(attach_common_nav_prelude=attach)}
        kwargs=dict(protocol=p,arm=arm,enabled=True,reach_source_root=p['common']['reach_source_root_reference'])
        return log, cost, driver, caller, modules, kwargs, original_driver

    def test_default_off_no_sources_no_guard_no_import(self):
        with patch.object(entry,'_verified_imports',side_effect=AssertionError), patch.object(entry,'provider_config',side_effect=AssertionError):
            self.assertIsNone(entry.assemble_nav_dev_sources('/DO_NOT_READ'))

    def test_D_cost_original_driver_final_journal_prelude_boundary_in_order(self):
        log,cost,driver,caller,mods,kw,factory=self.fixture('D')
        with patch.object(entry,'_verified_imports',return_value=mods),patch.object(entry,'build_cd_driver',side_effect=factory):
            result=entry.assemble_nav_dev_sources({},**kw)
            self.assertIs(result.driver,driver)
            self.assertFalse(result.dispatchable)
            self.assertFalse(result.DEV_acquisition_and_receipt_terminal_complete)
        self.assertEqual([x[0]for x in log],['cost','driver','prelude','boundary'])
        self.assertIs(log[1][1]['shared_path_cost'],cost)
        self.assertIs(log[-1][1]['path_cost'],cost)
        self.assertIs(log[-1][1]['common_caller'],caller)
        self.assertIs(log[-1][1]['planner'],driver.planner)
        self.assertFalse(log[0][1]['software_fixture']);self.assertFalse(log[2][1]['software_fixture'])

    def test_C_same_common_prelude_no_cost_no_boundary(self):
        log,cost,driver,caller,mods,kw,factory=self.fixture('C')
        with patch.object(entry,'_verified_imports',return_value=mods),patch.object(entry,'build_cd_driver',side_effect=factory):
            result=entry.assemble_nav_dev_sources({},**kw)
            self.assertIs(result.driver,driver)
            self.assertFalse(result.dispatchable)
            self.assertFalse(result.DEV_acquisition_and_receipt_terminal_complete)
        self.assertEqual([x[0]for x in log],['driver','prelude'])
        self.assertIsNone(log[0][1]['shared_path_cost'])

    def test_boundary_error_propagates_once_no_C_fallback_or_counter_reset(self):
        log,cost,driver,caller,mods,kw,factory=self.fixture('D')
        def fail(**kw):log.append(('refusal',kw));raise RuntimeError('synthetic seam refusal')
        mods['nav_query_boundary'].bind_original_d_query_boundary=fail
        with patch.object(entry,'_verified_imports',return_value=mods),patch.object(entry,'build_cd_driver',side_effect=factory),self.assertRaises(RuntimeError):
            entry.assemble_nav_dev_sources({},**kw)
        self.assertEqual([x[0]for x in log],['cost','driver','prelude','refusal'])

    def test_alternate_cost_or_source_refused_before_import(self):
        for extra in [dict(shared_path_cost=lambda:None),dict(source_paths={})]:
            with patch.object(entry,'_verified_imports')as imp,self.assertRaises(entry.AssemblyError):
                entry.assemble_nav_dev_sources({},protocol=protocol(),arm='D',enabled=True,**extra)
            imp.assert_not_called()

    def test_boundary_must_keep_original_D_identity(self):
        log,cost,driver,caller,mods,kw,factory=self.fixture('D')
        mods['nav_query_boundary'].bind_original_d_query_boundary=lambda **kw:object()
        with patch.object(entry,'_verified_imports',return_value=mods),patch.object(entry,'build_cd_driver',side_effect=factory),self.assertRaises(entry.AssemblyError):
            entry.assemble_nav_dev_sources({},**kw)


if __name__=='__main__':unittest.main(verbosity=2)
