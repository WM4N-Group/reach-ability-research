"""Explicit external evidence roots; historical JSON path strings are never executed."""
from dataclasses import dataclass
from pathlib import Path

MODULE_DIR = Path(__file__).resolve().parent
REPO_ROOT = MODULE_DIR.parents[1]


@dataclass(frozen=True)
class EvidenceRoots:
    control: Path
    run: Path
    terminal_review: Path
    verification: Path

    @classmethod
    def from_args(cls, args):
        roots = cls(*(Path(getattr(args, name)).expanduser().resolve() for name in (
            'control_root', 'run_root', 'terminal_review_root', 'verification_root')))
        for name in ('control', 'run', 'terminal_review', 'verification'):
            if not getattr(roots, name).is_dir():
                raise FileNotFoundError(f'Missing external evidence root {name}: {getattr(roots, name)}')
        return roots

    def original_path(self, key):
        locations = {
            'control_manifest': (self.control, 'package-manifest.json'),
            'run_manifest': (self.run, 'run-files-manifest.json'),
            'events': (self.run, 'native-small/attempt/controllers/floor-aware-planning-events.jsonl'),
            'payloads': (self.run, 'native-small/attempt/controllers/planner-masks-complete.jsonl'),
            'prior_pair_index': (self.terminal_review, 'complete_mask_pair_index.json'),
            'native_frame': (self.terminal_review, 'last_native_control_line.jsonl'),
        }
        root, relative = locations[key]
        return contained_file(root, relative)

    def new_output(self, path, candidate=None):
        output = Path(path).expanduser().resolve()
        protected = [REPO_ROOT, self.control, self.run, self.terminal_review, self.verification]
        if candidate is not None:
            protected.append(Path(candidate).resolve())
        if any(output.is_relative_to(root) for root in protected):
            raise ValueError('Output must be outside repository and all original/candidate evidence roots')
        if output.exists():
            raise FileExistsError(f'Refusing to overwrite output: {output}')
        return output


def contained_file(root, relative):
    root = Path(root).resolve()
    path = (root / relative).resolve()
    if not path.is_relative_to(root):
        raise ValueError(f'Evidence path escapes supplied root: {relative}')
    if not path.is_file():
        raise FileNotFoundError(f'Missing external evidence: {path}')
    return path


def add_evidence_arguments(parser):
    for flag in ('control-root', 'run-root', 'terminal-review-root', 'verification-root'):
        parser.add_argument('--' + flag, type=Path, required=True)
