"""Explicit fresh-fork extension: same registry factory, goal-sealed lookup only.

Does not construct the factory, controllers, Runtime, native goals or a world.
The caller must generate goal-sealed placement contracts before query binding.
Both A/B use the exact same extension. Original published source is untouched.
"""
from pathlib import Path
import ast,hashlib,importlib,sys,textwrap
FACTORY_SHA='2da2c075e1316ab81251ac71f72004b927e769bfd88047a3af1a171d8d1d387e'
OLD="""contract=self.contracts.get(obj.ref)
        if contract is None or contract.target_ref!=obj.ref or contract.sha256!=self.contract_hashes[obj.ref]:raise ValueError('Immutable associated placement contract required')"""
NEW="""key=(obj.ref,option.original_push_goal_sha256)
        contract=self.contracts.get(key)
        if contract is None or contract.target_ref!=obj.ref or contract.sha256!=self.contract_hashes[key]:raise ValueError('Immutable associated placement contract required')"""

def factory_class(*,source_root=None,enabled=False):
    if type(enabled)is not bool:raise ValueError('Explicit default-off opt-in')
    if not enabled:return None
    root=Path(source_root).resolve(strict=True);p=root/'ainav/native/registered_skill_factory.py'
    raw=p.read_bytes()
    if p.is_symlink()or hashlib.sha256(raw).hexdigest()!=FACTORY_SHA:raise ValueError('Exact original common registry factory required')
    text=raw.decode();tree=ast.parse(text);cls=next(n for n in tree.body if isinstance(n,ast.ClassDef)and n.name=='RegisteredSkillSessionFactory')
    fn=next(n for n in cls.body if isinstance(n,ast.FunctionDef)and n.name=='prospective_push_contract');original=ast.get_source_segment(text,fn)
    if original.count(OLD)!=1:raise ValueError('One exact contract lookup, no other method changes')
    changed=original.replace(OLD,NEW,1)
    if changed.replace(NEW,OLD,1)!=original:raise ValueError('Source delta must exactly invert')
    sys.path.insert(0,str(root));module=importlib.import_module('ainav.native.registered_skill_factory')
    if Path(module.__file__).resolve()!=p:raise ValueError('Same-source original factory module required')
    namespace=dict(vars(module));exec(compile(textwrap.dedent(changed),str(p)+'[T-COMPLEX-01-exact-goal-seal-lookup]','exec'),namespace)
    result=type('ComplexMultiGoalRegisteredSkillSessionFactory',(module.RegisteredSkillSessionFactory,),{'prospective_push_contract':namespace['prospective_push_contract']})
    result.source_delta_receipt=dict(original_source_sha256=FACTORY_SHA,changed_method='prospective_push_contract',change='Object-only single-goal lookup -> (registered object, SAME option original_push_goal_sha256) immutable contract lookup',all_original_query_body_world_FIFO_binding_checks_retained=True,inverse_restores_original_method=True,native_controller_or_guards_changed=False,actual_dynamic_qualification=False)
    return result
