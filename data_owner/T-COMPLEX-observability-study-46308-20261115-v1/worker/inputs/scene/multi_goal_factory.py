"""Fresh-fork common factory: finite immutable goals, exact query goal seals.

No factory/controller/world construction here. The same extension is shared by
both policies; actual prospective goal arrays are sealed by the ORIGINAL
resolver, never synthesized from static geometry. Original source untouched.
"""
from pathlib import Path
from types import MappingProxyType
import ast,hashlib,importlib,sys,textwrap
FACTORY_SHA='2da2c075e1316ab81251ac71f72004b927e769bfd88047a3af1a171d8d1d387e'
OLD="""contract=self.contracts.get(obj.ref)
        if contract is None or contract.target_ref!=obj.ref or contract.sha256!=self.contract_hashes[obj.ref]:raise ValueError('Immutable associated placement contract required')"""
NEW="""key=(obj.ref,option.original_push_goal_sha256)
        if getattr(self,'_complex_contract_query',None)!=query_sha256:raise ValueError('Exact current query contract seals required')
        contract=self._complex_query_contracts.get(key)
        if (contract is None or contract.target_ref!=obj.ref or self.contracts.get(contract.sha256) is not contract
                or contract.sha256!=self.contract_hashes[contract.sha256]):raise ValueError('Immutable associated placement contract required')
        actual=binding.view.box_push_target
        if hasattr(actual,'detach'):actual=actual.detach().cpu().numpy()
        if hasattr(actual,'tolist'):actual=actual.tolist()
        if (len(actual)!=1 or len(actual[0])<2 or
                any(abs(float(actual[0][j])-contract.drive_goal_xy_m[j])>1e-6 for j in range(2))):
            raise ValueError('Original actual native goal differs from declared public placement contract')"""

def _install_query_contracts(self,query_sha256,option_contract_pairs):
    """Register exact already-prepared same-query seals, no native controller.

    Constructor placement_contracts is the FINITE immutable catalogue keyed by
    contract.sha256. This per-query map expires on the next query and does not
    mutate that catalogue. Original bind_batch still seals world/target/history.
    """
    from ainav.native.behavior_authority import BehaviorOption
    if not isinstance(query_sha256,str)or len(query_sha256)!=64 or query_sha256 in self.used_queries:raise ValueError('Fresh actual query SHA required')
    if getattr(self,'_complex_contract_query',None)==query_sha256:raise ValueError('No query seal replacement or second install')
    if self.executor is None:raise ValueError('Attach the actual same-world executor before query binding')
    if self.executor.session is not None and (not self.executor.reported_end or self.executor.last_outcome!='succeeded'):raise ValueError('Cannot prebind a query while an earlier owner runs or failed')
    frozen={}
    for option,contract in option_contract_pairs:
        if not isinstance(option,BehaviorOption)or option.skill!='PUSH' or self.contracts.get(contract.sha256)is not contract or self.contract_hashes.get(contract.sha256)!=contract.sha256:raise ValueError('Exact original option and immutable finite placement catalogue required')
        key=(contract.target_ref,option.original_push_goal_sha256)
        if key in frozen:raise ValueError('Duplicate same-object/native-goal seal')
        frozen[key]=contract
    if not frozen:raise ValueError('At least one actually prepared PUSH goal required')
    self._complex_contract_query=query_sha256;self._complex_query_contracts=MappingProxyType(frozen)

def factory_class(*,source_root=None,enabled=False):
    if type(enabled)is not bool:raise ValueError('Explicit default-off opt-in')
    if not enabled:return None
    root=Path(source_root).resolve(strict=True);p=root/'ainav/native/registered_skill_factory.py';raw=p.read_bytes()
    if p.is_symlink()or hashlib.sha256(raw).hexdigest()!=FACTORY_SHA:raise ValueError('Exact original common registry factory required')
    text=raw.decode();tree=ast.parse(text);cls=next(n for n in tree.body if isinstance(n,ast.ClassDef)and n.name=='RegisteredSkillSessionFactory');fn=next(n for n in cls.body if isinstance(n,ast.FunctionDef)and n.name=='prospective_push_contract');original=ast.get_source_segment(text,fn)
    if original.count(OLD)!=1:raise ValueError('One exact contract lookup, no other method changes')
    changed=original.replace(OLD,NEW,1)
    if changed.replace(NEW,OLD,1)!=original:raise ValueError('Source delta must exactly invert')
    sys.path.insert(0,str(root));module=importlib.import_module('ainav.native.registered_skill_factory')
    if Path(module.__file__).resolve()!=p:raise ValueError('Same-source original factory module required')
    namespace=dict(vars(module));exec(compile(textwrap.dedent(changed),str(p)+'[T-COMPLEX-01-exact-query-goal-contract]','exec'),namespace)
    result=type('ComplexMultiGoalRegisteredSkillSessionFactory',(module.RegisteredSkillSessionFactory,),{'__module__':__name__,'prospective_push_contract':namespace['prospective_push_contract'],'install_query_contracts':_install_query_contracts})
    result.source_delta_receipt=dict(original_source_sha256=FACTORY_SHA,changed_method='prospective_push_contract',change='Immutable finite placement catalogue + exact query/object/native-goal-seal lookup and actual native XY correspondence',all_original_query_body_world_FIFO_binding_checks_retained=True,inverse_restores_original_method=True,native_controller_or_guards_changed=False,actual_dynamic_qualification=False)
    return result
