"""Two-level proposal, primitive tree, evaluator, advisor and arborist."""
from dataclasses import dataclass
from .contracts import DecisionBatch, Primitive, SkillPlan, exact, sha, text
from .tree import SkillTree


@dataclass(frozen=True)
class Selection:
    query_sha256: str
    token: str
    option_sha256: str
    primitive_key: str
    tree_revision: int
    evidence_ref: str


class AinavPlanner:
    def __init__(self, roles, journal, *, plan_count=5, gamma=.9, terminal_bonus=1., max_role_calls=8):
        if type(plan_count) is not int or not 2 <= plan_count <= 5:
            raise ValueError('Two to five distinct object strategies required')
        if type(max_role_calls) is not int or not 3 <= max_role_calls <= 10:
            raise ValueError('Explicit bounded role-call budget required')
        self.roles, self.journal = roles, journal
        self.plan_count, self.max_role_calls = plan_count, max_role_calls
        self.tree = SkillTree(gamma=gamma, terminal_bonus=terminal_bonus)
        self.last_observation = None
        self.pending = None
        self.events = []
        self.calls = 0

    def _role(self, role, payload, observation):
        if self.calls >= self.max_role_calls:
            raise RuntimeError('Per-decision VLM call budget exhausted; no retry/fallback')
        self.calls += 1
        result=self.roles.run(role,payload,observation)
        if isinstance(result,dict) and result.get('type')=='json_object':
            result={k:v for k,v in result.items() if k!='type'}
            self.journal(dict(event='transport_format_marker_ignored',role=role,
                ignored_field='type=json_object',action_values_or_ids_changed=False))
        return result

    def _expand(self, batch):
        payload = dict(batch.public(), plan_count=self.plan_count, allowed_target_refs=sorted(batch.observation.targets), skill_parameter_schema={
            'NAV':{'required':['goal_world_x_m','goal_world_y_m','surface_height_m'],'values':'finite numbers; same declared map coordinates'},
            'PUSH':{'oneOf':[{'required':['push_distance_m','surface_height_m']},{'required':['goal_world_x_m','goal_world_y_m','surface_height_m']}],'push_distance_m':[.2,.4,.6],'surface_height_m':[0.,.4],'meaning':'relative displacement OR public absolute placement XY; match an admitted first action exactly'},
            'CLIMB':{'required':['surface_height_m'],'surface_height_m':[.2,.4,.6],'meaning':'destination surface height, not current support'},
            'HOLD':{'required':['surface_height_m'],'surface_height_m':[.6]},
            'EXIT_PUSH':{'required':['push_distance_m','surface_height_m'],'meaning':'same immutable attempt parameters, native protection only'},
            'RECOVER':{'required':[],'meaning':'native protection only'}},
            parameter_rules='Only these numeric keys; no symbolic/string values inside parameters. Preconditions are separate strings. Future map-object placeholders are hypotheses, not native binding certificates.')
        obj = self._role('object_proposer', payload, batch.observation)
        exact(obj, ('plans',), 'object proposer output')
        if not isinstance(obj['plans'], list) or not 1 <= len(obj['plans']) <= self.plan_count:
            raise ValueError('Bounded object strategy list required')
        ids=set();accepted_objects=[];rejected=[]
        for plan in obj['plans']:
            try:
                exact(plan, ('plan_id', 'objects', 'strategy'), 'object plan')
                text(plan['plan_id'], 'plan ID', 80);text(plan['strategy'], 'strategy', 2048)
                if (not isinstance(plan['objects'],list) or not all(isinstance(x,str) for x in plan['objects'])
                        or not set(plan['objects']) <= batch.observation.targets or plan['plan_id'] in ids):
                    raise ValueError('Unknown target or repeated plan identity')
                ids.add(plan['plan_id']);accepted_objects.append(plan)
            except (ValueError,TypeError) as error:
                rejected.append(dict(stage='object',plan_id=plan.get('plan_id') if isinstance(plan,dict) else None,reason=str(error)))
        if not accepted_objects:raise ValueError('No valid object strategies; no fallback')
        result = self._role('skill_proposer', dict(payload, plan_count=len(accepted_objects),
            object_plans=accepted_objects), batch.observation)
        exact(result, ('plans',), 'skill proposer output')
        if not isinstance(result['plans'],list) or not 1 <= len(result['plans']) <= self.plan_count:
            raise ValueError('Bounded skill expansions required')
        supported=batch.public()['capability_contract']['skills']
        legal={Primitive.from_option(x).command_key for x in batch.options}
        valid=[];seen=set()
        for row in result['plans']:
            try:
                plan=SkillPlan.parse(row,batch.observation.targets)
                if plan.plan_id not in ids or plan.plan_id in seen:
                    raise ValueError('Unknown or duplicate object/skill plan identity')
                if any(step.skill not in supported for step in plan.steps):
                    raise ValueError('Future step invented an unsupported robot capability')
                if plan.steps[0].command_key not in legal:
                    raise ValueError('First step lacks exact current native admission')
                seen.add(plan.plan_id);valid.append(plan)
            except (ValueError,TypeError) as error:
                rejected.append(dict(stage='skill',plan_id=row.get('plan_id') if isinstance(row,dict) else None,reason=str(error)))
        if rejected:self.journal(dict(event='invalid_model_plans_quarantined',query_sha256=batch.sha256,
             rejected=rejected,accepted_object_plan_count=len(accepted_objects),accepted_skill_plan_count=len(valid),
             generated_actions_by_code=False,native_guard_relaxed=False))
        if not valid:raise ValueError('No valid model skill plans; no fallback')
        plans=tuple(valid)
        # Object-level strategies may legitimately map to identical primitives.
        # AINav merges common traces, including complete duplicate paths. Do not
        # fabricate extra maneuvers or reject an otherwise valid native choice.
        unique_skill_plans = len({sha([s.public() for s in p.steps]) for p in plans})
        self.tree.add(plans)
        self.journal(dict(event='primitive_tree_expanded', query_sha256=batch.sha256,
                          object_plans=obj, skill_plans=result, unique_skill_plans=unique_skill_plans,
                          duplicate_skill_plans_merged=len(plans)-unique_skill_plans, tree=self.tree.public()))

    def select(self, batch):
        if not isinstance(batch, DecisionBatch) or any(x.mandatory_protection for x in batch.options):
            raise ValueError('Planner receives a typed task-choice batch, not mandatory safety')
        if self.pending is not None:
            raise RuntimeError('Actual previous execution outcome required before another selection')
        self.calls = 0
        legal = {Primitive.from_option(x).command_key for x in batch.options}
        if len(legal) != len(batch.options):
            raise ValueError('Ambiguous same-command native candidates rejected')
        had_tree = bool(self.tree.nodes())
        if had_tree and self.last_observation is not None:
            events = batch.observation.value['events'] + list(self.events)
            old_ids = {x['target_ref'] for x in self.last_observation.value['objects']}
            new_ids = {x['target_ref'] for x in batch.observation.value['objects']}
            if new_ids-old_ids:
                events.append(dict(kind='new_objects', description='New observed targets: '+','.join(sorted(new_ids-old_ids)),
                                   evidence_ref=batch.observation.sha256))
            advice = self._role('advisor', dict(batch.public(), tree=self.tree.public(), new_events=events), batch.observation)
            exact(advice, ('replan', 'triggers', 'reason'), 'advisor output')
            if (type(advice['replan']) is not bool or not isinstance(advice['triggers'], list)
                    or any(x not in ('failure', 'new_objects', 'revaluation') for x in advice['triggers'])
                    or not isinstance(advice['reason'], str) or not advice['reason']):
                raise ValueError('Typed advisor interpretation required')
            # Actual failure and loss of current admission cannot be overruled by VLM.
            forced = any(x['kind'] == 'failure' for x in events) or not any(n.step.command_key in legal for n in self.tree.root.children.values())
            if advice['replan'] or forced:
                edits = self._role('arborist', dict(batch.public(), tree=self.tree.public(), advisor=advice,
                                   forced_by_actual_failure_or_no_admitted_root=forced,
                                   inadmissible_root_nodes=[n.node_id for n in self.tree.root.children.values() if n.step.command_key not in legal]), batch.observation)
                exact(edits, ('prune_node_ids', 'expand', 'reason'), 'arborist output')
                if (not isinstance(edits['prune_node_ids'], list) or not all(isinstance(x, str) for x in edits['prune_node_ids'])
                        or type(edits['expand']) is not bool or not isinstance(edits['reason'], str) or not edits['reason']):
                    raise ValueError('Typed arborist edit required')
                self.tree.prune(edits['prune_node_ids'])
                self.journal(dict(event='arborist_tree_edited', query_sha256=batch.sha256,
                                  advice=advice, edits=edits, tree=self.tree.public()))
                if edits['expand'] or forced:
                    self._expand(batch)
        if not self.tree.nodes():
            self._expand(batch)
        result = self._role('evaluator', dict(batch.public(), tree=self.tree.public()), batch.observation)
        exact(result, ('nodes',), 'evaluator output')
        pruned = self.tree.evaluate(result['nodes'], batch.sha256)
        try:
            path = self.tree.select(legal, batch.sha256)
        except ValueError:
            if self.calls+3>self.max_role_calls:raise
            self.journal(dict(event='semantic_tree_has_no_current_root_regenerate_once',
                query_sha256=batch.sha256,native_actions_still_available=len(legal),
                code_generated_actions=False,physical_retry=False))
            self._expand(batch)
            retry=self._role('evaluator',dict(batch.public(),tree=self.tree.public(),
                clarification='No retained root matched current native actions. Judge contract feasibility, not guaranteed physical success. Native eligible interactions may be risky; lower reward rather than inventing a prohibition.'),batch.observation)
            exact(retry,('nodes',),'evaluator output')
            pruned=tuple(pruned)+self.tree.evaluate(retry['nodes'],batch.sha256)
            path=self.tree.select(legal,batch.sha256)
        selected = path[0]
        option = next(x for x in batch.options if Primitive.from_option(x).command_key == selected.step.command_key)
        ref = self.journal(dict(event='ainav_tree_selection', query_sha256=batch.sha256,
            selected_token=option.token, selected_option_sha256=option.sha256,
            selected_node_id=selected.node_id, selected_primitive_key=selected.step.key,
            hypothetical_skeleton=[x.step.public() for x in path],
            evaluator_pruned_node_ids=list(pruned), tree=self.tree.public(),
            admitted_first_action_count=len(legal),
            tree_first_action_count=len({n.step.command_key for n in self.tree.root.children.values() if n.step.command_key in legal}),
            meaningful_choice=len({n.step.command_key for n in self.tree.root.children.values() if n.step.command_key in legal})>1,
            world_model_used=False,
            semantic_intents_only=bool(getattr(batch,'semantic_intents_only',False)),
            physical_action_issued=False, task_success_inferred=False))
        text(ref, 'durable selection evidence reference')
        selection = Selection(batch.sha256, option.token, option.sha256, selected.step.key, self.tree.revision, ref)
        self.pending = selection
        self.last_observation = batch.observation
        self.events.clear()
        return selection

    def observe(self, option, receipt):
        if self.pending is None or self.pending.option_sha256 != option.sha256 or receipt.option_sha256 != option.sha256:
            raise ValueError('Outcome must bind this planner selected exact native option')
        if receipt.status == 'succeeded':
            self.tree.advance(self.pending.primitive_key, receipt_ref=receipt.evidence_ref)
        elif receipt.status in ('failed', 'hard_stop'):
            # Retain context for advisor/arborist, not a global object ban.
            self.events.append(dict(kind='failure', description=option.skill+' failed on '+option.target_ref,
                                    evidence_ref=receipt.evidence_ref))
            if receipt.status == 'hard_stop':
                self.journal(dict(event='planner_native_hard_stop', task_success_inferred=False))
        elif receipt.status == 'budget_expired':
            self.events.append(dict(kind='revaluation', description='Native interval expired without skill completion',
                                    evidence_ref=receipt.evidence_ref))
        else:
            raise ValueError('Planner completion hook only accepts actual task outcomes')
        self.pending = None


    def reject_intent(self,intent,reason,evidence_ref):
        """A read-only prerequisite rejection is NOT a failed physical receipt."""
        from .intents import SkillIntent
        if not isinstance(intent,SkillIntent) or self.pending is None or self.pending.option_sha256!=intent.sha256:
            raise ValueError('Only the actual pending model intent may be rejected')
        text(reason,'execution rejection');text(evidence_ref,'execution judgment evidence')
        node=self.tree.root.children.get(self.pending.primitive_key)
        if node is not None:self.tree.prune([node.node_id])
        self.events.append(dict(kind='revaluation',description='Execution prerequisites: '+reason,evidence_ref=evidence_ref))
        self.journal(dict(event='planner_intent_prerequisite_rejected',intent_sha256=intent.sha256,reason=reason,
            evidence_ref=evidence_ref,physical_failure_receipt_fabricated=False,tree_advanced=False))
        self.pending=None

    def observe_intent(self,intent,actual_option,receipt,binding_ref):
        """Advance an intent only on its same-skill actual native completion."""
        from .intents import SkillIntent
        if (not isinstance(intent,SkillIntent) or self.pending is None or self.pending.option_sha256!=intent.sha256
            or receipt.option_sha256!=actual_option.sha256 or actual_option.skill!=intent.skill
            or dict(actual_option.parameters)!=dict(intent.parameters)):
            raise ValueError('Actual same-skill/parameters native result required for semantic intent')
        text(binding_ref,'judged same-object execution binding')
        if receipt.status=='succeeded':self.tree.advance(self.pending.primitive_key,receipt_ref=receipt.evidence_ref)
        elif receipt.status in ('failed','hard_stop','budget_expired'):
            self.events.append(dict(kind='failure' if receipt.status!='budget_expired' else 'revaluation',
                description=intent.skill+' actual execution '+receipt.status,evidence_ref=receipt.evidence_ref))
        else:raise ValueError('Actual terminal task outcome required')
        self.journal(dict(event='planner_intent_native_result',intent_sha256=intent.sha256,
            native_option_sha256=actual_option.sha256,binding_ref=binding_ref,receipt_ref=receipt.evidence_ref,
            actual_status=receipt.status,tree_advanced=receipt.status=='succeeded'))
        self.pending=None
