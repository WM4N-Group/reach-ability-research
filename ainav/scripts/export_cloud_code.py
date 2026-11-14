#!/usr/bin/env python3
"""Export an explicit code-only allowlist, without committing inherited dirty files."""
from pathlib import Path
import argparse, hashlib, json, re, shutil, subprocess
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--destination',type=Path,required=True);args=p.parse_args()
root=Path(__file__).resolve().parents[1];dest=args.destination.resolve()
if dest==root or dest.is_relative_to(root):raise SystemExit('Use an independent export checkout, never the inherited development tree')
base=Path('consumer-deliveries/AINAV-CLIMB-PREPARATION-CANDIDATES-20261113-v1')
release=json.loads((root/base/'CANDIDATE_RELEASE_v1.json').read_bytes())
files={base/'CANDIDATE_RELEASE_v1.json',*[base/rel for rel in release['files_sha256']]}
for rel,h in release['files_sha256'].items():
    if hashlib.sha256((root/base/rel).read_bytes()).hexdigest()!=h:raise SystemExit('Published source drift: '+rel)
for folder in [Path('development/climb_preparation_v2'),Path('development/registered_layout_conditions_v1'),Path('consumer-deliveries/AINAV-NATIVE-PREFIX-CONDITION-PILOT-20261114-v1'),Path('consumer-deliveries/AINAV-G2-REGISTERED-PREFIX-SOURCE-GATE-20261115-v1')]:
    files.update(f.relative_to(root) for f in (root/folder).rglob('*') if f.is_file() and f.suffix in ('.py','.json','.md') and '__pycache__' not in f.parts)
files.update(map(Path,['scripts/export_cloud_code.py','scripts/remote_code_smoke.py','scripts/measure_g1_public_boundary.py','scripts/compare_g1_public_values.py','docs/REMOTE_EXECUTION_AND_CODE_STORAGE_20261114.md']))
patterns=[re.compile(rb'-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----'),re.compile(rb'\b(?:ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}|sk-(?:proj-)?[A-Za-z0-9_-]{32,})\b'),re.compile(rb'https?://[^/\s:@]+:[^/\s@]+@')]
content={};total=0
for rel in sorted(files):
    src=root/rel
    if rel.is_absolute() or '..' in rel.parts or src.is_symlink() or not src.resolve().is_relative_to(root):raise SystemExit('Unsafe export path')
    data=src.read_bytes();total+=len(data)
    if len(data)>2*1024*1024 or any(pattern.search(data) for pattern in patterns):raise SystemExit('Export size/credential screening requires review: '+str(rel))
    content[rel]=data
if total>16*1024*1024:raise SystemExit('Code-only export unexpectedly exceeds16MiB')
for rel,data in content.items():
    target=dest/'ainav'/rel
    if target.is_symlink() or not target.resolve().is_relative_to(dest/'ainav'):raise SystemExit('Unsafe destination path')
    target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
head=subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip()
manifest={'role':'CURATED_AINAV_SOURCE_EXPORT_NOT_BULK_COMMIT_OF_INHERITED_DIRTY_TREE','development_HEAD_lineage':head,
 'selection':'Exact frozen299-member published source plus release; current owned development modules; fixed two-condition prefix package; export/deployment tools and docs',
 'excluded':'Inherited outputs/manifests, raw RGBD/NPZ, checkpoints, environments/SDK binaries, credentials and pycache; original working tree unchanged',
 'file_count':len(content),'content_bytes':total,'files_sha256':{str(rel):hashlib.sha256(data).hexdigest() for rel,data in content.items()}}
(dest/'ainav/SOURCE_EXPORT.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
(dest/'ainav/.gitignore').write_text('__pycache__/\n*.py[cod]\n.env\n.env.*\noutputs/\ndatasets/\ncheckpoints/\nlogs/\n*.pt\n*.pth\n*.ckpt\n*.npz\n*.npy\n*.mjb\n*.mjb.gz\n*.mp4\n')
checksum_files=[dest/'ainav'/rel for rel in sorted(content)]+[dest/'ainav/SOURCE_EXPORT.json',dest/'ainav/.gitignore']
if (dest/'ainav/README.md').is_file():checksum_files.append(dest/'ainav/README.md')
(dest/'CODE_SHA256SUMS').write_text(''.join(hashlib.sha256(path.read_bytes()).hexdigest()+'  '+str(path.relative_to(dest))+'\n' for path in sorted(checksum_files)))
print(json.dumps({'files_exported':len(content),'content_bytes':total,'credential_patterns_found':0,'original_tree_staged_or_committed':False},sort_keys=True))
