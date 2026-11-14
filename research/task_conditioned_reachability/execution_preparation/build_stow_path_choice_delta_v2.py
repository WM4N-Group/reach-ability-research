"""New bundle for the source-derived target-view identity repair; v1 immutable."""
import argparse
import hashlib
import json
from pathlib import Path
from .native_stow_path_binding_v2 import transform_stall_source
from .build_stow_path_choice_delta import BASE_RELEASE_SHA, ALIASES, SCOPE_SOURCES

REPAIR_SOURCES=('ainav/native/registered_push_api.py','ainav/native/registered_target_context.py',
                'ainav/native/session_factory.py')


def sha(data):return hashlib.sha256(data).hexdigest()


def build(package,output):
    package,output=Path(package).resolve(),Path(output).resolve()
    raw=(package/'BASELINE_RELEASE_v1.json').read_bytes()
    if sha(raw)!=BASE_RELEASE_SHA:raise ValueError('Exact complete-v6 release')
    if output==package or package in output.parents:raise ValueError('Do not edit selected delivery')
    base=json.loads(raw);pins={};sources={}
    for rel in ALIASES+SCOPE_SOURCES+REPAIR_SOURCES:
        b=(package/'reference-source'/rel).read_bytes()
        if sha(b)!=base['complete_reference_source_files_sha256'][rel]:raise ValueError('Source drift: '+rel)
        pins[rel]=sha(b)
        if rel in ALIASES:sources[rel]=transform_stall_source(b.decode())
    output.mkdir(parents=True,exist_ok=False)
    for rel,text in sources.items():
        p=output/'source-delta'/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text)
    runtime=output/'reach_stow_choice';runtime.mkdir()
    (runtime/'__init__.py').write_text('"""V2 target-view identity repair; default-off, not physically qualified."""\n')
    (runtime/'stow_path_choice.py').write_bytes(Path(__file__).with_name('stow_path_choice.py').read_bytes())
    # Same external import API; new source hash, not a replacement of v1 files.
    (runtime/'native_stow_path_binding.py').write_bytes(Path(__file__).with_name('native_stow_path_binding_v2.py').read_bytes())
    manifest=dict(schema='reach-selected-v6-default-disabled-stow-path-delta-v2',
        selected_release_sha256=BASE_RELEASE_SHA,original_source_sha256=pins,
        changed_original_source_files=list(ALIASES),
        files_sha256={str(p.relative_to(output)):sha(p.read_bytes()) for p in sorted(output.rglob('*.py'))},
        default_enabled=False,physical_execution_authorized=False,not_a_complete_new_whole_program_freeze=True,
        failed_v1_program_sha256='d7d42515dc564556ae54ba91551b76927ebb2766750b5aec2425a3dca3f341d7',
        failed_v1_scope_must_remain_closed=True,old_zero_or_main_must_not_be_reused=True,
        changed_v1_function_only='_selected_session (plus module description)',
        original_reference_law_and_optimizer_core_unchanged=True,
        original_two_alias_capture_hook_unchanged_from_v1=True,
        source_derived_session_factory_repair_tests=8,
        original_selected_factory_and_native_session_constructor_executed_in_CPU_regression=True,
        geometry_Machine_constructor_and_capture_are_explicit_fixtures=True,
        owner_native_environment_requalification_done=False,physically_installed_or_executed=False,
        owner_next_step='New owned v2 intake with actual root-runtime/proxy/target-view graph, not flattened v1 fixture. Do not hot edit/reopen failed v1; a new physical scope still needs new freeze and fresh own-zero.')
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--selected-package',required=True);p.add_argument('--output',required=True)
    a=p.parse_args();print(json.dumps(build(a.selected_package,a.output),indent=2))


if __name__=='__main__':main()
