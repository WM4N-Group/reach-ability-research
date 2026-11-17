"""Finite selected source/declaration checks, NOT full native import qualification.

Hashes bytes without importing AINav/Reach or touching a backend/world. Closed
sources are never rewritten. Whole-program dependency inventory remains required.
"""
from pathlib import Path
import ast
import hashlib
import json

REACH_PACKAGE = 'research.task_conditioned_reachability.execution_preparation'
REACH_PINS = {
    'finite_multistep_planner.py': '3a5eb184b9988371f0f05909bfa92e008b7eeb3b56eaef349b68416ef8a15bb9',
    'v4_common_nav_prelude.py': '3b6f37d653d3db0af882157bd3e7627faadd44d4aa246c927a82212d87a3343a',
    'v4_nav_reference_cost.py': '6f9dfdecfbd4eea1a0a96eeca9626560c058db1b40abf5b3c987c4972f67c266',
    'v4_reference_cost.py': '59b357d6c2dceb0a6bb51991c0c4b7b65aa37a99121a4fe7b63233b11c97bda9',
    'v4_backbone_adapters.py': '56dfd5767d8dd9abe0b191fdee6adb9d75bb7adb1e5c3feef9b5a18871051620',
    'v4_successor_choice.py': 'f8ce704afce74ddbfa984bcf46c97adf7797cedc978f3aa8ba8fa572022e1295',
}
DECLARATION_PINS = {
    'NAV_DEV_DECLARATION.json': 'cd8d8584ca4ea3497381c321354ef29f89a2b5c871fa0cdc51f737a14e7634cb',
    'INITIALIZATION_AND_RNG_ADDENDUM.json': 'fc04cc1dcd58e7f3692ef04d2a425c1ad603fd257f343b83f907096284723a47',
}


def checked_bytes(path, pin):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError('Missing/alias selected source: ' + path.name)
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != pin:
        raise ValueError('Selected source drift: ' + path.name)
    return raw


def verify_reach_sources(root):
    base = Path(root) / REACH_PACKAGE.replace('.', '/')
    pins = {}
    for name, pin in REACH_PINS.items():
        path = base / name
        raw = checked_bytes(path, pin)
        # Check eager relative module imports. Lazy A/B-only WM constructor imports
        # are outside this selected C/D domain, not a request to stage WM.
        for node in ast.parse(raw).body:
            if isinstance(node, ast.ImportFrom) and node.level:
                if node.level != 1 or node.module is None or node.module.split('.')[0] + '.py' not in REACH_PINS:
                    raise ValueError('Unselected relative Reach source dependency: ' + name)
        pins[str(path)] = pin
    return pins


def read_declarations(paths):
    if type(paths) is not dict or set(paths) != set(DECLARATION_PINS):
        raise ValueError('Explicit two selected prospective declarations')
    return {name: json.loads(checked_bytes(paths[name], pin))
            for name, pin in DECLARATION_PINS.items()}


def adopted_task(declarations):
    d = declarations['NAV_DEV_DECLARATION.json']
    r = declarations['INITIALIZATION_AND_RNG_ADDENDUM.json']
    return dict(independent_DEV_not_original_V4=True,
                public_domain=d['common_public_domain'],
                initialization=r['initialization'], fair_served_model=r['fair_served_model'],
                physical_asset=d['physical_asset'])


def provider_config(protocol):
    """Only immutable nominal declaration, never an initial-state/pose resolver."""
    declarations = read_declarations(protocol['declaration_sources'])
    task = adopted_task(declarations)
    if protocol['common']['supported_DEV_task_and_initialization'] != task:
        raise ValueError('Exact selected DEV task/initialization, not silent V4 edit')
    d = task['public_domain']
    return dict(required_visit_refs=tuple(d['required_visit_refs']), finish_ref=d['finish_ref'],
                public_map_source_ref='declared:NAV_DEV_DECLARATION:' + DECLARATION_PINS['NAV_DEV_DECLARATION.json'],
                declared_bounds_xyxy=tuple(d['declared_bounds_xyxy']),
                declared_obstacles_xyxy=tuple(tuple(x) for x in d['declared_obstacles_xyxy']),
                footprint_radius_m=d['footprint_radius_m'],
                nav_phase_policy=declarations['NAV_DEV_DECLARATION.json']['planning_prior']['phase_policy'])
