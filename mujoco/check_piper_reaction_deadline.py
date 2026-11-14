"""Checks for the loaded-contact reaction deadline condition."""

import json
import math
from pathlib import Path
import unittest

from reconfigurable_navigation.reachability.reaction_deadline import (
    LoadedReactionActionEvidence,
    assess_allowed_loaded_reaction_deadline,
    assess_loaded_contact_reaction_deadline,
)


DT = 0.005


def tick(time_s):
    result = round(time_s / DT)
    if not math.isclose(result * DT, time_s, abs_tol=1e-12):
        raise ValueError("Evidence time is off the frozen substep clock")
    return result


class ReactionDeadlineTests(unittest.TestCase):
    def test_all_action_result_requires_every_action_to_be_too_late(self):
        actions = (
            LoadedReactionActionEvidence("leg", 4, True),
            LoadedReactionActionEvidence("arm_and_leg", 5, True),
        )
        result = assess_allowed_loaded_reaction_deadline(
            first_illegal_substep=104,
            prior_legal_loaded_control_end_substep=100,
            allowed_actions=actions,
            allowed_action_set_complete=True,
        )
        self.assertEqual(result.state, "conditional_all_allowed_reactions_too_late")
        self.assertEqual(result.available_substeps, 4)
        self.assertFalse(result.contact_authorized)
        earlier = (actions[0], LoadedReactionActionEvidence("arm_and_leg", 3, True))
        self.assertEqual(assess_allowed_loaded_reaction_deadline(
            first_illegal_substep=104,
            prior_legal_loaded_control_end_substep=100,
            allowed_actions=earlier,
            allowed_action_set_complete=True,
        ).state, "undetermined")

    def test_all_action_result_abstains_on_missing_proof(self):
        certified = LoadedReactionActionEvidence("leg", 4, True)
        cases = (
            ((certified,), False, "abstain_incomplete_action_set"),
            ((certified, LoadedReactionActionEvidence("arm", None, True)), True,
             "abstain_missing_effect_delay_lower_bound"),
            ((certified, LoadedReactionActionEvidence("arm", 4, False)), True,
             "abstain_missing_counterfactual_prefix"),
        )
        for actions, complete, expected in cases:
            with self.subTest(expected=expected):
                result = assess_allowed_loaded_reaction_deadline(
                    first_illegal_substep=104,
                    prior_legal_loaded_control_end_substep=100,
                    allowed_actions=actions,
                    allowed_action_set_complete=complete,
                )
                self.assertEqual(result.state, expected)
                self.assertFalse(result.contact_authorized)

    def test_all_action_result_rejects_invalid_action_sets(self):
        certified = LoadedReactionActionEvidence("leg", 4, True)
        for actions, complete in (
            ((), True), ((certified, certified), True),
            ((LoadedReactionActionEvidence(" ", 4, True),), True),
            ((LoadedReactionActionEvidence("leg", -1, True),), True),
            ((LoadedReactionActionEvidence("leg", 4, 1),), True),
            ((certified,), 1),
        ):
            with self.subTest(actions=actions, complete=complete):
                with self.assertRaises(ValueError):
                    assess_allowed_loaded_reaction_deadline(
                        first_illegal_substep=104,
                        prior_legal_loaded_control_end_substep=100,
                        allowed_actions=actions,
                        allowed_action_set_complete=complete,
                    )

    def test_all_action_without_loaded_anchor_has_no_reaction_trigger(self):
        result = assess_allowed_loaded_reaction_deadline(
            first_illegal_substep=100,
            prior_legal_loaded_control_end_substep=None,
            allowed_actions=(LoadedReactionActionEvidence("arm", None, False),),
            allowed_action_set_complete=False,
        )
        self.assertEqual(result.state, "conditional_no_prior_loaded_anchor")
        self.assertFalse(result.contact_authorized)

    def test_missing_anchor_is_only_a_loaded_reaction_limit(self):
        result = assess_loaded_contact_reaction_deadline(
            first_illegal_substep=100,
            prior_legal_loaded_control_end_substep=None,
            earliest_effect_delay_lower_bound_substeps=None,
        )
        self.assertEqual(result.state, "conditional_no_prior_loaded_anchor")
        self.assertIsNone(result.available_substeps)
        self.assertFalse(result.contact_authorized)

    def test_certified_earliest_effect_at_event_is_too_late(self):
        result = assess_loaded_contact_reaction_deadline(
            first_illegal_substep=102,
            prior_legal_loaded_control_end_substep=100,
            earliest_effect_delay_lower_bound_substeps=2,
        )
        self.assertEqual(result.state, "conditional_reaction_too_late")
        self.assertEqual(result.available_substeps, 2)
        self.assertEqual(assess_loaded_contact_reaction_deadline(
            first_illegal_substep=102,
            prior_legal_loaded_control_end_substep=100,
            earliest_effect_delay_lower_bound_substeps=1,
        ).state, "undetermined")

    def test_seen_6403_6415_have_no_measured_effect_delay(self):
        path = Path(__file__).resolve().parents[1] / (
            "evidence/2026-10-09/lateral-loaded-boundary-clock-6401-6416.json"
        )
        evidence = json.loads(path.read_text(encoding="utf-8"))
        for seed, expected_ticks in ((6403, 4), (6415, 2)):
            record = next(row for row in evidence["records"] if row["seed"] == seed)
            event = record["first_illegal"]
            anchor = event["prior_legal_loaded_control_step_ends_in_same_bout"][-1]
            result = assess_loaded_contact_reaction_deadline(
                first_illegal_substep=tick(event["time_s"]),
                prior_legal_loaded_control_end_substep=tick(anchor["control_step_end_s"]),
                earliest_effect_delay_lower_bound_substeps=None,
            )
            self.assertEqual(result.available_substeps, expected_ticks)
            self.assertEqual(result.state, "abstain_missing_effect_delay_lower_bound")
            self.assertFalse(result.contact_authorized)
            all_actions = assess_allowed_loaded_reaction_deadline(
                first_illegal_substep=tick(event["time_s"]),
                prior_legal_loaded_control_end_substep=tick(anchor["control_step_end_s"]),
                allowed_actions=(LoadedReactionActionEvidence("deployment_arm_leg_class", None, False),),
                allowed_action_set_complete=False,
            )
            self.assertEqual(all_actions.state, "abstain_incomplete_action_set")
            self.assertFalse(all_actions.contact_authorized)

    def test_invalid_clock_and_delay_are_rejected(self):
        for event, anchor, delay in ((0, None, None), (True, None, None),
                                     (10, 10, 0), (10, 11, 0),
                                     (10, 9, -1), (10, 9, True)):
            with self.subTest(event=event, anchor=anchor, delay=delay):
                with self.assertRaises(ValueError):
                    assess_loaded_contact_reaction_deadline(
                        first_illegal_substep=event,
                        prior_legal_loaded_control_end_substep=anchor,
                        earliest_effect_delay_lower_bound_substeps=delay,
                    )


if __name__ == "__main__":
    unittest.main()
