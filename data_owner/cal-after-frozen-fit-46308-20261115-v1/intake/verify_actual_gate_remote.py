"""Read-only verify actual Reach release/gate/fit/dataset hashes; do not export rows/weights."""
from pathlib import Path
import json,hashlib,sys,datetime
R=Path('/mnt/yuanyue/reach-runs/G3-TRAIN-only-20261115-v1');sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
expected=json.load(sys.stdin);P=R/'TRAIN_GATE_AND_FIT_RELEASE.json';assert sha(P)==expected['release_sha256'];release=json.loads(P.read_bytes());print(json.dumps(dict(at=datetime.datetime.now().astimezone().isoformat(),release_sha256=sha(P),release=release,files=[dict(name=n,sha256=sha(R/n),keys=list(json.loads((R/n).read_bytes())))for n,pin in expected['files'].items()if (sha(R/n)==pin or (_ for _ in ()).throw(AssertionError('Reach file pin drift '+n)))],no_weights_or_rows_exported=True),ensure_ascii=False))
