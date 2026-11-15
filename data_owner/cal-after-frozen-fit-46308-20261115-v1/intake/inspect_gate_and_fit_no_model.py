from pathlib import Path
import json,hashlib
R=Path('/mnt/yuanyue/reach-runs/G3-TRAIN-only-20261115-v1');p=R/'TRAIN_SOURCE_FEATURE_LABEL_GATE.json';g=json.loads(p.read_bytes());f=json.loads((R/'TRAIN_FROZEN_FIT.json').read_bytes());f.pop('model');d=json.loads((R/'DERIVED_TRAINING_PROTOCOL.json').read_bytes());print(json.dumps(dict(gate=g,fit_summary=f,derived_qualification_scope=d.get('qualification_scope'),derived_training_gate=d.get('training_gate_source_reports'),derived_activation=d.get('training_activation')),ensure_ascii=False))
