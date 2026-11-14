"""Pinned, stdout-only archive checks. No SDK, runner import, SSH or actuation.

Historical canonical_checkers are source snapshots, NOT importable modules here.
This thin adapter only reuses their already-reviewed JSON/AST comparison logic.
"""
import argparse
import ast
import contextlib
import copy
import hashlib
import io
import json
import sys
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent


def digest_bytes(value):
    return hashlib.sha256(value).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text())


def index():
    return read_json(HERE / "canonical_evidence_index.json")["entries"]


def contained(relative):
    path = (HERE / relative).resolve()
    if not path.is_relative_to(HERE) or not path.is_file():
        raise ValueError("Missing/escaping bundled file: " + relative)
    return path


def pinned_bytes(key, explicit_path):
    # No fallback to historical paths; caller must supply every external input.
    path = Path(explicit_path).expanduser().resolve(strict=True)
    value = path.read_bytes()
    if digest_bytes(value) != index()[key]["sha256"]:
        raise ValueError("Canonical digest mismatch: " + key)
    return value


def exact_json(left, right):
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(
            exact_json(left[key], right[key]) for key in left
        )
    if isinstance(left, list):
        return len(left) == len(right) and all(
            exact_json(a, b) for a, b in zip(left, right)
        )
    return left == right


def verify_archive():
    manifest = read_json(HERE / "archive_sha256.json")
    for relative, expected in manifest["files"].items():
        if digest_bytes(contained(relative).read_bytes()) != expected:
            raise ValueError("Archive digest mismatch: " + relative)
    bundled = 0
    for entry in index().values():
        if "archived_relative_path" not in entry:
            continue
        value = contained(entry["archived_relative_path"]).read_bytes()
        if not (
            digest_bytes(value) == entry["sha256"] == entry["archived_sha256"]
            and len(value) == entry["bytes"]
        ):
            raise ValueError("Canonical snapshot mismatch")
        bundled += 1
    return {
        "archive_files_verified": len(manifest["files"]),
        "canonical_byte_exact_copies": bundled,
        "external_inputs_opened": False,
        "SDK_physics_or_old_test_suites_executed": False,
    }


def compare_prefix(args):
    current = json.loads(pinned_bytes("formal_progress", args.progress))
    old = json.loads(pinned_bytes("v13_report", args.old_report))
    events_equal = len(current["events"]) == 95 and exact_json(
        current["events"], old["events"][:95]
    )
    row = old["trace"][3100]
    keys = [
        "phase", "base", "box_speed_mps", "base_speed_mps",
        "hand_box_contact", "platform_feet", "climb_diagnostics",
    ]
    checkpoint_equal = (
        current["step"] == 15500
        and current["time_s"] == row["t"] == 310.0
        and set(current) & set(row) == set(keys)
        and all(exact_json(current[key], row[key]) for key in keys)
    )
    if not (events_equal and checkpoint_equal):
        raise ValueError("Pinned recorded-prefix comparison failed")
    return {
        "events_0_to_94_type_sensitive_equal": True,
        "trace_index": 3100,
        "common_checkpoint_keys_equal": keys,
        "full_continuous_state_or_suffix_NAV_success_proved": False,
        "bounded_source_task": "FAILED_WALL_TIMEOUT_BASELINE_NOT_COMPLETED",
        "success_rate_denominator": 1,
        "successes": 0,
    }


def load_pgid_functions(key, explicit_path):
    # Exact trusted SHA first; never import the external producer module/package.
    tree = ast.parse(pinned_bytes(key, explicit_path).decode())
    names = {"validate_snapshot", "quiet", "best_effort", "wait_stopped"}
    nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef)
             and node.name in names]
    if {node.name for node in nodes} != names:
        raise ValueError("Required pinned pure functions missing")

    def need(condition, message):
        if not condition:
            raise ValueError(message)

    namespace = {
        "P": {"CUDA_VISIBLE_DEVICES": "GPU-8d80b743-a2bb-fc25-37e1-8710fa364809"},
        "SOURCE": "synthetic-offline-owner",
        "need": need,
        "snapshot": None,
        "time": SimpleNamespace(sleep=lambda _: None),
    }
    # These four SHA-pinned functions only consume snapshots/callbacks here.
    # No gates, subprocesses, module imports, physical paths or producer main.
    exec(compile(ast.Module(body=copy.deepcopy(nodes), type_ignores=[]),
                 "<pinned-pgid-offline-AST>", "exec"), namespace)
    return namespace


def pgid_snapshot(namespace, rows):
    return {
        "collector_pid": 9,
        "owner_marker": {"source_id": namespace["SOURCE"], "pid": 100, "pgid": 100},
        "ps": {"returncode": 0, "stderr": "", "stdout":
               "PID PGID STAT COMMAND\n1 1 Ss init\n" +
               "\n".join(rows) + ("\n" if rows else "")},
        "gpu": {"returncode": 0, "stderr": "", "stdout":
                "0, GPU-other, 1, 0\n1, " +
                namespace["P"]["CUDA_VISIBLE_DEVICES"] + ", 1, 0\n"},
        "apps": {"returncode": 0, "stderr": "", "stdout": ""},
    }


def compare_pgid(args):
    old = load_pgid_functions("r2_runner", args.r2_runner)
    new = load_pgid_functions("r3_runner", args.r3_runner)
    rows = [
        '101 100 S /usr/bin/python3 -c "offline fixture"',
        '100 700 S /usr/bin/python3 -c "offline fixture"',
    ]
    for row in rows:
        if not old["quiet"](pgid_snapshot(old, [row])):
            raise ValueError("Expected r2 counterexample not reproduced")
        if new["quiet"](pgid_snapshot(new, [row])):
            raise ValueError("r3 owned live PID/PGID was incorrectly ignored")
    collector = pgid_snapshot(new, ['9 9 S python3 -c "inventory text"'])
    zombie = pgid_snapshot(new, ['101 100 Z python3 -c "defunct"'])
    if not (new["quiet"](collector) and new["quiet"](zombie)):
        raise ValueError("Collector/zombie positive control failed")
    sequence = [pgid_snapshot(new, [row]) for row in rows] + [collector]
    calls = {"get": 0, "sleep": 0, "notify": 0}

    class BoundExceeded(BaseException):
        pass

    def get():
        calls["get"] += 1
        if calls["get"] > len(sequence):
            raise BoundExceeded("Offline snapshot sequence exhausted")
        return sequence[calls["get"] - 1]

    def sleep(_):
        calls["sleep"] += 1
        if calls["sleep"] > len(sequence):
            raise BoundExceeded("Offline wait bound exceeded")

    def notify():
        calls["notify"] += 1
        raise OSError(28, "synthetic notification ENOSPC")

    with contextlib.redirect_stdout(io.StringIO()):
        stopped = new["wait_stopped"](get, notify, sleep)
    if stopped is not collector or calls != {"get": 3, "sleep": 2, "notify": 1}:
        raise ValueError("PGID wait returned too early or outside fixture bound")
    return {
        "original_counterexamples": 2,
        "r2_false_quiescence_reproduced": True,
        "r3_owned_PID_PGID_rejected": True,
        "collector_and_zombie_controls": True,
        "bounded_wait_calls": calls,
        "SDK_SSH_or_processes_launched": False,
        "source_RUN_authorization": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_subparsers(dest="mode", required=True)
    modes.add_parser("verify-archive")
    prefix = modes.add_parser("compare-prefix")
    prefix.add_argument("--progress", required=True)
    prefix.add_argument("--old-report", required=True)
    pgid = modes.add_parser("compare-pgid")
    pgid.add_argument("--r2-runner", required=True)
    pgid.add_argument("--r3-runner", required=True)
    args = parser.parse_args()
    try:
        if args.mode == "verify-archive":
            result = verify_archive()
        elif args.mode == "compare-prefix":
            result = compare_prefix(args)
        else:
            result = compare_pgid(args)
    except Exception as error:
        print(type(error).__name__ + ": " + str(error), file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
