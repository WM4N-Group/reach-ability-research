"""Explicit SOFTWARE regression: prefix merging must not erase proposed paths.

Uses original pure AINav planner/tree, synthetic 2px public image and fake roles.
No real model, physics, training, native admission or measured cost is involved.
"""
import json
import unittest
from . import test_v4_methods as fixtures
from .test_v4_methods import Journal, FakeWM, canonical, AinavPlanner
from .v4_backbone_adapters import AinavSuccessorAdapter, VLMWMIntentPlanner
from .v4_successor_choice import NominalCost


def plans(actions, *, prefix_terminal=True):
    first = {k: actions[0][k] for k in ('skill', 'target_ref', 'parameters', 'preconditions')}
    second = {k: actions[1][k] for k in ('skill', 'target_ref', 'parameters', 'preconditions')}
    end = dict(skill='CLIMB', target_ref='goal', parameters=dict(surface_height_m=.6), preconditions=[])
    return [dict(plan_id='short', steps=[first], reaches_goal=prefix_terminal),
            dict(plan_id='long', steps=[first, end], reaches_goal=True),
            dict(plan_id='other', steps=[second, end], reaches_goal=True)]


class PrefixRoles:
    def __init__(self, prefix_terminal=True):
        self.prefix_terminal = prefix_terminal
        self.calls = []

    def run(self, role, payload, obs):
        self.calls.append(role)
        if role == 'object_proposer':
            return dict(plans=[dict(plan_id=n, objects=['seen-1'], strategy='EXPLICIT_SOFTWARE')
                               for n in ('short', 'long', 'other')])
        if role == 'skill_proposer':
            return dict(plans=plans(payload['admitted_first_actions'], prefix_terminal=self.prefix_terminal))
        if role == 'evaluator':
            return dict(nodes=[dict(node_id=n['node_id'], executable=True, reward=.5,
                                    evidence='EXPLICIT_SOFTWARE_NOT_NATIVE') for n in payload['tree']['nodes']])
        raise AssertionError(role)


class PrefixBackend:
    kind = 'openai_compatible_vision_api'
    identity = dict(role='EXPLICIT_SOFTWARE_NOT_API')

    def generate(self, request, *, timeout_s):
        return canonical(dict(plans=plans(request['payload']['admitted_first_actions']), selected_plan_id='other'))


class TerminalPrefixTests(unittest.TestCase):
    # Reuse only original contract fixture setup, NOT the old suite's tests.
    setUp = fixtures.SourceSeamTests.setUp
    batch = fixtures.SourceSeamTests.batch

    def provider(self, missing_short=False):
        self.evaluated = []
        def cost(obs, path, *, query_sha256):
            steps = tuple(json.loads(s)['target_ref'] for s in path.steps_json)
            self.evaluated.append((steps, path.path_id))
            if missing_short and len(steps) == 1:
                return NominalCost(path.path_id, query_sha256, 'UNKNOWN', None, False,
                                   'EXPLICIT_SOFTWARE_MISSING_COMPLETE_TERMINAL')
            value = 1. if len(steps) == 1 else 20. if steps[0] == 'seen-1' else 5.
            return NominalCost(path.path_id, query_sha256, 'KNOWN_NOMINAL', value, True,
                               'EXPLICIT_SOFTWARE_COMPLETE_COST_NOT_ACTUAL')
        return cost

    def adapter(self, cost, *, enabled=True, prefix_terminal=True):
        roles = PrefixRoles(prefix_terminal)
        base = AinavPlanner(roles, self.journal, plan_count=3)
        return AinavSuccessorAdapter(base, optimizer_enabled=enabled, path_cost=cost,
                                     journal=self.journal, software_fixture=True)

    def test_D_enumerates_terminal_prefix_AND_longer_continuation(self):
        p = self.adapter(self.provider()); b = self.batch(); selection = p.select(b)
        self.assertEqual({s for s, _ in self.evaluated},
                         {('seen-1',), ('seen-1', 'goal'), ('seen-2', 'goal')})
        self.assertEqual(len({name for _, name in self.evaluated}), 3)
        self.assertEqual(selection.option_sha256, b.options[0].sha256)
        self.assertEqual(len(p.last_choice['selected_path'].steps_json), 1)

    def test_B_D_compare_same_proposals_despite_tree_prefix_merging(self):
        batches = self.batch(); domains = []; chosen = []
        for arm in ('B', 'D'):
            cost = self.provider()
            p = (VLMWMIntentPlanner(PrefixBackend(), FakeWM(), optimizer_enabled=True,
                                   path_cost=cost, journal=Journal(), software_fixture=True)
                 if arm == 'B' else self.adapter(cost))
            chosen.append(p.select(batches).option_sha256)
            domains.append({s for s, _ in self.evaluated})
        self.assertEqual(domains[0], domains[1])
        self.assertEqual(chosen, [batches.options[0].sha256] * 2)

    def test_terminal_flag_does_not_override_unknown_cost_or_terminal_model(self):
        p = self.adapter(self.provider(missing_short=True)); selection = p.select(self.batch())
        self.assertEqual(len(self.evaluated), 3)
        self.assertFalse(p.last_choice['optimization_applied'])
        self.assertIs(selection, p.baseline.pending)
        self.assertEqual(p.last_choice['reason'], 'UNKNOWN_OR_PARTIAL_SUCCESSOR_KEEP_ORIGINAL_BASELINE')

    def test_nonterminal_internal_node_is_not_invented_as_complete_plan(self):
        p = self.adapter(self.provider(), prefix_terminal=False); p.select(self.batch())
        self.assertEqual({s for s, _ in self.evaluated}, {('seen-1', 'goal'), ('seen-2', 'goal')})

    def test_D_does_not_mutate_original_tree_terminal_or_children(self):
        batch = self.batch()
        c = self.adapter(None, enabled=False); c.select(batch)
        expected = c.baseline.tree.public()
        d = self.adapter(self.provider()); d.select(batch)
        self.assertEqual(d.baseline.tree.public(), expected)
        self.assertEqual(d.baseline.roles.calls, c.baseline.roles.calls)

    def test_nonterminal_leaf_still_requires_provider_and_unknown_falls_back(self):
        class PartialRoles(PrefixRoles):
            def run(self, role, payload, obs):
                result = super().run(role, payload, obs)
                if role == 'skill_proposer':
                    result['plans'][2]['reaches_goal'] = False
                return result
        base = AinavPlanner(PartialRoles(), self.journal, plan_count=3)
        seen = []
        def cost(obs, path, *, query_sha256):
            first = json.loads(path.steps_json[0])['target_ref']; seen.append(first)
            return NominalCost(path.path_id, query_sha256,
                'UNKNOWN' if first == 'seen-2' else 'KNOWN_NOMINAL',
                None if first == 'seen-2' else 1., first != 'seen-2', 'EXPLICIT_SOFTWARE')
        d = AinavSuccessorAdapter(base, optimizer_enabled=True, path_cost=cost,
                                 journal=self.journal, software_fixture=True)
        d.select(self.batch())
        self.assertIn('seen-2', seen)
        self.assertFalse(d.last_choice['optimization_applied'])

    def test_C_off_keeps_original_tree_and_no_cost_evaluation(self):
        def no_cost(*args, **kwargs):
            raise AssertionError('C must never invoke cost')
        p = self.adapter(no_cost, enabled=False); selection = p.select(self.batch())
        self.assertIs(selection, p.baseline.pending)
        root = next(n for n in p.baseline.tree.root.children.values() if n.step.target_ref == 'seen-1')
        self.assertTrue(root.terminal and root.children)
        self.assertFalse(any(x['event'] == 'reach_v4_shared_optimizer_choice' for x in self.journal))


if __name__ == '__main__':
    unittest.main()
