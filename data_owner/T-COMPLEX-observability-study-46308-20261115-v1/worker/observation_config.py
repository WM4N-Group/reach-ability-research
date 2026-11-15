from pathlib import Path
import json,os
R=Path('/mnt/yuanyue/data-team/deployments/46308-20261114');B=R/'workspace';N='T-COMPLEX-observability-study-46308-20261115-v1';W=B/'workers'/N;M=B/'manifests'/N;SDK_ROOT=Path('/mnt/yuanyue/ainav-execution-reference-20261112-v1/sdk-bundle');ENVIRONMENT=Path('/mnt/yuanyue/data-team/env-native-v1');SOURCE=B/'workers/new-critic-cohort-46308-20261115-v1/inputs/AINav/common-source';OWN=W/'inputs/scene';REACH=W/'inputs/Reach';PROTOCOL=json.loads((W/'protocol.json').read_bytes());IDS=('OBS',);SCOPES={a:PROTOCOL['arms'][a]['scope_id']for a in IDS};ARM=os.environ.get('DATA_OBSERVATION_ARM');
if ARM not in IDS:raise ValueError('Explicit OBS only, no comparison scope default')
