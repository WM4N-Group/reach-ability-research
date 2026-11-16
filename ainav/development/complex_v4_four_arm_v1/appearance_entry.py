"""Default-off NEW shared visible-asset revision, not an old-run patch/authority.

Existing review hex colors become a NEW native appearance choice, not a claim
that review colors were already approved physical rendering. All five arms must
freeze the same new asset if adopted. Exact original detector/ambiguity, geometry,
material, camera, native controllers and success gates remain unchanged.
Only Data can invoke the real fresh guarded compiler; no renderer/world/Actor
is constructed by imports or software fixtures. A different-hue palette is NOT
proof of actual rendered separation, native admission or general tracking.
"""
from pathlib import Path
import colorsys,hashlib,json,math,types
from v4_native_asset import require,load_scene,SCENE_SHA256

CONTRACT_SHA='75842a43ee8313edf95e8d92bbc6dc5b22d5f18474c316fa7c5f92a67e895457'
REFERENCE_SHA='0b3547b0f85005afa01b958b13d20d448a67e5cf3206f545f71b8174745f768e'
COUNTS=('nq','nv','nu','nbody','ngeom','npair','ncam','nsensor','nplugin','nkey')


def contract():
    p=Path(__file__).with_name('COMMON_APPEARANCE_REVISION.json');raw=p.read_bytes()
    require(hashlib.sha256(raw).hexdigest()==CONTRACT_SHA,'Exact proposed common appearance revision')
    c=json.loads(raw);scene=load_scene()
    require(c['schema']=='AINav-V4-common-visible-appearance-revision-v1'
            and c['scene_sha256']==SCENE_SHA256 and c['reference_static_MJB_sha256']==REFERENCE_SHA
            and c['shared_arms']==list('ABCDE'),'One explicit new appearance shared by ALL five arms')
    expected={o['body_name']+'_geom':o['review_color']for o in scene['objects']}
    require(c['body_geom_review_hex']==expected,'Only existing review palette, no new hidden marker/route design')
    return c


def palette(c):
    output={}
    for name,value in c['body_geom_review_hex'].items():
        require(type(value)is str and len(value)==7 and value[0]=='#'
                and all(x in '0123456789abcdef'for x in value[1:]),'Exact declared RGB hex')
        output[name]=tuple(int(value[i:i+2],16)/255. for i in (1,3,5))+(1.,)
    return output


def declared_hue_families(c):
    # Exact existing visual_box_proposals family boundaries; no detector rewrite.
    families=(('warm',.035,.16),('green',.28,.50),('violet',.70,.90),('red',.95,.035))
    result={}
    for name,rgba in palette(c).items():
        h,s,v=colorsys.rgb_to_hsv(*rgba[:3])
        matches=[family for family,lo,hi in families if (lo<=h<hi if lo<hi else h>=lo or h<hi)]
        require(len(matches)==1 and s>=.18 and v>=.08,'Declared colors within original proposal ranges')
        result[name]=matches[0]
    require(len(set(result.values()))==len(result),'Different declared families, not a rendered qualification')
    return result


def apply_fresh_spec_palette(sim,*,enabled=False,scene=None,main_steps=0,guard=None):
    require(type(enabled)is bool,'Explicit owner opt-in')
    if not enabled:return None
    require(callable(guard)and guard()is not False,'Actual Data fresh-asset owner guard')
    scene=load_scene()if scene is None else scene
    require(scene==load_scene()and type(main_steps)is int and main_steps==0
            and getattr(sim,'step_count',0)==0 and float(sim.data.time)==0. and not sim.queue,
            'Exact scene on a fresh ZERO-step spec, not a live/resumed model')
    c=contract();wanted=palette(c);geoms=list(sim.spec.geoms)
    # MuJoCo permits multiple unnamed robot/visual geoms. Require uniqueness
    # ONLY for our three named targets; preserve all other geoms by index, not
    # a name-keyed dict that would collapse legitimate empty names.
    indices={name:[i for i,g in enumerate(geoms)if g.name==name]for name in wanted}
    require(all(len(found)==1 for found in indices.values()),
            'Each of the three declared target geoms must be present exactly once')
    selected={name:geoms[found[0]]for name,found in indices.items()}
    before=[tuple(float(v)for v in g.rgba)for g in geoms]
    for name in wanted:
        original_rgba=before[indices[name][0]]
        require(len(original_rgba)==4 and all(abs(a-b)<=1e-7 for a,b in zip(original_rgba,c['old_all_box_rgba'])),
                'Only exact old shared brown appearance, never overwrite a previous revision')
    # Validate every target before ANY write. Only the fresh spec's three rgba
    # fields are written; old MJB bytes and every other spec field stay untouched.
    require(guard()is not False,'Owner refused fresh appearance revision')
    for name,rgba in wanted.items():selected[name].rgba=rgba
    target_indices={found[0]for found in indices.values()}
    require(all(tuple(float(v)for v in g.rgba)==before[i]for i,g in enumerate(geoms)if i not in target_indices),
            'No other geometry appearance may change')
    return dict(revision_id=c['revision_id'],contract_sha256=CONTRACT_SHA,
        old_all_box_rgba=c['old_all_box_rgba'],new_box_rgba=wanted,
        declared_hue_families_not_rendered_proof=declared_hue_families(c),
        only_fresh_spec_RGBA_written=True,compiled_mechanics_or_render_or_native_qualified=False,
        all_five_same_new_asset_required=True)


def _array_hash(value):
    return hashlib.sha256(str((tuple(value.shape),str(value.dtype))).encode()+value.tobytes()).hexdigest()


def _arrays(model):
    result={}
    for name in dir(model):
        if name.startswith('_'):continue
        value=getattr(model,name)
        if hasattr(value,'shape')and hasattr(value,'dtype')and callable(getattr(value,'tobytes',None)):
            result[name]=_array_hash(value)
    return result


def _options(option):
    result={}
    for name in dir(option):
        if name.startswith('_'):continue
        value=getattr(option,name)
        if hasattr(value,'shape')and hasattr(value,'dtype')and callable(getattr(value,'tobytes',None)):
            result[name]=dict(array_sha256=_array_hash(value))
        elif isinstance(value,(int,float,bool)):
            require(not isinstance(value,float)or math.isfinite(value),'Finite unchanged engine options')
            result[name]=value
        elif callable(value):
            continue
        else:
            # Do not silently omit a public engine field (including a pybind
            # enum) and then claim complete option equality.
            require(type(getattr(value,'name',None))is str
                    and callable(getattr(value,'__int__',None)),
                    'Unclassified compiled engine option field: '+name)
            result[name]=dict(enum_type=type(value).__module__+'.'+type(value).__qualname__,
                              enum_name=value.name,enum_value=int(value))
    return result


def verify_compiled_render_only_delta(reference,candidate):
    """Static MODEL metadata only, no MjData/runtime/renderer or physics call.

    Compare every array-exposing compiled field except the exact three rgba
    rows. A shape/dtype/name/options/contact/dynamics change is NOT tolerated.
    This certifies a render-only compiled delta, not actual camera colors.
    """
    c=contract();wanted=palette(c)
    require(all(getattr(reference,k)==getattr(candidate,k)for k in COUNTS),'No topology/count change')
    before,after=_arrays(reference),_arrays(candidate)
    require(before.keys()==after.keys()and 'geom_rgba'in before,'Complete same compiled array domain')
    require(all(before[n]==after[n]for n in before if n!='geom_rgba'),
            'ALL compiled non-RGBA arrays must remain BYTE-identical, no mechanics/calibration exception')
    require(_options(reference.opt)==_options(candidate.opt),'Exact original engine options')
    for name in ('names','paths'):
        require(getattr(reference,name,None)==getattr(candidate,name,None),'No compiled names/assets/path change')
    require(tuple(reference.geom_rgba.shape)==(reference.ngeom,4)
            and tuple(candidate.geom_rgba.shape)==(candidate.ngeom,4)
            and str(reference.geom_rgba.dtype)==str(candidate.geom_rgba.dtype),
            'Exact compiled RGBA shape and dtype')
    ids={}
    for name,rgba in wanted.items():
        oldid=int(reference.geom(name).id);newid=int(candidate.geom(name).id)
        require(oldid==newid,'No geometry ID remapping')
        oldrow=reference.geom_rgba[oldid];newrow=candidate.geom_rgba[newid]
        require(all(abs(float(a)-b)<=1e-7 for a,b in zip(oldrow,c['old_all_box_rgba'])),
                'Reference must be actual original brown static asset')
        require(all(abs(float(a)-b)<=1e-7 for a,b in zip(newrow,rgba)),'Compiled exact proposed RGBA')
        ids[name]=oldid
    require(len(set(ids.values()))==3,'Three distinct box rows')
    for index in range(reference.ngeom):
        if index not in ids.values():
            require(reference.geom_rgba[index].tobytes()==candidate.geom_rgba[index].tobytes(),
                    'No fourth/background/camera/robot appearance change')
    common={k:v for k,v in before.items()if k!='geom_rgba'}
    return dict(only_changed_array='geom_rgba',only_changed_rows=ids,
        unchanged_nonRGBA_array_count=len(common),unchanged_nonRGBA_arrays_sha256=common,
        engine_options_unchanged=True,topology_names_paths_unchanged=True,
        actual_render_or_current_association_or_native_admission=False)


def _bound_palette_compiler(guard):
    import native_entry
    original=native_entry._bound_original('compile_static_asset')
    namespace=dict(original.__globals__);construct=namespace['construct_into_native_spec']
    require(construct is native_entry._v4_construct,'Exact original private V4 constructor binding')
    def fresh_palette_construct(sim,**kwargs):
        result=construct(sim,**kwargs)
        revision=apply_fresh_spec_palette(sim,enabled=True,scene=kwargs['scene'],main_steps=kwargs['main_steps'],guard=guard)
        return dict(result,common_appearance_revision=revision)
    namespace['construct_into_native_spec']=fresh_palette_construct
    bound=types.FunctionType(original.__code__,namespace,original.__name__,original.__defaults__,original.__closure__)
    bound.__kwdefaults__=dict(original.__kwdefaults__ or {})
    return bound,original


def compile_new_shared_palette_asset(*,enabled=False,reference_model_path=None,guard=None,**owner_kwargs):
    require(type(enabled)is bool,'Explicit Data new-program opt-in')
    if not enabled:return None
    require(callable(guard)and guard()is not False,'Actual Data new asset guard, not a lease from this source')
    p=Path(reference_model_path)
    require(not p.is_symlink()and hashlib.sha256(p.read_bytes()).hexdigest()==REFERENCE_SHA,
            'Read-only exact old static MJB reference; never prior Runtime/state/zero')
    def checked_guard():
        require(guard()is not False,'Actual Data owner guard refused new shared asset')
    c=contract();bound,_original=_bound_palette_compiler(checked_guard)
    result=bound(enabled=True,guard=checked_guard,**owner_kwargs)
    require(result['scene_sha256']==SCENE_SHA256 and result['actual_main_steps']==0 and result['Actor_forwards']==0,
            'Only original guarded fresh static compiler, not a task/Actor')
    out=Path(result['model_path'])
    require(not out.is_symlink()and hashlib.sha256(out.read_bytes()).hexdigest()==result['model_sha256'],
            'Exact new immutable output model bytes')
    import mujoco  # Only Data's explicitly invoked compiler path; no import in software fixtures.
    before=mujoco.MjModel.from_binary_path(str(p));after=mujoco.MjModel.from_binary_path(str(out))
    proof=verify_compiled_render_only_delta(before,after)
    result['common_appearance_revision']=dict(revision_id=c['revision_id'],contract_sha256=CONTRACT_SHA,
        reference_static_MJB_sha256=REFERENCE_SHA,new_static_MJB_sha256=result['model_sha256'],
        compiled_render_only_delta_proof=proof,all_five_same_new_asset_required=True,
        actual_render_or_current_association_or_task_qualified=False)
    require(guard()is not False,'Owner refused final appearance asset evidence')
    return result
