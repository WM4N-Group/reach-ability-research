"""AST-limited host launcher: only CUDA/EGL deployment coordinates may change.

The archived runner, SDK/controllers/actors, task scene and original protocol
remain byte-identical. No route, motor reference, safety or success mutation.
"""
import ast
import hashlib

ALLOWED_RUNNERS=frozenset(('run_full_course.py','run_nav_pilot.py','zero_step_native.py','zero_step_registered_scene.py','run_supported_capture.py','run_model_layout_nav.py'))


def compile_runner(raw,*,filename,host):
    if filename.rsplit('/',1)[-1] not in ALLOWED_RUNNERS:raise ValueError('Only explicitly reviewed native runners may use this deployment wrapper')
    tree=ast.parse(raw,filename=filename);counts=dict(egl=0,runtime=0,cold_runtime=0)
    class DeploymentOnly(ast.NodeTransformer):
        def visit_Call(self,node):
            self.generic_visit(node)
            if isinstance(node.func,ast.Name) and node.func.id=='construct_runtime':
                if len(node.args)!=2 or node.keywords:raise ValueError('Original Runtime construction signature changed')
                node.args[1]=ast.Call(func=ast.Attribute(value=ast.Name(id='_AINAV_HOST',ctx=ast.Load()),attr='runtime_config',ctx=ast.Load()),args=[node.args[1]],keywords=[])
                counts['runtime']+=1
            elif isinstance(node.func,ast.Name) and node.func.id=='construct_cold_runtime':
                if any(k.arg=='actor_device' for k in node.keywords):raise ValueError('Do not override an already explicit constructor device')
                node.keywords.append(ast.keyword(arg='actor_device',value=ast.Attribute(value=ast.Name(id='_AINAV_HOST',ctx=ast.Load()),attr='actor_device',ctx=ast.Load())))
                counts['cold_runtime']+=1
            for k in node.keywords:
                if k.arg=='MUJOCO_EGL_DEVICE_ID':
                    if not isinstance(k.value,ast.Constant) or k.value.value!='1':raise ValueError('Expected original A800 EGL literal1')
                    k.value=ast.Constant(value=str(host.egl_device_id));counts['egl']+=1
            return node
    updated=DeploymentOnly().visit(tree);ast.fix_missing_locations(updated)
    if counts['egl']!=1 or counts['runtime']+counts['cold_runtime']!=1:raise ValueError('Exactly one native construction and EGL binding expected; fail on source drift')
    receipt=dict(original_runner_sha256=hashlib.sha256(raw.encode()).hexdigest(),adapted_AST_sha256=hashlib.sha256(ast.dump(updated,include_attributes=False).encode()).hexdigest(),
        hooks=counts,actor_device=host.actor_device,egl_device_id=host.egl_device_id,
        allowed_changes=['constructor actor_device','EGL device number'],controller_actor_scene_success_or_safety_modified=False,
        archived_runner_or_native_source_overwritten=False,hardware_fallback=False)
    return compile(updated,filename+'[declared-host-device-only]','exec'),receipt
