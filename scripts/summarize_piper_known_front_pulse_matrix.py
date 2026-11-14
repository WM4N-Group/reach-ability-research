"""Compare frozen signed front-foot pulses in three inspected Isaac states."""

import argparse
import hashlib
import json
import math
from pathlib import Path


SEEDS = (5703, 5712, 5802)
MODES = ("front-up", "front-down")
OFFSETS = (10, 20)
BASELINE_SHA256 = {
    5703: "27d36b18b012b76814e9a8715c6c6418a0f943317dba1fa1c80539b4ac2249a6",
    5712: "5fa840c27d9b08cb7d5952657a82d1cd27b78f06290b7229b7940d0ea9d6877a",
    5802: "4746bfcbbba37cfe89154447a51357c09678b4bbd58addaecf6e193739881392",
}
OLD_MANIFEST_SHA256 = "a563eec3888c484d5d6a045bc2c417e72b0d7ff5e9723a27ad934bb72d48c10d"
NEW_MANIFEST_SHA256 = "972be98354ccddbe68badac6e1f1d446c10ece56f210a22a3c8e5a4d3928bbc0"
BASELINE_ONLY = {"recovery_decision_state"}
PULSE_ONLY = {"support_probe_applied", "support_probe_leg_actions", "support_probe_dynamics"}


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_verified(path, expected):
    if sha256(path) != expected:
        raise ValueError(f"Frozen input differs: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def terminal_reason(report):
    active = [name for name, value in report["terminal"]["reasons"].items() if value]
    if len(active) != 1:
        raise ValueError("Expected exactly one original terminal reason")
    return active[0]


def pulse_row(seed, mode, baseline, candidate, audit, expected_candidate_sha, expected_audit_sha):
    if (candidate["seed"] != seed or candidate["schema_version"] != 20
            or candidate["support_response_probe"] != mode
            or candidate["record_support_response_velocity"] is not True
            or candidate["initial_state"] != baseline["initial_state"]
            or candidate["handoff"] != baseline["handoff"]
            or candidate["nav_actor_sha256"] != baseline["nav_actor_sha256"]
            or candidate["push_checkpoint_sha256"] != baseline["push_checkpoint_sha256"]
            or candidate["control_sha256"] != baseline["control_sha256"]
            or candidate["step_dt"] != baseline["step_dt"]
            or candidate["push_budget_s"] != baseline["push_budget_s"]
            or baseline["schema_version"] != 18
            or len(baseline["support_trace"]) != baseline["push_executed_steps"]
            or len(candidate["support_trace"]) != candidate["push_executed_steps"]):
        raise ValueError(f"Seed{seed} {mode} control or source differs")
    original = baseline["support_trace"]
    tested = candidate["support_trace"]
    first_action = next((index for index, item in enumerate(tested)
                         if item["support_probe_applied"]), None)
    if first_action is None:
        raise ValueError(f"Seed{seed} {mode} did not actuate")
    for index in range(first_action):
        reference = {key: value for key, value in original[index].items()
                     if key not in BASELINE_ONLY}
        observed = {key: value for key, value in tested[index].items()
                    if key not in PULSE_ONLY}
        if reference != observed:
            raise ValueError(f"Seed{seed} {mode} pre-action step {index} differs")
        direct = tested[index]["support_probe_dynamics"]
        expected = original[index]["recovery_decision_state"]
        if any(direct[key] != expected[key] for key in ("base_vel_w", "base_omega_w")):
            raise ValueError(f"Seed{seed} {mode} pre-action velocity differs at {index}")
    active = [index for index, item in enumerate(tested) if item["support_probe_applied"]]
    if (active != list(range(first_action, first_action + 20))
            or candidate["support_probe_steps"] != 20
            or not 0.0 < candidate["support_probe_max_target_delta_rad"] <= 0.0400001
            or abs(candidate["support_probe_trigger_s"]
                   - original[first_action - 1]["push_elapsed_s"]) > 1e-8
            or abs(tested[first_action]["push_elapsed_s"]
                   - candidate["support_probe_trigger_s"] - 0.02) > 1e-8):
        raise ValueError(f"Seed{seed} {mode} warning or pulse schedule differs")
    if seed == 5802:
        if (audit["candidate_sha256"] != expected_candidate_sha
                or audit["audit_sha256"] != "ca5fcc2d9248b7fe03d61a64148fe3ab0dc8863f403788623d384cc0d6696960"
                or audit["pre_action_equal_steps"] != first_action):
            raise ValueError("Seed5802 prior paired audit differs")
    elif (audit["candidate_sha256"] != expected_candidate_sha
          or audit["audit_sha256"] != "ab642e1a0b129857c76998116c90533044fdeb3aafcf3e99d7e2ddaea5cc8bee"
          or not audit["whole_previous_rollout_equal_after_stripping_velocity"]
          or audit["pre_action_velocity_equal_steps"] != first_action):
        raise ValueError(f"Seed{seed} {mode} prior paired audit differs")
    samples = []
    for offset in OFFSETS:
        index = first_action + offset
        if index >= min(len(original), len(tested)):
            raise ValueError(f"Seed{seed} {mode} lacks fixed response sample {offset}")
        observed = tested[index]["support_probe_dynamics"]
        reference = original[index]["recovery_decision_state"]
        values = {
            "since_first_action_sample_s": offset * candidate["step_dt"],
            "base_vertical_velocity_delta_m_s": observed["base_vel_w"][2] - reference["base_vel_w"][2],
            "base_y_angular_velocity_delta_rad_s": (observed["base_omega_w"][1]
                                                    - reference["base_omega_w"][1]),
        }
        if not all(math.isfinite(value) for value in values.values()):
            raise ValueError(f"Seed{seed} {mode} nonfinite response")
        prior = next((item for item in (audit["response"] if seed == 5802 else audit["samples"])
                      if (item.get("since_first_action_s", item.get("elapsed_since_first_action_s"))
                          == values["since_first_action_sample_s"])), None)
        if prior is None:
            raise ValueError(f"Seed{seed} {mode} prior response sample missing")
        prior_vz = prior.get("base_vertical_velocity_delta_m_s", prior.get("base_vz_delta_m_s"))
        prior_omega = prior.get("base_y_angular_velocity_delta_rad_s",
                                prior.get("base_omega_y_delta_rad_s"))
        if (abs(values["base_vertical_velocity_delta_m_s"] - prior_vz) > 1e-12
                or abs(values["base_y_angular_velocity_delta_rad_s"] - prior_omega) > 1e-12):
            raise ValueError(f"Seed{seed} {mode} response differs from prior audit")
        samples.append(values)
    return {
        "seed": seed,
        "mode": mode,
        "candidate_sha256": expected_candidate_sha,
        "prior_audit_sha256": expected_audit_sha,
        "warning_push_s": candidate["support_probe_trigger_s"],
        "first_action_push_s": tested[first_action]["push_elapsed_s"],
        "pre_action_equal_steps": first_action,
        "maximum_target_delta_rad": candidate["support_probe_max_target_delta_rad"],
        "baseline_terminal_reason": terminal_reason(baseline),
        "baseline_terminal_push_s": baseline["push_elapsed_s"],
        "candidate_terminal_reason": terminal_reason(candidate),
        "candidate_terminal_push_s": candidate["push_elapsed_s"],
        "samples": samples,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--old-manifest", type=Path, required=True)
    parser.add_argument("--new-manifest", type=Path, required=True)
    parser.add_argument("--old-baseline-dir", type=Path, required=True)
    parser.add_argument("--new-baseline", type=Path, required=True)
    parser.add_argument("--old-candidate-dir", type=Path, required=True)
    parser.add_argument("--new-candidate-dir", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    if args.output_json.exists():
        parser.error("Output file exists")
    protocol = json.loads(args.protocol.read_text(encoding="utf-8"))
    if (protocol["analysis_sha256"] != sha256(Path(__file__))
            or protocol["old_manifest_sha256"] != OLD_MANIFEST_SHA256
            or protocol["new_manifest_sha256"] != NEW_MANIFEST_SHA256
            or protocol["seeds_in_order"] != list(SEEDS)
            or protocol["modes_in_order"] != list(MODES)
            or protocol["response_offsets_steps"] != list(OFFSETS)):
        raise ValueError("Frozen cross-state protocol differs")
    old = read_verified(args.old_manifest, OLD_MANIFEST_SHA256)
    new = read_verified(args.new_manifest, NEW_MANIFEST_SHA256)
    rows = []
    control_sha = None
    for seed in SEEDS:
        baseline_path = (args.new_baseline if seed == 5802 else
                         args.old_baseline_dir / f"seed{seed}-decision-state.json")
        baseline = read_verified(baseline_path, BASELINE_SHA256[seed])
        if control_sha is None:
            control_sha = baseline["control_sha256"]
        elif control_sha != baseline["control_sha256"]:
            raise ValueError("Baseline control sources differ across states")
        for mode in MODES:
            manifest = new if seed == 5802 else old
            record = next((item for item in manifest["runs"]
                           if item.get("seed", 5802) == seed and item["mode"] == mode), None)
            if record is None:
                raise ValueError(f"Missing frozen candidate: {seed} {mode}")
            directory = args.new_candidate_dir if seed == 5802 else args.old_candidate_dir
            candidate = read_verified(directory / f"seed{seed}-{mode}.json", record["candidate_sha256"])
            audit = read_verified(directory / f"seed{seed}-{mode}-audit.json", record["audit_sha256"])
            rows.append(pulse_row(seed, mode, baseline, candidate, audit,
                                  record["candidate_sha256"], record["audit_sha256"]))
    output = {
        "schema_version": 1,
        "scope": "Three inspected states, two frozen signed pulses; mechanism and falsification only",
        "analysis_sha256": sha256(Path(__file__)),
        "protocol_sha256": sha256(args.protocol),
        "old_manifest_sha256": OLD_MANIFEST_SHA256,
        "new_manifest_sha256": NEW_MANIFEST_SHA256,
        "control_sha256": control_sha,
        "rows": rows,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("x", encoding="utf-8") as stream:
        json.dump(output, stream, indent=2, allow_nan=False)
    print(json.dumps({"rows": len(rows), "terminal_reasons": {
        f"{row['seed']}-{row['mode']}": row["candidate_terminal_reason"] for row in rows
    }}, indent=2))


if __name__ == "__main__":
    main()
