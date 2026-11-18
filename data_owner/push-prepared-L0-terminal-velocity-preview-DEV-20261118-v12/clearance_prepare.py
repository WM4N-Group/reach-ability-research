"""Original clearance/einsum on synthetic CPU tensors under the actual audit hook."""
from pathlib import Path
from hashlib import sha256
import importlib.util
import sys

OPT='torch.backends.opt_einsum'
OPT_SHA='969d5271687e5540861b9e3605eb8fccc0a00eca48570625e12fdd5e40cdd05d'
MATH_SHA='817fe86a272706519ba5f1da84242b3a744da2514fe979b0a6ee7812d33fb54b'

def verify_clearance_preload(freeze):
    opt=sys.modules[OPT];p=Path(opt.__file__)
    assert not p.is_symlink() and freeze['files'].get(str(p))==sha256(p.read_bytes()).hexdigest()==OPT_SHA
    # Confirm only the actual frozen environment's supported/default mode; no
    # installation or toggling of the math implementation or global flags.
    assert opt.is_available() is False and opt.enabled is False
    return OPT_SHA

def qualify_clearance(config,freeze):
    import indexed_guard as guard
    import torch
    assert not torch.cuda.is_initialized()
    verify_clearance_preload(freeze)
    p=Path(config['SDK'])/'push/controller/box_push_control.py'
    assert not p.is_symlink() and freeze['files'][str(p)]==sha256(p.read_bytes()).hexdigest()==MATH_SHA
    spec=importlib.util.spec_from_file_location('_data_cpu_frozen_push_clearance_only',p)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    x=torch.zeros((1,6),dtype=torch.float32);gradient=torch.zeros((1,2,6),dtype=torch.float32);gradient[0,0,0]=1;gradient[0,1,1]=1
    d=torch.tensor([[.01,.06]],dtype=torch.float32);lo=torch.full_like(x,-.1);hi=torch.full_like(x,.1)
    names=frozenset(sys.modules)
    class FixtureEngine:pass
    e=FixtureEngine();e.state='RUNNING';e.failure=None;guard._install_hook(e)
    try:
        target,residual=mod.project_clearance_target(x,x,gradient,d,lo,hi,minimum=.05)
        assert e.state=='RUNNING' and e.failure is None and frozenset(sys.modules)==names
    finally:e.state='CLOSED'
    assert target.shape==(1,6) and abs(target[0,0].item()-.04)<1.e-6 and residual.shape==(1,) and residual.abs().max().item()<1.e-6
    assert not torch.cuda.is_initialized()
    return dict(CPU_fixture_only=True,original_einsum_clearance_passed_running_import_audit=True,
        no_new_modules_at_exact_math_callsite=True,only_torch_backend_preloaded_no_optional_package_installed=True,
        original_clearance_source_sha256=MATH_SHA,torch_backend_source_sha256=OPT_SHA,
        unchanged_optional_backend_unavailable_disabled=True,no_physics_or_resource_qualification=True)
