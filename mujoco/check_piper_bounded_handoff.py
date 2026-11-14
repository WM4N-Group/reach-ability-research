"""Regression checks for conditional belief-state handoff viability."""

from dataclasses import replace
import unittest

from reconfigurable_navigation.reachability.bounded_handoff import (
    SAFETY_TERMS,
    BeliefNode,
    BeliefTransition,
    JointBoundEvidence,
    MatchedActionWitness,
    classify_matched_action_witness,
    evaluate_bounded_handoff,
)


POLICY = "a" * 64
CONTROL = "b" * 64


def margins(**changes):
    result = {term: 1.0 for term in SAFETY_TERMS}
    result.update(changes)
    return result


def belief(node_id, step, safety, reached, transitions=(), *, history=None):
    return BeliefNode(node_id, step, safety, reached, transitions,
                      observation_history_id=history or node_id)


def edge(action_id, successor_ids, safety=None):
    return BeliefTransition(action_id, successor_ids, margins() if safety is None else safety)


def evidence(**changes):
    values = {
        "model_sha256": "c" * 64,
        "calibration_manifest_sha256": "d" * 64,
        "policy_sha256": POLICY,
        "control_sha256": CONTROL,
        "scene_case": "toy-scene",
        "scene_contract_sha256": "f" * 64,
        "entry_distribution_sha256": "e" * 64,
        "entry_observation_history_id": "root",
        "joint_coverage_lower_bound": 0.99,
        "coverage_confidence_level": 0.95,
        "coverage_unit": "full_rollout",
        "coverage_action_scope": "all_graph_actions_and_branches",
        "coverage_horizon_steps": 2,
        "coverage_step_dt_s": 0.02,
        "state_enclosure_validated": True,
        "transition_enclosure_validated": True,
        "command_realization_enclosure_validated": True,
        "observation_partition_validated": True,
        "max_control_delay_steps": 1,
        "modelled_delay_steps": 1,
        "validated_action_ids": frozenset({"hold", "left", "right", "a", "b"}),
    }
    values.update(changes)
    return JointBoundEvidence(**values)


def evaluate(nodes, proof, budget=0.04, horizon_steps=2):
    return evaluate_bounded_handoff(
        nodes, "root", horizon_steps=horizon_steps, step_dt_s=0.02,
        remaining_push_budget_s=budget,
        expected_policy_sha256=POLICY, expected_control_sha256=CONTROL,
        expected_model_sha256="c" * 64,
        expected_calibration_manifest_sha256="d" * 64,
        expected_scene_case="toy-scene",
        expected_scene_contract_sha256="f" * 64,
        expected_entry_distribution_sha256="e" * 64,
        required_joint_coverage=0.95,
        required_coverage_confidence=0.95,
        evidence=proof,
    )


class BoundedHandoffTests(unittest.TestCase):
    def test_full_push_budget_horizon_is_iterative_and_checks_last_step(self):
        nodes = {
            "root": belief("root", 0, margins(), False,
                           (edge("hold", ("step1",)),)),
        }
        for step in range(1, 601):
            node_id = f"step{step}"
            transitions = () if step == 600 else (
                edge("hold", (f"step{step + 1}",)),
            )
            nodes[node_id] = belief(node_id, step, margins(), step == 600, transitions)
        proof = evidence(coverage_horizon_steps=600)
        result = evaluate(nodes, proof, budget=12.0, horizon_steps=600)
        self.assertEqual(result.verdict, "model_conditional_inner_set")
        self.assertEqual(len(result.causal_policy), 600)
        nodes["step600"] = belief("step600", 600, margins(base_contact=-0.1), True)
        self.assertEqual(evaluate(nodes, proof, budget=12.0, horizon_steps=600).verdict,
                         "abstain")

    def test_one_causal_feedback_policy_wins_after_observation_branches(self):
        nodes = {
            "root": belief("root", 0, margins(), False,
                               (edge("hold", ("seen-left", "seen-right")),)),
            "seen-left": belief("seen-left", 1, margins(), False,
                                    (edge("left", ("goal-left",)),)),
            "seen-right": belief("seen-right", 1, margins(), False,
                                     (edge("right", ("goal-right",)),)),
            "goal-left": belief("goal-left", 2, margins(), True),
            "goal-right": belief("goal-right", 2, margins(), True),
        }
        result = evaluate(nodes, evidence())
        self.assertEqual(result.verdict, "model_conditional_inner_set")
        self.assertEqual(result.causal_policy,
                         {"root": "hold", "seen-left": "left", "seen-right": "right"})
        self.assertFalse(result.contact_authorized)

    def test_no_clairvoyant_action_for_indistinguishable_hidden_states(self):
        nodes = {
            "root": belief("root", 0, margins(), False, (
                edge("a", ("goal-a", "bad-b")),
                edge("b", ("bad-a", "goal-b")),
            )),
            "goal-a": belief("goal-a", 1, margins(), True),
            "goal-b": belief("goal-b", 1, margins(), True),
            "bad-a": belief("bad-a", 1, margins(base_contact=-0.1), False),
            "bad-b": belief("bad-b", 1, margins(base_contact=-0.1), False),
        }
        result = evaluate(nodes, evidence())
        self.assertEqual(result.verdict, "abstain")
        self.assertEqual(result.reason, "no_inner_policy_proved_by_supplied_bounds")

    def test_hidden_components_with_same_history_share_one_action(self):
        nodes = {
            "root": belief("root", 0, margins(), False, (
                edge("a", ("goal-a",)),
                edge("b", ("bad-a",)),
            ), history="same-observation"),
            "hidden-other": belief("hidden-other", 0, margins(), False, (
                edge("a", ("bad-b",)),
                edge("b", ("goal-b",)),
            ), history="same-observation"),
            "goal-a": belief("goal-a", 1, margins(), True),
            "goal-b": belief("goal-b", 1, margins(), True),
            "bad-a": belief("bad-a", 1, margins(base_contact=-0.1), False),
            "bad-b": belief("bad-b", 1, margins(base_contact=-0.1), False),
        }
        result = evaluate(nodes, evidence(entry_observation_history_id="same-observation"))
        self.assertEqual(result.verdict, "abstain")
        self.assertEqual(result.reason, "no_inner_policy_proved_by_supplied_bounds")

    def test_shared_history_collects_all_successors_before_observation_branches(self):
        nodes = {
            "root": belief("root", 0, margins(), False,
                           (edge("hold", ("seen-left",)),), history="same"),
            "hidden-other": belief("hidden-other", 0, margins(), False,
                                   (edge("hold", ("seen-right",)),), history="same"),
            "seen-left": belief("seen-left", 1, margins(), False,
                                (edge("left", ("goal-left",)),)),
            "seen-right": belief("seen-right", 1, margins(), False,
                                 (edge("right", ("goal-right",)),)),
            "goal-left": belief("goal-left", 2, margins(), True),
            "goal-right": belief("goal-right", 2, margins(), True),
        }
        result = evaluate(nodes, evidence(entry_observation_history_id="same"))
        self.assertEqual(result.verdict, "model_conditional_inner_set")
        self.assertEqual(result.causal_policy,
                         {"same": "hold", "seen-left": "left", "seen-right": "right"})

    def test_missing_coverage_delay_or_source_abstains(self):
        nodes = {"root": belief("root", 0, margins(), True)}
        self.assertEqual(evaluate(nodes, None).reason, "missing_joint_bound_evidence")
        self.assertEqual(evaluate(nodes, evidence(joint_coverage_lower_bound=0.90)).reason,
                         "insufficient_joint_coverage")
        self.assertEqual(evaluate(nodes, evidence(modelled_delay_steps=0)).reason,
                         "unbounded_or_unmodelled_control_delay")
        self.assertEqual(evaluate(nodes, evidence(policy_sha256="e" * 64)).reason,
                         "source_or_scene_outside_calibration")
        self.assertEqual(evaluate(nodes, evidence(model_sha256="e" * 64)).reason,
                         "source_or_scene_outside_calibration")
        self.assertEqual(evaluate(nodes, evidence(calibration_manifest_sha256="e" * 64)).reason,
                         "source_or_scene_outside_calibration")
        self.assertEqual(evaluate(nodes, evidence(scene_contract_sha256="a" * 64)).reason,
                         "source_or_scene_outside_calibration")
        self.assertEqual(evaluate(nodes, evidence(entry_distribution_sha256="f" * 64)).reason,
                         "entry_distribution_or_history_outside_calibration")
        self.assertEqual(evaluate(nodes, evidence(entry_observation_history_id="reset-push")).reason,
                         "entry_distribution_or_history_outside_calibration")
        self.assertEqual(evaluate(nodes, evidence(validated_action_ids=frozenset())).verdict,
                         "model_conditional_inner_set")
        self.assertEqual(evaluate(nodes, evidence(), budget=0.03).reason,
                         "horizon_exceeds_push_budget")

    def test_self_collision_needs_its_own_safety_margin(self):
        missing = margins()
        del missing["self_collision"]
        self.assertEqual(evaluate({"root": belief("root", 0, missing, True)},
                                  evidence()).verdict, "abstain")
        self.assertEqual(evaluate({"root": belief("root", 0,
                                                  margins(self_collision=-0.001), True)},
                                  evidence()).verdict, "abstain")
        self.assertEqual(evaluate({"root": belief("root", 0, margins(), True)},
                                  evidence()).verdict, "model_conditional_inner_set")

    def test_control_step_endpoints_cannot_hide_interval_contact(self):
        nodes = {
            "root": belief("root", 0, margins(), False,
                           (edge("hold", ("goal",),
                                 margins(invalid_hand_contact=-0.001)),)),
            "goal": belief("goal", 1, margins(), True),
        }
        proof = evidence(coverage_horizon_steps=1)
        self.assertEqual(evaluate(nodes, proof, horizon_steps=1).verdict, "abstain")
        nodes["root"] = belief("root", 0, margins(), False,
                               (edge("hold", ("goal",), {}),))
        self.assertEqual(evaluate(nodes, proof, horizon_steps=1).verdict, "abstain")
        nodes["root"] = belief("root", 0, margins(), False,
                               (edge("hold", ("goal",)),))
        self.assertEqual(evaluate(nodes, proof, horizon_steps=1).verdict,
                         "model_conditional_inner_set")

    def test_shared_observation_requires_interval_safety_for_every_hidden_state(self):
        nodes = {
            "root": belief("root", 0, margins(), False,
                           (edge("hold", ("goal-a",)),), history="same"),
            "hidden-other": belief("hidden-other", 0, margins(), False,
                                   (edge("hold", ("goal-b",),
                                         margins(self_collision=-0.001)),), history="same"),
            "goal-a": belief("goal-a", 1, margins(), True),
            "goal-b": belief("goal-b", 1, margins(), True),
        }
        proof = evidence(coverage_horizon_steps=1,
                         entry_observation_history_id="same")
        self.assertEqual(evaluate(nodes, proof, horizon_steps=1).verdict, "abstain")

    def test_stepwise_or_weakly_calibrated_coverage_cannot_certify_rollout(self):
        nodes = {"root": belief("root", 0, margins(), True)}
        self.assertEqual(evaluate(nodes, evidence(coverage_unit="control_step")).reason,
                         "coverage_not_full_rollout")
        self.assertEqual(evaluate(nodes, evidence(coverage_action_scope="observed_policy_only")).reason,
                         "coverage_not_action_uniform")
        self.assertEqual(evaluate(nodes, evidence(coverage_confidence_level=None)).reason,
                         "insufficient_coverage_confidence")
        self.assertEqual(evaluate(nodes, evidence(coverage_confidence_level=0.90)).reason,
                         "insufficient_coverage_confidence")
        self.assertEqual(evaluate(nodes, evidence(coverage_horizon_steps=1)).reason,
                         "coverage_horizon_mismatch")
        self.assertEqual(evaluate(nodes, evidence(coverage_step_dt_s=0.01)).reason,
                         "coverage_horizon_mismatch")

    def test_abstention_does_not_expose_an_inapplicable_coverage_bound(self):
        nodes = {"root": belief("root", 0, margins(), True)}
        for proof in (evidence(model_sha256="e" * 64),
                      evidence(scene_contract_sha256="a" * 64),
                      evidence(coverage_horizon_steps=1),
                      evidence(joint_coverage_lower_bound=0.90)):
            result = evaluate(nodes, proof)
            self.assertEqual(result.verdict, "abstain")
            self.assertIsNone(result.joint_coverage_lower_bound)
            self.assertFalse(result.contact_authorized)

    def test_scene_contract_hash_is_required(self):
        with self.assertRaisesRegex(ValueError, "scene_contract_sha256"):
            evidence(scene_contract_sha256="")
        nodes = {"root": belief("root", 0, margins(), True)}
        with self.assertRaisesRegex(ValueError, "SHA-256 pinned"):
            evaluate_bounded_handoff(
                nodes, "root", horizon_steps=2, step_dt_s=0.02,
                remaining_push_budget_s=0.04,
                expected_policy_sha256=POLICY, expected_control_sha256=CONTROL,
                expected_model_sha256="c" * 64,
                expected_calibration_manifest_sha256="d" * 64,
                expected_scene_case="toy-scene", expected_scene_contract_sha256="",
                expected_entry_distribution_sha256="e" * 64,
                required_joint_coverage=0.95,
                required_coverage_confidence=0.95,
                evidence=evidence(),
            )

    def test_missing_safety_component_cannot_be_certified(self):
        incomplete = margins()
        del incomplete["invalid_hand_contact"]
        nodes = {"root": belief("root", 0, incomplete, True)}
        self.assertEqual(evaluate(nodes, evidence()).verdict, "abstain")

    def test_unvalidated_action_cannot_supply_a_winning_policy(self):
        nodes = {
            "root": belief("root", 0, margins(), False,
                               (edge("hold", ("goal",)),)),
            "goal": belief("goal", 1, margins(), True),
        }
        result = evaluate(nodes, evidence(validated_action_ids=frozenset()))
        self.assertEqual(result.verdict, "abstain")
        self.assertEqual(result.reason, "no_inner_policy_proved_by_supplied_bounds")

    def test_ik_goal_without_executed_command_enclosure_abstains(self):
        nodes = {
            "root": belief("root", 0, margins(), False,
                           (edge("arm-approach", ("goal",)),)),
            "goal": belief("goal", 1, margins(), True),
        }
        proof = evidence(coverage_horizon_steps=1,
                         validated_action_ids=frozenset({"arm-approach"}),
                         command_realization_enclosure_validated=False)
        result = evaluate(nodes, proof, horizon_steps=1)
        self.assertEqual(result.verdict, "abstain")
        self.assertEqual(result.reason, "unvalidated_command_realization")
        self.assertIsNone(result.joint_coverage_lower_bound)
        self.assertEqual(evaluate(nodes, replace(proof,
                         command_realization_enclosure_validated=True),
                         horizon_steps=1).verdict, "model_conditional_inner_set")

    def test_validation_flags_reject_truthy_non_boolean_values(self):
        for name in ("state_enclosure_validated", "transition_enclosure_validated",
                     "command_realization_enclosure_validated", "observation_partition_validated"):
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, name):
                evidence(**{name: "false"})

    def test_bad_graph_is_rejected(self):
        nodes = {
            "root": belief("root", 0, margins(), False,
                               (edge("hold", ("root",)),)),
        }
        with self.assertRaisesRegex(ValueError, "advance exactly one step"):
            evaluate(nodes, evidence())

    def test_observation_history_identity_is_required_and_time_consistent(self):
        nodes = {"root": BeliefNode("root", 0, margins(), True)}
        with self.assertRaisesRegex(ValueError, "Missing observation history"):
            evaluate(nodes, evidence())
        nodes = {
            "root": belief("root", 0, margins(), False,
                           (edge("hold", ("goal",)),), history="same"),
            "goal": belief("goal", 1, margins(), True, history="same"),
        }
        with self.assertRaisesRegex(ValueError, "different steps"):
            evaluate(nodes, evidence())

    def test_matched_failure_refutes_only_that_frozen_action_at_that_state(self):
        witness = MatchedActionWitness("1" * 64, "2" * 64, "front-down",
                                       True, "base_contact")
        self.assertEqual(classify_matched_action_witness(witness), "refuted_at_observed_state")
        self.assertEqual(classify_matched_action_witness(
            replace(witness, pre_action_trace_equal=False)), "abstain_unmatched_rollout")
        self.assertEqual(classify_matched_action_witness(
            replace(witness, terminal_reason="box_settled")), "observed_success_only")
        self.assertEqual(classify_matched_action_witness(
            replace(witness, terminal_reason="time_out")), "refuted_at_observed_state")


if __name__ == "__main__":
    unittest.main()
