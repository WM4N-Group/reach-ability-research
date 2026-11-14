"""Find exact-state command witnesses that refute a proposed robust interval."""

from __future__ import annotations

import argparse
from decimal import Decimal
import json
from pathlib import Path

from check_piper_startup import sha256


def assess_interval(
    state_sha256: str, nominal_x: Decimal, radius: Decimal, observations: list[dict]
) -> dict:
    if radius < 0:
        raise ValueError("radius must be non-negative")
    witnesses = []
    for item in observations:
        if item["state_sha256"] != state_sha256:
            continue
        if item["valid"] is not True:
            raise ValueError("Unvalidated observation cannot support a witness query")
        if abs(item["offset_x"] - nominal_x) <= radius and not item["accepted"]:
            witnesses.append({
                "offset_x_m": str(item["offset_x"]),
                "distance_from_nominal_m": str(abs(item["offset_x"] - nominal_x)),
                "reason": item["reason"],
                "source_sha256": item["source_sha256"],
            })
    return {
        "decision": "refuted_by_witness" if witnesses else "abstain_no_continuous_certificate",
        "witnesses": witnesses,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol-json", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    if args.output_json.exists():
        parser.error("Require a new output path")
    protocol = json.loads(args.protocol_json.read_text(), parse_float=Decimal)
    if sha256(Path(__file__)) != protocol["auditor_sha256"]:
        raise ValueError("Frozen auditor changed")
    summary_path = Path(protocol["transfer_summary_path"])
    transfer_protocol_path = Path(protocol["transfer_protocol_path"])
    if (sha256(summary_path) != protocol["transfer_summary_sha256"]
            or sha256(transfer_protocol_path) != protocol["transfer_protocol_sha256"]):
        raise ValueError("Frozen transfer evidence changed")
    summary = json.loads(summary_path.read_text(), parse_float=Decimal)
    transfer = json.loads(transfer_protocol_path.read_text(), parse_float=Decimal)
    if (summary["protocol_sha256"] != protocol["transfer_protocol_sha256"]
            or summary["evaluated_count"] != len(summary["rows"])
            or [item["name"] for item in transfer["grid"]]
            != [item["name"] for item in summary["rows"][0]["grid"]]):
        raise ValueError("Transfer summary and protocol disagree")
    anchor_x = transfer["anchor_offset_local_m"][0]
    observations = []
    for row in summary["rows"]:
        if (row["decision"] != "evaluated" or not row["eligible"]
                or not row["anchor_valid"] or not row["anchor_acceptance"]):
            raise ValueError("Only validated accepted anchors can be queried")
        state = row["context_sha256"]
        seed = row["seed"]
        if (sha256(summary_path.parent / f"seed{seed}-context-v1.json") != state
                or sha256(summary_path.parent / f"seed{seed}-anchor-suffix-v1.json")
                != row["anchor_suffix_sha256"]):
            raise ValueError("Frozen context or anchor artifact changed")
        observations.append({
            "state_sha256": state, "offset_x": anchor_x, "valid": True,
            "accepted": row["anchor_acceptance"], "reason": "completed",
            "source_sha256": row["anchor_suffix_sha256"],
        })
        for item, frozen in zip(row["grid"], transfer["grid"], strict=True):
            if (item["name"] != frozen["name"]
                    or item["offset_local_m"] != frozen["offset_local_m"]
                    or item["valid"] is not True
                    or sha256(summary_path.parent / f"seed{seed}-{item['name']}-suffix-v1.json")
                    != item["suffix_sha256"]):
                raise ValueError("Grid observation differs from frozen protocol")
            observations.append({
                "state_sha256": state, "offset_x": item["offset_local_m"][0],
                "valid": item["valid"], "accepted": item["ten_second_acceptance"],
                "reason": item["reason"], "source_sha256": item["suffix_sha256"],
            })
    if len({row["context_sha256"] for row in summary["rows"]}) != len(summary["rows"]):
        raise ValueError("Duplicate state hashes")
    queries = []
    for row in summary["rows"]:
        state = row["context_sha256"]
        for radius_text in protocol["hypothetical_radius_m"]:
            radius = Decimal(radius_text)
            result = assess_interval(state, anchor_x, radius, observations)
            queries.append({
                "seed": row["seed"], "layout": row["layout"],
                "state_sha256": state,
                "nominal_offset_x_m": str(anchor_x),
                "hypothetical_radius_m": radius_text,
                **result,
            })
    output = {
        "schema_version": 1,
        "scope": "Finite exact-state simulation counterexamples only; no positive certificate",
        "protocol_sha256": sha256(args.protocol_json),
        "auditor_sha256": sha256(Path(__file__)),
        "transfer_summary_sha256": protocol["transfer_summary_sha256"],
        "queries": queries,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("x") as destination:
        json.dump(output, destination, indent=2, allow_nan=False)
        destination.write("\n")
    counts = {radius: sum(item["decision"] == "refuted_by_witness"
                           and item["hypothetical_radius_m"] == radius for item in queries)
              for radius in protocol["hypothetical_radius_m"]}
    print(json.dumps({"output_sha256": sha256(args.output_json),
                      "refuted_counts_by_radius": counts,
                      "query_count": len(queries)}))


if __name__ == "__main__":
    main()
