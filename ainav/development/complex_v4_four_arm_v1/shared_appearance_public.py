"""Default-off SAME public palette/declared-subject prior for ALL five methods.

Bind ONLY an already-loaded new common palette asset at task0. No MJB/model
read/restore, renderer, detector, transport or physics is invoked here. Original
Observation schema stays source_ref+anchors: annotations are ordinary public
static descriptions, never current object identity/pose/visibility or readiness.
This is future method wiring, NOT a dependency/retry of Data's palette component.
"""
from pathlib import Path
import hashlib,json
from appearance_entry import contract,palette,CONTRACT_SHA,REFERENCE_SHA
from public_candidates import declared_map,public_effects
from v4_native_asset import require,load_scene,SCENE_SHA256

MAP_SHA='802d3651187052d46c4006717d21fd27f21a2fde61ecc7e93a857197dd894cb6'
_SEAL=object()

def _sha(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()

def _hex_sha(value):
    return type(value)is str and len(value)==64 and all(c in '0123456789abcdef'for c in value)

def _public_map(scene):
    p=Path(__file__).with_name('SHARED_APPEARANCE_DECLARED_MAP.json');raw=p.read_bytes()
    require(not p.is_symlink()and hashlib.sha256(raw).hexdigest()==MAP_SHA,'Exact common Reach-proposed public prior')
    new=json.loads(raw);base=declared_map(scene)
    require(set(new)=={'source_ref','anchors'}and len(new['anchors'])==len(base['anchors']),
            'Original strict Observation map schema/domain; no extra hidden fields or anchors')
    require(new['source_ref']==base['source_ref']+'; SHARED_PUBLIC_APPEARANCE_PRIOR:'+CONTRACT_SHA,
            'Same prior explicitly public to A/B/C/D/E, not a private A/B table')
    for original,annotated in zip(base['anchors'],new['anchors']):
        require(set(annotated)==set(original)and
                all(annotated[k]==original[k]for k in original if k!='description')and
                annotated['description'].startswith(original['description']),
                'Only append public static descriptions; original geometry/uncertainty/order unchanged')
    return new

def _asset_evidence(asset):
    c=contract();require(type(asset)is dict and asset.get('scene_sha256')==SCENE_SHA256,
                         'Source compiled asset for exact unchanged physical scene')
    digest=asset.get('model_sha256');require(_hex_sha(digest)and digest!=REFERENCE_SHA,'NEW selected MJB, never old brown')
    e=asset.get('common_appearance_revision');require(type(e)is dict and
        e.get('revision_id')==c['revision_id']and e.get('contract_sha256')==CONTRACT_SHA and
        e.get('new_static_MJB_sha256')==digest and e.get('reference_static_MJB_sha256')==REFERENCE_SHA and
        e.get('all_five_same_new_asset_required')is True,'One new common asset/contract evidence identity')
    p=e.get('compiled_render_only_delta_proof',{})
    require(type(p)is dict,'Structured compiled render delta proof')
    hashes=p.get('unchanged_nonRGBA_arrays_sha256',{});rows=p.get('only_changed_rows',{})
    require(type(rows)is dict and type(hashes)is dict,'Structured three-row and nonRGBA hash proof')
    require(p.get('only_changed_array')=='geom_rgba'and set(rows)==set(palette(c))and
            all(type(i)is int and i>=0 for i in rows.values())and len(set(rows.values()))==3 and
            p.get('engine_options_unchanged')is True and p.get('topology_names_paths_unchanged')is True and
            type(p.get('unchanged_nonRGBA_array_count'))is int and p['unchanged_nonRGBA_array_count']>0 and
            type(hashes)is dict and len(hashes)==p['unchanged_nonRGBA_array_count']and all(_hex_sha(x)for x in hashes.values()),
            'Source exact compiled-only-RGBA proof required; this map is not a mechanics qualifier')
    checked=dict(revision_id=e['revision_id'],contract_sha256=e['contract_sha256'],
        new_static_MJB_sha256=e['new_static_MJB_sha256'],reference_static_MJB_sha256=e['reference_static_MJB_sha256'],
        all_five_same_new_asset_required=True,compiled_render_only_delta_proof=dict(
            only_changed_array='geom_rgba',only_changed_rows=dict(rows),engine_options_unchanged=True,
            topology_names_paths_unchanged=True,unchanged_nonRGBA_array_count=p['unchanged_nonRGBA_array_count'],
            unchanged_nonRGBA_arrays_sha256=dict(hashes)))
    return digest,checked  # Only whitelisted static public proof fields, never arbitrary input metadata.

def _loaded(components,digest,e,*,software_fixture,fresh):
    require(components['scene_sha256']==SCENE_SHA256 and components['scene']==load_scene(),
            'Exact shared source scene, not another task/geometry')
    r=components['runtime'];model=r.sim.model;receipt=components['construction']
    require(receipt.get('static_model_sha256')==digest and receipt.get('recorded_dynamic_state_loaded')is False
            and receipt.get('actor_weights_modified')is False and receipt.get('initialization_only')is True,
            'Original loader receipt binds this exact new common static MJB, not replay/old world')
    if fresh:
        require(r.step_count==0 and float(r.sim.data.time)==0. and not r.sim.queue
                and receipt.get('main_motor_steps')==0,'Only fresh pre-method declaration binding, never hot-switch maps')
    if not software_fixture:
        require(type(model).__name__=='MjModel'and type(model).__module__=='mujoco._structs',
                'Actual already-loaded original model, not software metadata upgraded to production')
        import mujoco
        require(type(model)is mujoco.MjModel,'Exact installed static model type; no model construction here')
    for name,rgba in palette(contract()).items():
        gid=int(model.geom(name).id)
        require(gid==e['compiled_render_only_delta_proof']['only_changed_rows'][name]
                and len(model.geom_rgba[gid])==4
                and all(abs(float(a)-b)<=1e-7 for a,b in zip(model.geom_rgba[gid],rgba))
                and int(model.geom_matid[gid])==-1,
                'This actual loaded model must have exact new box RGBA/no material override; not claimed render identity')
    return r,model

class SharedAppearanceDeclaration:
    __slots__=('_map_json','_digest','_evidence_json','_runtime_id','_model_id','software_fixture','_frozen')
    def __init__(self,*,_seal,public_map,digest,evidence,runtime,model,software_fixture):
        require(_seal is _SEAL,'Use guarded source declaration builder, not an arbitrary dict/marker')
        self._map_json=json.dumps(public_map,sort_keys=True,separators=(',',':'),allow_nan=False)
        self._digest=digest;self._evidence_json=json.dumps(evidence,sort_keys=True,separators=(',',':'),allow_nan=False)
        self._runtime_id=id(runtime);self._model_id=id(model);self.software_fixture=software_fixture;self._frozen=True
    def __setattr__(self,key,value):
        require(not getattr(self,'_frozen',False),'Declaration identity is immutable; no method/arm/time switch')
        object.__setattr__(self,key,value)
    def public_map(self):return json.loads(self._map_json)
    def verify_bound_components(self,components):
        r,model=_loaded(components,self._digest,json.loads(self._evidence_json),software_fixture=self.software_fixture,fresh=False)
        require(id(r)==self._runtime_id and id(model)==self._model_id,'No cross-world/episode declaration reuse')
    @property
    def selected_MJB_sha256(self):return self._digest

def require_live_declaration(context):
    require(type(context)is SharedAppearanceDeclaration and context.software_fixture is False,
            'Only a non-fixture source-bound common declaration may enter a live driver')

def build_shared_appearance_declaration(*,enabled=False,components=None,compiled_asset=None,journal=None,
                                      guard=None,software_fixture=False):
    require(type(enabled)is bool and type(software_fixture)is bool,'Explicit default-off/public fixture provenance')
    if not enabled:return None
    require(callable(guard)and callable(journal)and guard()is not False,'Actual owner guard and durable journal')
    digest,e=_asset_evidence(compiled_asset)
    r,model=_loaded(components,digest,e,software_fixture=software_fixture,fresh=True)
    public=_public_map(components['scene'])
    context=SharedAppearanceDeclaration(_seal=_SEAL,public_map=public,digest=digest,evidence=e,
        runtime=r,model=model,software_fixture=software_fixture)
    require(guard()is not False,'Owner refused new common public declaration')
    ref=journal(dict(event='V4_same_five_public_appearance_declaration_bound_NOT_semantic_or_native_ready',
        software_fixture=software_fixture,common_map_file_sha256=MAP_SHA,common_map_value_sha256=_sha(public),
        common_appearance_contract_sha256=CONTRACT_SHA,selected_new_MJB_sha256=digest,
        checked_asset_public_metadata_sha256=_sha(e),public_effects_sha256=_sha(public_effects(components['scene'])),
        all_five_receive_same_static_prior=True,no_extra_anchor_geometry_or_continuous_goal=True,
        current_identity_visibility_pose_native_admission_or_WM_prediction_claimed=False,
        no_frame_model_restore_constructor_API_or_physics_call=True,model_input=False))
    require(type(ref)is str and bool(ref),'Durable source declaration evidence required')
    return context
