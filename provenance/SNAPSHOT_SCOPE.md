# Snapshot scope

The original worktree remains at its own path, branch and remote with all dirty/untracked work intact. This new repository deliberately starts a code-only history; it is not a rewritten or squashed upstream history.

CODE_SNAPSHOT.json records exact files at export time. Subsequently authored root README.md, AGENTS.md and operations/REMOTE_EXECUTION_CN.md explain this repository's current operational policy. The copied .gitignore additionally excludes credentials, environments and heavyweight execution artifacts. Thus the exported .gitignore hash in the manifest describes its upstream bytes, not the final authored .gitignore; Git commit/tree is the final snapshot identity.

Data-owned code is copied for custody under owner_snapshot; its machine-specific authority/locks/pins are NOT migrated or granted by this copy. No credentials, weights, raw evidence, videos, datasets or environments are intentionally part of the snapshot. Historical references to excluded data remain provenance, not proof that an old test is portable.
