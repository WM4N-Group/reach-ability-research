"""Write a NEW local two-alias delta bundle, never edit selected reference-source."""
import argparse
import hashlib
import json
from pathlib import Path
from .native_stow_path_binding import transform_stall_source

BASE_RELEASE_SHA = '3098297041dbfa50dd1928ee81ce28c68d3458ed544cc494dea7374177b7c49e'
ALIASES = ('mujoco_zyh/stall_stow.py', 'ainav/native/current_stall_stow.py')
SCOPE_SOURCES = ('ainav/native/placement_handoff.py', 'ainav/native/full_verified_placement.py',
                 'mujoco_zyh/moving_push_exit.py', 'mujoco_zyh/native_behavior_executor.py')


def sha(data): return hashlib.sha256(data).hexdigest()


def build(package, output):
    package, output = Path(package).resolve(), Path(output).resolve()
    raw = (package/'BASELINE_RELEASE_v1.json').read_bytes()
    if sha(raw) != BASE_RELEASE_SHA:
        raise ValueError('Exact selected complete-v6 release required')
    base = json.loads(raw)
    if output == package or package in output.parents:
        raise ValueError('Never modify the read-only selected delivery')
    sources = {}; pins = {}
    for rel in ALIASES+SCOPE_SOURCES:
        b = (package/'reference-source'/rel).read_bytes()
        if sha(b) != base['complete_reference_source_files_sha256'][rel]:
            raise ValueError('Selected source pin drift: '+rel)
        pins[rel] = sha(b)
        if rel in ALIASES: sources[rel] = transform_stall_source(b.decode())
    output.mkdir(parents=True, exist_ok=False)
    for rel, text in sources.items():
        p = output/'source-delta'/rel;p.parent.mkdir(parents=True, exist_ok=True);p.write_text(text)
    runtime = output/'reach_stow_choice';runtime.mkdir()
    (runtime/'__init__.py').write_text('"""Default-disabled Reach selected-v6 path-choice delta."""\n')
    for name in ('stow_path_choice.py', 'native_stow_path_binding.py'):
        (runtime/name).write_bytes(Path(__file__).with_name(name).read_bytes())
    manifest = dict(schema='reach-selected-v6-default-disabled-stow-path-delta-v1',
                    selected_release_sha256=BASE_RELEASE_SHA, original_source_sha256=pins,
                    changed_original_source_files=list(ALIASES),
                    files_sha256={str(p.relative_to(output)):sha(p.read_bytes()) for p in sorted(output.rglob('*.py'))},
                    default_enabled=False, physical_execution_authorized=False,
                    not_a_complete_new_whole_program_freeze=True,
                    owner_next_step='AINav/Data: new owned fork, bind_to_host on both loaded aliases, new whole-program freeze/own-zero; old scopes closed')
    (output/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    return manifest


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--selected-package',required=True);p.add_argument('--output',required=True)
    a=p.parse_args();print(json.dumps(build(a.selected_package,a.output),indent=2))


if __name__ == '__main__': main()
