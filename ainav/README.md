# AINav code export

This branch stores reproducible AINav source under `ainav/`. It is a curated source export, not a bulk commit of the inherited dirty development checkout.

- `consumer-deliveries/AINAV-CLIMB-PREPARATION-CANDIDATES-20261113-v1/`: exact published 299-member full-host source package and its release manifest. Full `ExecutionJudgedFullCourse` / original283 lineage; not a WM-v9 profile switch.
- `development/climb_preparation_v2/`: current owned public-observation, component, geometry and candidate development modules; not hot-installed into closed runs.
- `consumer-deliveries/AINAV-NATIVE-PREFIX-CONDITION-PILOT-20261114-v1/`: fixed left/right native-prefix pilot and the default2/explicit3 planner source overlay. The source overlay is NOT silently applied to the older immutable source package.
- `docs/REMOTE_EXECUTION_AND_CODE_STORAGE_20261114.md`: current compute/storage direction and deployment limitations.
- `SOURCE_EXPORT.json`: exact code allowlist, file hashes, size and lineage.

## Compute location

Simulation/training compute is on the user-designated SSH host `180.97.68.228:46308`. Authentication is managed outside Git. Local and GitHub copies store code; datasets, checkpoints, raw RGBD, NPZ, videos and large outputs remain in remote execution storage. Do not copy virtual environments or credentials into this repository.

The current native-prefix physical pilot remains Data-owned: fresh device locks/lease, complete program freeze and that program's own zero are required on the designated host. Do not run historical launchers, restore closed roots, lower original guards, or reinterpret audit-only data as training data.

## Code-only deployment smoke

```bash
python3 -I -B ainav/scripts/remote_code_smoke.py --root ainav
```

This compiles code, verifies published source hashes and checks default2/explicit3 request construction. It does **not** construct a simulator/Actor/renderer, issue commands, train a model or prove native qualification.

## Updating this branch

From the active AINav development checkout, export only the allowlist:

```bash
python3 -I -B scripts/export_cloud_code.py --destination /absolute/path/to/independent/cloud-checkout
```

Review the branch diff, retain peer directories, run the code-only check and commit only the exported `ainav/` files. Preserve original dirty/untracked files in the development checkout. Use normal authenticated Git, never place passwords or access tokens in a remote URL.
