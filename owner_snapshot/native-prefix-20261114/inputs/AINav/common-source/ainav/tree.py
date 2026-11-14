"""AINav prefix tree and Eq.(3) mean-child return; no dynamics or MCTS."""
from dataclasses import dataclass, field
import math
from .contracts import Primitive, SkillPlan, finite


@dataclass
class Node:
    node_id: str
    step: Primitive | None = None
    children: dict = field(default_factory=dict)
    terminal: bool = False
    reward: float = 0.
    q: float = 0.
    evidence: str = ''


class SkillTree:
    def __init__(self, *, gamma=.9, terminal_bonus=1., max_nodes=256):
        if not finite(gamma) or not 0 <= gamma <= 1 or not finite(terminal_bonus) or terminal_bonus < 0:
            raise ValueError('Explicit finite discount/terminal reward required')
        if type(max_nodes) is not int or not 2 <= max_nodes <= 4096:
            raise ValueError('Bounded tree size required')
        self.gamma, self.terminal_bonus, self.max_nodes = gamma, terminal_bonus, max_nodes
        self.root = Node('root')
        self.next_id = 0
        self.history = []
        self.epoch = None
        self.revision = 0

    def nodes(self):
        result = []
        def visit(node):
            for child in node.children.values():
                result.append(child)
                visit(child)
        visit(self.root)
        return tuple(result)

    def add(self, plans):
        if not isinstance(plans, tuple) or not all(isinstance(p, SkillPlan) for p in plans):
            raise ValueError('Typed skill plans required')
        # Validate prospective growth before changing the current tree.
        existing = set()
        def paths(node, path=()):
            for child in node.children.values():
                p = path + (child.step.key,)
                existing.add(p)
                paths(child, p)
        paths(self.root)
        proposed = set(existing)
        for plan in plans:
            path = ()
            for step in plan.steps:
                path += (step.key,)
                proposed.add(path)
        if len(proposed) > self.max_nodes:
            raise ValueError('Tree node budget exceeded; no partial expansion installed')
        for plan in plans:
            parent = self.root
            for step in plan.steps:
                if step.key not in parent.children:
                    self.next_id += 1
                    parent.children[step.key] = Node('n'+str(self.next_id), step)
                parent = parent.children[step.key]
            parent.terminal |= plan.reaches_goal
        self.epoch = None
        self.revision += 1

    def prune(self, node_ids):
        if not isinstance(node_ids, (tuple, list)) or len(set(node_ids)) != len(node_ids):
            raise ValueError('Distinct prune IDs required')
        valid = {n.node_id for n in self.nodes()}
        if not set(node_ids) <= valid:
            raise ValueError('Cannot prune root, executed history or unknown nodes')
        chosen = set(node_ids)
        def visit(node):
            for key, child in list(node.children.items()):
                if child.node_id in chosen:
                    del node.children[key]
                else:
                    visit(child)
        visit(self.root)
        self.epoch = None
        self.revision += 1

    def evaluate(self, rows, epoch):
        if not isinstance(epoch, str) or len(epoch) != 64:
            raise ValueError('Evaluation must bind the current immutable public query')
        nodes = {n.node_id: n for n in self.nodes()}
        if not isinstance(rows, list) or len(rows) != len(nodes):
            raise ValueError('Every current tree node needs exactly one evaluation')
        parsed = {}
        for row in rows:
            if (not isinstance(row, dict) or set(row) != {'node_id', 'executable', 'reward', 'evidence'}
                    or not isinstance(row['node_id'], str) or row['node_id'] not in nodes or row['node_id'] in parsed
                    or type(row['executable']) is not bool or not finite(row['reward']) or not 0 <= row['reward'] <= 1
                    or not isinstance(row['evidence'], str) or not row['evidence'] or len(row['evidence']) > 2048):
                raise ValueError('Invalid, duplicate or ungrounded node evaluation')
            # Feasibility dominates the semantic reward, as in AINav:
            # non-executable nodes are removed below, even if the LLM gave
            # them positive task contribution. Raw replies remain in evidence.
            parsed[row['node_id']] = row
        # Atomic validation above: malformed output cannot partly edit a tree.
        invalid = [k for k, row in parsed.items() if not row['executable']]
        if invalid:
            self.prune(invalid)
        for node in self.nodes():
            row = parsed[node.node_id]
            node.reward, node.evidence = float(row['reward']), row['evidence']
        def backup(node):
            child_values = [backup(c) for c in node.children.values()]
            future = self.gamma * sum(child_values) / len(child_values) if child_values else 0.
            node.q = node.reward + future + (self.terminal_bonus if node.terminal and not child_values else 0.)
            if not math.isfinite(node.q):
                raise ValueError('Nonfinite backed-up value rejected')
            return node.q
        backup(self.root)
        self.epoch = epoch
        self.revision += 1
        return tuple(invalid)

    def select(self, command_keys, epoch):
        if self.epoch != epoch:
            raise RuntimeError('Stale tree scores cannot control a new public query')
        candidates = [n for n in self.root.children.values() if n.step.command_key in command_keys]
        if not candidates:
            raise ValueError('No root action has current native admission; no fallback')
        selected = max(candidates, key=lambda n: (n.q, n.node_id))
        result = [selected]
        while result[-1].children:
            result.append(max(result[-1].children.values(), key=lambda n: (n.q, n.node_id)))
        return tuple(result)

    def advance(self, primitive_key, *, receipt_ref):
        if not receipt_ref or primitive_key not in self.root.children:
            raise ValueError('Only an actually completed root primitive may advance the tree')
        node = self.root.children[primitive_key]
        self.history.append(dict(step=node.step.public(), receipt_ref=receipt_ref))
        # The completed node is not a terminal hypothesis for the new root.
        self.root = Node('root', children=node.children)
        self.epoch = None
        self.revision += 1

    def public(self):
        rows = []
        def visit(node, parent='root'):
            for child in node.children.values():
                rows.append(dict(node_id=child.node_id, parent=parent, step=child.step.public(),
                                 hypothetical_goal_leaf=child.terminal, reward=child.reward, q=child.q))
                visit(child, child.node_id)
        visit(self.root)
        return dict(revision=self.revision, evaluation_query_sha256=self.epoch,
                    gamma=self.gamma, terminal_bonus=self.terminal_bonus,
                    backup='immediate + gamma * mean(children); terminal bonus at leaves',
                    executed_history=list(self.history), nodes=rows)
