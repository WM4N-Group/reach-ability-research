#!/usr/bin/env python3
"""Export a code-only custody snapshot without changing the working Git index.

An export is NOT a runtime freeze, authority transfer, native qualification or
permission to replay closed scopes. Destination must not exist. Never copies
credentials, environments, model weights, datasets or raw experiment evidence.
"""
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

TEXT_EXTENSIONS={'.py','.sh','.bash','.json','.yaml','.yml','.toml','.xml','.urdf',
                 '.mjcf','.cfg','.ini','.txt','.md','.rst','.cpp','.cc','.c','.h',
                 '.hpp','.cmake','.in','.usda','.gitignore','.gitattributes'}
ROOT_FILES={'LICENSE','CODE_OF_CONDUCT.md','CONTRIBUTING.md','pyproject.toml',
            'requirements.txt','.gitignore','.gitattributes','.pre-commit-config.yaml'}
EXCLUDED_PARTS={'.git','__pycache__','.pytest_cache','node_modules','evidence',
                'artifacts','outputs','output','logs','runs','checkpoints','datasets',
                'videos','recordings','.venv','.envs','envs','.mamba','credentials',
                '.ssh','.codex'}
MAX_TEXT_BYTES=2*1024**2

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def allowed(relative,path):
    parts=relative.parts
    return (not path.is_symlink() and path.is_file() and
            not any(p in EXCLUDED_PARTS for p in parts) and
            (path.suffix.lower() in TEXT_EXTENSIONS or path.name in ROOT_FILES or path.name=='CMakeLists.txt') and
            path.name not in ('.env','known_hosts','authorized_keys') and
            path.stat().st_size<=MAX_TEXT_BYTES)

def export(source,destination,owner_snapshot=None):
    source=source.resolve();destination=destination.resolve()
    if destination.exists():raise ValueError('New destination required; never overwrite a repository or user files')
    source_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip()
    tracked=subprocess.check_output(['git','ls-files','-z'],cwd=source).decode().split('\0')
    paths={Path(x) for x in tracked if x}
    for directory in ('research','operations'):
        paths.update(p.relative_to(source) for p in (source/directory).rglob('*') if p.is_file())
    destination.mkdir(parents=True)
    files={};excluded=[]
    for relative in sorted(paths):
        p=source/relative
        if relative.as_posix() in ('README.md','AGENTS.md'):continue
        if not allowed(relative,p):excluded.append(str(relative));continue
        target=destination/relative;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(p,target);files[str(relative)]={'sha256':sha(p),'bytes':p.stat().st_size,'origin':'WORKTREE_CODE_SNAPSHOT'}
    for name in ('README.md','AGENTS.md'):
        target=destination/'provenance'/('UPSTREAM_'+name);target.parent.mkdir(exist_ok=True)
        shutil.copy2(source/name,target)
        files[str(target.relative_to(destination))]={'sha256':sha(target),'bytes':target.stat().st_size,'origin':'UPSTREAM_WORKTREE_DOCUMENT'}
    if owner_snapshot:
        owner_snapshot=owner_snapshot.resolve()
        for p in sorted(owner_snapshot.rglob('*')):
            relative=p.relative_to(owner_snapshot)
            if not allowed(relative,p):continue
            target=destination/'owner_snapshot/native-prefix-20261114'/relative
            target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
            files[str(target.relative_to(destination))]={'sha256':sha(target),'bytes':target.stat().st_size,'origin':'DATA_OWNED_CODE_COPY_NOT_MIGRATED_AUTHORITY'}
    manifest=dict(created_at=dt.datetime.now(dt.timezone.utc).isoformat(),source_head=source_head,
        source_branch=subprocess.check_output(['git','branch','--show-current'],cwd=source,text=True).strip(),
        source_worktree_dirty=True,snapshot_not_upstream_commit=True,source_index_or_branch_modified=False,
        runtime_freeze_or_execution_authority=False,weights_and_large_assets_included=False,
        experiment_raw_data_or_credentials_included=False,
        bytes=sum(v['bytes'] for v in files.values()),file_count=len(files),files=files,
        excluded_from_code_custody=excluded)
    (destination/'provenance/CODE_SNAPSHOT.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n')
    return manifest

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True)
    p.add_argument('--destination',type=Path,required=True);p.add_argument('--owner-code-snapshot',type=Path)
    a=p.parse_args();m=export(a.source,a.destination,a.owner_code_snapshot)
    print(json.dumps({k:m[k] for k in ('source_head','file_count','bytes')},indent=2))
if __name__=='__main__':main()
