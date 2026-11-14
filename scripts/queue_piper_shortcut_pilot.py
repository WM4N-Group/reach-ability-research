"""Run one prepared Isaac shortcut pilot after its assigned GPU becomes idle."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time


def write_state(directory: Path, state: dict) -> None:
    temporary = directory / f"queue-state.{os.getpid()}.tmp"
    temporary.write_text(json.dumps(state, indent=2) + "\n")
    os.replace(temporary, directory / "queue-state.json")


def busy_pids(gpu: int) -> list[str] | None:
    result = subprocess.run(
        ["nvidia-smi", "-i", str(gpu), "--query-compute-apps=pid",
         "--format=csv,noheader,nounits"],
        capture_output=True, text=True, check=False,
    )
    if result.returncode:
        return None
    return sorted({line.strip() for line in result.stdout.splitlines() if line.strip()})


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runner", type=Path, required=True)
    parser.add_argument("--baseline-plan", type=Path, required=True)
    parser.add_argument("--screen", type=Path, required=True)
    parser.add_argument("--prepared", type=Path, required=True)
    parser.add_argument("--edge-start-index", type=int, required=True)
    parser.add_argument("--edge-end-index", type=int, required=True)
    parser.add_argument("--gpu", type=int, choices=(0, 1), required=True)
    parser.add_argument("--poll-s", type=int, default=30)
    parser.add_argument("--max-wait-s", type=int, default=43200)
    args = parser.parse_args()
    if args.poll_s < 5 or args.max_wait_s < args.poll_s:
        parser.error("Invalid wait interval")
    if not (args.runner.is_file() and args.baseline_plan.is_file()
            and args.screen.is_file() and (args.prepared / "plan.json").is_file()):
        parser.error("The frozen runner, sources, and prepared pilot must exist")
    if any((args.prepared / name).exists() for name in
           ("report.json", "run.log", "exit-status.json", "queue-claim.json")):
        parser.error("Pilot or queue output already exists")

    claim = {"pid": os.getpid(), "start_unix": time.time(), "gpu": args.gpu}
    with (args.prepared / "queue-claim.json").open("x") as handle:
        json.dump(claim, handle, indent=2)
    started = time.monotonic()
    idle_polls = 0
    try:
        while time.monotonic() - started < args.max_wait_s:
            busy = busy_pids(args.gpu)
            idle_polls = idle_polls + 1 if busy == [] else 0
            write_state(args.prepared, {
                "status": "queued", "gpu": args.gpu, "busy_pids": busy,
                "idle_polls": idle_polls, "time_unix": time.time(),
            })
            if idle_polls >= 2:
                command = [sys.executable, str(args.runner),
                           "--baseline-plan", str(args.baseline_plan),
                           "--screen", str(args.screen),
                           "--output", str(args.prepared),
                           "--edge-start-index", str(args.edge_start_index),
                           "--edge-end-index", str(args.edge_end_index),
                           "--physical-gpu", str(args.gpu), "--run-prepared"]
                write_state(args.prepared, {"status": "running", "gpu": args.gpu,
                                            "time_unix": time.time(), "command": command})
                with (args.prepared / "queue-run.log").open("x") as log:
                    result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT,
                                            check=False)
                write_state(args.prepared, {
                    "status": "finished" if result.returncode == 0 else "failed",
                    "gpu": args.gpu, "returncode": result.returncode,
                    "time_unix": time.time(),
                })
                raise SystemExit(result.returncode)
            time.sleep(args.poll_s)
        write_state(args.prepared, {"status": "queue_timeout", "gpu": args.gpu,
                                    "time_unix": time.time()})
        raise SystemExit(1)
    except Exception as exc:
        write_state(args.prepared, {"status": "queue_error", "gpu": args.gpu,
                                    "error": repr(exc), "time_unix": time.time()})
        raise


if __name__ == "__main__":
    main()
