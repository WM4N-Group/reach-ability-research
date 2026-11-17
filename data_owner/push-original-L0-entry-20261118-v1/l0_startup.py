"""Strict L0 ORIGINAL independent PUSH startup, per-physics request source adapter.

Not the L1 Runtime with NAV deleted. No constructor/model/GPU/Actor/IO/dispatch
on import or source assembly. Native use still needs a NEW complete parent,
original safety/lease/watch, actual commands, full freeze/prepare/own-zero.
"""
import ast
import copy
import hashlib
from pathlib import Path
import types

PLAY_SHA = '12a922f19a12cb8bb27feee70efe7e637d62047e25bc54e1d377c1bafac9f2b7'
BRIDGE_SHA = 'fafcc5c7f68db6d2a0a499316fd2707b1a98808d35913e1e847e65b4ae2c4cdc'
RUNTIME_SHA = '2e12846c7a7789b2f44953a12685b3d0221fbd0f9449cd704e8232916877aff5'
CASE = dict(level='L0_ORIGINAL_STANDARD_INITIALIZATION_NOT_NATURAL_PREDECESSOR',
    seed=3701,delay_ms=20,box_size_m=[1.2,1.2,.2],box_mass_kg=1.,
    fresh_robot_xyz_m=[-.08,0.,.33],box_initial_xyz_m=[1.1,0.,.1],
    native_and_public_goal_xy_m=[1.7,0.],push_distance_m=.6,mode='uncompensated',
    original_pre_task_Z_adjustment_XY_restore_base_velocity_zero_explicit=True,
    original_controller_reset_applied_zero_history_none_before_first_Actor=True,
    forbidden_after_a_predecessor_or_any_Actor=True,extra_settle_until_success=False,
    registered12N_FF_FIFO_clocked_native_and_full_exit_still_required=True,
    execution_enabled=False,not_authority=True)
_STEP = '_data_L0_original_physics_request'
_NOTE = '_data_L0_original_initialization_note'
TOKEN = object()


def need(ok, message):
    if not ok:raise ValueError(message)


def _source(path, pin):
    path=Path(path);raw=path.read_bytes()
    need(not path.is_symlink() and hashlib.sha256(raw).hexdigest()==pin,'Exact original source bytes')
    return path,raw.decode()


def _identity(code):
    return (code.co_code,tuple(_identity(c)if isinstance(c,types.CodeType)else c for c in code.co_consts),
            code.co_names,code.co_varnames,code.co_freevars,code.co_cellvars,
            code.co_argcount,code.co_kwonlyargcount,code.co_posonlyargcount,code.co_flags)


def _original_function(original,path,text,name,class_name=None):
    need(type(original)is types.FunctionType and not original.__closure__,'Original simple source function')
    module=compile(text,str(path),'exec',dont_inherit=True)
    if class_name:
        module=next(c for c in module.co_consts if isinstance(c,types.CodeType)and c.co_name==class_name)
    expected=next(c for c in module.co_consts if isinstance(c,types.CodeType)and c.co_name==name)
    need(_identity(original.__code__)==_identity(expected),'No changed original control bytecode')
    tree=ast.parse(text)
    body=tree.body if class_name is None else next(n for n in tree.body if isinstance(n,ast.ClassDef)and n.name==class_name).body
    return next(n for n in body if isinstance(n,ast.FunctionDef)and n.name==name)


def derive_fresh_L0_runtime_source(raw=None,*,enabled=False):
    """One constructor-only INITIAL literal, before any task step; no live write.

    RuntimeAdapter's original camera/calibration three-hunk preparation can then
    apply to this private source. Published SDK file remains byte-exact. The
    generated Runtime variant is explicitly NOT unmodified executed source.
    """
    need(type(enabled)is bool,'Explicit L0 constructor source opt-in')
    if not enabled:return None
    need(type(raw)is bytes and hashlib.sha256(raw).hexdigest()==RUNTIME_SHA,'Original Runtime source')
    old="sim.data.qpos[:3] = [-1., box_y if scenario in ('nav-push','nav-push-climb','box-stairs') else 0., .33]"
    new="sim.data.qpos[:3] = [-.08, box_y if scenario in ('nav-push','nav-push-climb','box-stairs') else 0., .33]"
    text=raw.decode();need(text.count(old)==1,'One exact original initialization site')
    changed=text.replace(old,new,1);need(changed.replace(new,old,1)==text,'Only declared INITIAL root X')
    ast.parse(changed)
    return changed,dict(original_SHA256=RUNTIME_SHA,private_variant_SHA256=hashlib.sha256(changed.encode()).hexdigest(),
        inverse_restores_original=True,constructor_only_hunks=1,initial_xyz_m=[-.08,0.,.33],
        task_resume_or_teleport_from_predecessor=False,Actor_or_safety_algorithm_changed=False,
        source_only_not_a_world_or_execution_permission=True)


def _compile_settle(original,path,note):
    path,text=_source(path,PLAY_SHA);fn=_original_function(original,path,text,'settle')
    notes={
      'sim.data.qpos[2]':'ORIGINAL_INITIAL_FOOT_Z_ADJUSTMENT',
      'sim.data.qpos[:2]':'ORIGINAL_PRE_TASK_XY_RESTORE',
      'sim.data.qvel[:6]':'ORIGINAL_PRE_TASK_BASE_VELOCITY_ZERO',
      'sim.applied_commands[:]':'ORIGINAL_PRE_ACTOR_APPLIED_COMMANDS_ZERO',
      'sim.history':'ORIGINAL_PRE_ACTOR_HISTORY_NONE'}
    expected=['ORIGINAL_INITIAL_FOOT_Z_ADJUSTMENT','ORIGINAL_PRE_TASK_XY_RESTORE',
              'ORIGINAL_PRE_TASK_BASE_VELOCITY_ZERO','ORIGINAL_PRE_ACTOR_CONTROLLER_RESET',
              'ORIGINAL_PRE_ACTOR_APPLIED_COMMANDS_ZERO','ORIGINAL_PRE_ACTOR_HISTORY_NONE']
    found=[]
    class Prepare(ast.NodeTransformer):
        def visit_Expr(self,node):
            if isinstance(node.value,ast.Call)and ast.unparse(node.value.func)=='sim.physics_step':
                need(not node.value.args and not node.value.keywords,'Only original default PD calls')
                return ast.copy_location(ast.Expr(ast.Yield(ast.Name(_STEP,ast.Load()))),node)
            node=self.generic_visit(node)
            if isinstance(node.value,ast.Call)and ast.unparse(node.value.func)=='sim.controller.reset':
                found.append(expected[3]);return [node,ast.copy_location(ast.Expr(ast.Call(ast.Name(_NOTE,ast.Load()),[ast.Constant(expected[3])],[])),node)]
            return node
        def _assignment(self,node):
            target=ast.unparse(node.target if isinstance(node,ast.AugAssign)else node.targets[0])
            if target in notes:
                found.append(notes[target]);return [node,ast.copy_location(ast.Expr(ast.Call(ast.Name(_NOTE,ast.Load()),[ast.Constant(notes[target])],[])),node)]
            return node
        def visit_Assign(self,node):return self._assignment(node)
        def visit_AugAssign(self,node):return self._assignment(node)
    patched=ast.fix_missing_locations(Prepare().visit(copy.deepcopy(fn)))
    need(found==expected,'Exact six original init-write/reset locations')
    need(sum(isinstance(n,ast.Yield)for n in ast.walk(patched))==2,'Exactly two original physical call sites')
    class Inverse(ast.NodeTransformer):
        def visit_Expr(self,node):
            if isinstance(node.value,ast.Call)and isinstance(node.value.func,ast.Name)and node.value.func.id==_NOTE:return None
            if isinstance(node.value,ast.Yield):
                return ast.copy_location(ast.Expr(ast.Call(ast.Attribute(ast.Name('sim',ast.Load()),'physics_step',ast.Load()),[],[])),node)
            return self.generic_visit(node)
    inverse=Inverse().visit(copy.deepcopy(patched))
    need(ast.dump(inverse,include_attributes=False)==ast.dump(fn,include_attributes=False),'Inverse must recover every original startup/control statement')
    private=dict(original.__globals__);need(_NOTE not in private and _STEP not in private,'No layered startup hook')
    private.update({_NOTE:note,_STEP:TOKEN})
    exec(compile(ast.fix_missing_locations(ast.Module(body=[patched],type_ignores=[])),str(path)+'[L0-per-physics-request-only]','exec',dont_inherit=True),private)
    return private['settle']


def _compile_default_PD(original,path):
    path,text=_source(path,BRIDGE_SHA);fn=_original_function(original,path,text,'physics_step','PushBridge')
    expr=fn.body[0].value
    need(isinstance(expr,ast.Call)and isinstance(expr.func,ast.Attribute)and expr.func.attr=='array'and
         isinstance(expr.func.value,ast.BoolOp)and isinstance(expr.func.value.op,ast.Or),'Original optional/default MotorCommand site')
    original_call=expr.func.value.values[1]
    need(isinstance(original_call,ast.Call)and ast.unparse(original_call.func)=='MotorCommand','Original PD command class')
    class Rename(ast.NodeTransformer):
        def visit_Name(self,n):return ast.copy_location(ast.Name('sim',n.ctx),n)if n.id=='self'else n
    call=Rename().visit(copy.deepcopy(original_call))
    # No hand-built gains/defaults: compile the exact ORIGINAL constructor AST.
    node=ast.FunctionDef(name='_data_original_default_PD',args=ast.arguments(posonlyargs=[],args=[ast.arg(arg='sim')],kwonlyargs=[],kw_defaults=[],defaults=[]),
        body=[ast.Return(call)],decorator_list=[])
    namespace=dict(original.__globals__)
    exec(compile(ast.fix_missing_locations(ast.Module(body=[node],type_ignores=[])),str(path)+'[exact-default-PD-expression]','exec',dont_inherit=True),namespace)
    return namespace['_data_original_default_PD'],namespace['MotorCommand']


class _OriginalSettleStepper:
    """No internal physical step. Caller must actually issue+ack each request once."""
    def __init__(self,runtime,guard,actor_call_count,settle,play_path,physics_step,bridge_path):
        need(callable(guard) and callable(actor_call_count),'Parent genuine guard and actual Actor-call counter reader')
        self.r=runtime;self.guard=guard;self.actor_call_count=actor_call_count;self.sim=runtime.sim
        need(runtime.step_count==0 and float(self.sim.data.time)==0. and not self.sim.queue,'ONLY fresh L0 task0; never after NAV/Actor/old zero')
        need(tuple(float(x)for x in self.sim.data.qpos[:3])==(-.08,0.,.33),'Original independent PUSH INITIAL pose, not L1 with NAV omitted')
        need(abs(float(self.sim.model.opt.timestep)-.005)<1e-12 and settle.__globals__['PHYSICS_DT']==.005,'Original physics dt before any issue')
        count=actor_call_count();need(type(count)is int and count==0,'Original L0 initialization only BEFORE any Actor invocation')
        self.world=(self.sim.model,self.sim.data,self.sim.queue)
        self.pending=False;self.failed=False;self.finished=False;self.original_result=None
        self.notes=[];self.issued=0;self.last_two=[];self.before=None;self.expected=None
        self.default_command,command_type=_compile_default_PD(physics_step,bridge_path)
        need(runtime.Command is command_type,'Same original command class; no value-only replacement')
        self.generator=_compile_settle(settle,play_path,self._note)(self.sim)

    def _guard(self):
        need(not self.failed,'Failed startup never resumes')
        need(all(a is b for a,b in zip(self.world,(self.sim.model,self.sim.data,self.sim.queue))),'Original world/data/FIFO aliases')
        answer=self.guard();need(answer is None or answer is True,'Original parent guard refusal')
        count=self.actor_call_count();need(type(count)is int and count==0,'No Actor calls may be hidden inside initialization')

    def _note(self,label):
        need(len(self.notes)<6,'Exactly bounded ORIGINAL init-write/reset metadata')
        self.notes.append(dict(label=label,task_step=self.r.step_count,task_sim_s=float(self.sim.data.time),
                               L0_initialization_not_continuous_L1=True,model_input=False))

    def next_command(self):
        try:
            need(not self.pending and not self.finished,'No unissued request skip/duplicate or finished startup restart')
            self._guard();before=(self.r.step_count,float(self.sim.data.time))
            try:request=next(self.generator)
            except StopIteration as done:
                need((self.r.step_count,float(self.sim.data.time))==before,'Finishing source cannot step physics')
                self.original_result=done.value;self.finished=True;return None
            need(request is TOKEN and (self.r.step_count,float(self.sim.data.time))==before,'Source emits a request, never a hidden physical step')
            command=self.default_command(self.sim);array=command.array()
            need(type(command)is self.r.Command and array.shape==(5,18),'Exact original default PD')
            self.before=before;self.expected=(array.shape,str(array.dtype),array.tobytes());self.pending=True
            return command
        except BaseException:
            self.failed=True;raise

    def after_actual_issue(self,*,native_error=None):
        try:
            if native_error is not None:raise native_error
            self._guard();need(self.pending,'No invented actual command')
            need(self.r.step_count==self.before[0]+1 and abs(float(self.sim.data.time)-self.before[1]-.005)<1e-7,'Exactly ONE original actual .005s Runtime step required')
            a=self.r.last.array();need((a.shape,str(a.dtype),a.tobytes())==self.expected,'Actual original command must match request')
            self.last_two.append(self.r.last.position.copy());self.last_two=self.last_two[-2:]
            self.issued+=1;self.pending=False
        except BaseException:
            self.failed=True;raise

    def snapshot(self):
        # ACK count is not a fee substitute if Runtime.step raised after advancing.
        clock=count=None
        try:
            clock=float(self.sim.data.time);count=self.r.step_count
        except (AttributeError,TypeError,ValueError):pass
        return dict(verified_actual_issue_acknowledgements=self.issued,observed_runtime_counter=count,observed_task_clock=clock,not_a_replacement_for_parent_partial_finally_cost=True,pending=self.pending,failed=self.failed,
            initialization_finished_not_PUSH_success=self.finished,original_startup_result=self.original_result,
            original_initialization_writes_and_resets=list(self.notes),
            no_added_state_reset_or_queue_clear=True,
            original_stable_gate_is_3N_NOT_registered12N_admission=True,
            actual_registered_entry_and_full_PUSH_exit_still_unqualified=True)


def prepare_startup(runtime=None,*,guard=None,actor_call_count=None,original_settle=None,play_path=None,
                    original_physics_step=None,bridge_path=None,enabled=False):
    need(type(enabled)is bool,'Explicit future complete-program L0 opt-in')
    if not enabled:return None
    return _OriginalSettleStepper(runtime,guard,actor_call_count,original_settle,play_path,original_physics_step,bridge_path)
