"""Validate a read-only NAV-to-PUSH transition cohort export.

The normalized export is a data contract, not a controller or safety gate.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path


EVENTS = {"transition_started", "transition_ready", "transition_ready_refreshed",
          "transition_ready_revoked", "skill_started", "transition_failed"}
SOURCE_KEYS = {"nav_actor", "push_actor", "push_legs", "transition_control",
               "evaluator", "assets", "task"}
TERMINAL_PHASES = {"nav", "transition", "push"}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def finite_number(value: object, name: str, minimum: float | None = None) -> float:
    require(type(value) in (int, float) and math.isfinite(value), f"{name} must be finite")
    number = float(value)
    require(minimum is None or number >= minimum, f"{name} below {minimum}")
    return number


def vector(value: object, size: int | None, name: str) -> list[float]:
    require(isinstance(value, list) and (size is None or len(value) == size)
            and len(value) > 0, f"{name} has wrong shape")
    return [finite_number(item, f"{name}[{index}]") for index, item in enumerate(value)]


def validate_ready_state(state: object, event_time: float, budget: float,
                         joint_count: int, name: str) -> bool:
    require(isinstance(state, dict), f"{name} missing state")
    for field in ("base_pos_m", "base_lin_vel_m_s", "base_ang_vel_rad_s",
                  "hand_box_rel_pos_m"):
        vector(state.get(field), 3, f"{name}.{field}")
    vector(state.get("foot_normal_force_n"), 4, f"{name}.foot_normal_force_n")
    joints = vector(state.get("joint_pos_rad"), joint_count, f"{name}.joint_pos_rad")
    vector(state.get("joint_vel_rad_s"), len(joints), f"{name}.joint_vel_rad_s")
    vector(state.get("joint_effort_ratio"), len(joints), f"{name}.joint_effort_ratio")
    sample_time = finite_number(state.get("sample_time_s"), f"{name}.sample_time_s", 0)
    remaining = finite_number(state.get("remaining_s"), f"{name}.remaining_s", 0)
    finite_number(state.get("min_clearance_m"), f"{name}.min_clearance_m")
    require(abs(sample_time - event_time) <= 1e-6, f"{name} uses a different sample time")
    require(abs(remaining - (budget - event_time)) <= 1e-6,
            f"{name} has a reset or inconsistent task clock")
    require(type(state.get("observation_history_valid")) is bool,
            f"{name} missing observation history validity")
    return state["observation_history_valid"]


def audit(cohort: dict) -> dict:
    require(isinstance(cohort, dict) and type(cohort.get("schema_version")) is int
            and cohort["schema_version"] == 1,
            "Expected normalized transition contract schema_version 1")
    budget = finite_number(cohort.get("episode_budget_s"), "episode_budget_s", 0)
    require(budget > 0, "episode_budget_s must be positive")
    requested = cohort.get("requested_episodes")
    require(type(requested) is int and requested > 0, "Invalid requested_episodes")
    sources = cohort.get("source_hashes")
    require(isinstance(sources, dict) and SOURCE_KEYS <= sources.keys(),
            "Missing source hashes")
    for key in SOURCE_KEYS:
        value = sources[key]
        require(isinstance(value, str) and len(value) == 64
                and all(character in "0123456789abcdef" for character in value),
                f"Invalid source hash: {key}")
    conventions = cohort.get("state_conventions")
    require(isinstance(conventions, dict), "Missing state conventions")
    joint_names = conventions.get("joint_names")
    foot_order = conventions.get("foot_order")
    require(isinstance(joint_names, list) and len(joint_names) == 18
            and all(isinstance(name, str) and name for name in joint_names)
            and len(set(joint_names)) == 18, "Missing or ambiguous 18-joint order")
    require(isinstance(foot_order, list) and len(foot_order) == 4
            and all(isinstance(name, str) for name in foot_order)
            and set(foot_order) == {"FL", "FR", "RL", "RR"},
            "Missing or ambiguous foot force order")
    for field in ("base_position_frame", "base_velocity_frame", "hand_box_relative_frame",
                  "clearance_definition"):
        require(isinstance(conventions.get(field), str) and conventions[field],
                f"Missing state convention: {field}")
    launch_keys = cohort.get("requested_episode_keys")
    require(isinstance(launch_keys, list) and len(launch_keys) == requested,
            "Missing NAV-start launch manifest")
    expected = set()
    for item in launch_keys:
        require(isinstance(item, dict) and type(item.get("env_id")) is int
                and item["env_id"] >= 0 and type(item.get("episode")) is int
                and item["episode"] > 0, "Invalid NAV-start launch key")
        key = (item["env_id"], item["episode"])
        require(key not in expected, f"Duplicate NAV-start launch key {key}")
        expected.add(key)
    episodes = cohort.get("episodes")
    require(isinstance(episodes, list) and len(episodes) == requested,
            "Missing or duplicate episode in full NAV-start denominator")

    seen = set()
    phases = Counter()
    reasons = Counter()
    ready_count = 0
    valid_history_count = 0
    revoked_count = 0
    refreshed_count = 0
    for row in episodes:
        require(isinstance(row, dict), "Episode must be an object")
        env_id, episode = row.get("env_id"), row.get("episode")
        require(type(env_id) is int and env_id >= 0 and type(episode) is int and episode > 0,
                "Invalid environment or episode ID")
        key = (env_id, episode)
        require(key not in seen, f"Duplicate episode {key}")
        seen.add(key)
        phase = row.get("terminal_phase")
        reason = row.get("terminal_reason")
        require(isinstance(phase, str) and phase in TERMINAL_PHASES
                and isinstance(reason, str) and reason,
                f"Missing terminal phase or reason for {key}")
        require(reason != "box_settled" or phase == "push",
                f"{key} settled outside PUSH phase")
        terminal_time = finite_number(row.get("terminal_time_s"), f"{key}.terminal_time_s", 0)
        require(terminal_time <= budget + 1e-6, f"{key} exceeds task budget")
        events = row.get("events")
        require(isinstance(events, list), f"{key} missing event list")
        names = []
        previous_time = -1.0
        history_valid = False
        ready_open = False
        reached_ready = False
        for event in events:
            require(isinstance(event, dict) and isinstance(event.get("name"), str)
                    and event["name"] in EVENTS,
                    f"{key} has unknown event")
            name = event["name"]
            if name in {"transition_started", "skill_started", "transition_failed"}:
                require(name not in names, f"{key} repeats {name}")
            event_time = finite_number(event.get("time_s"), f"{key}.{name}.time_s", 0)
            require(previous_time <= event_time <= terminal_time,
                    f"{key} has out-of-order event time")
            previous_time = event_time
            names.append(name)
            if name == "transition_ready":
                require(not ready_open, f"{key} repeated READY without revocation")
                ready_open = reached_ready = True
            elif name == "transition_ready_refreshed":
                require(ready_open, f"{key} refreshed without READY")
                refreshed_count += 1
            elif name == "transition_ready_revoked":
                require(ready_open, f"{key} revoked without READY")
                ready_open = False
                revoked_count += 1
            elif name == "skill_started":
                require(ready_open, f"{key} started PUSH without current READY")
            if name in {"transition_ready", "transition_ready_refreshed"}:
                history_valid = validate_ready_state(event.get("state"), event_time, budget,
                                                     len(joint_names),
                                                     f"{key}.{name}")
        if phase == "nav":
            require(not names, f"{key} has transition events after NAV failure")
        else:
            require(names and names[0] == "transition_started",
                    f"{key} missing transition_started")
        if reached_ready:
            ready_count += 1
            valid_history_count += int(history_valid)
        if phase == "transition":
            require(names[-1] == "transition_failed" and "skill_started" not in names,
                    f"{key} needs transition_failed without skill_started")
        if phase == "push":
            require(reached_ready and names[-1] == "skill_started"
                    and "transition_failed" not in names,
                    f"{key} needs ready before skill_started")
        phases[phase] += 1
        reasons[reason] += 1
    require(seen == expected, "Episode identities differ from NAV-start launch manifest")

    return {
        "schema_version": 1,
        "scope": "Read-only transition data contract; no reachability calibration or online authorization",
        "requested_episodes": requested,
        "terminal_phase_counts": dict(sorted(phases.items())),
        "terminal_reason_counts": dict(sorted(reasons.items())),
        "transition_ready_count": ready_count,
        "ready_revocation_events": revoked_count,
        "ready_refresh_events": refreshed_count,
        "ready_with_valid_observation_history": valid_history_count,
        "ready_without_valid_observation_history": ready_count - valid_history_count,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cohort-json", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    if args.output_json.exists():
        parser.error("Output file exists")
    try:
        payload = json.loads(args.cohort_json.read_text(encoding="utf-8"))
        result = audit(payload)
    except ValueError as error:
        parser.error(str(error))
    result["cohort_sha256"] = hashlib.sha256(args.cohort_json.read_bytes()).hexdigest()
    result["analysis_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
