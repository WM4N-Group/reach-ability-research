"""Pre-env-only contact sensor matrix for future explicit target-B PUSH.

Does NOT retarget controllers, mutate live scene aliases, move an object or
approve a PUSH handoff. Original A sensors remain unchanged. Each candidate gets
its own copies of every existing box_contact_* sensor (hand AND non-hand bodies),
so a future selected-target context cannot accidentally read A's hand contact
while pushing B. Actual SDK/physics integration remains a separate gate.
"""
from copy import deepcopy


def require(condition,message):
    if not condition:raise ValueError(message)


def compile_candidate_contacts(cfg,object_to_scene_key,*,environment_constructed=False):
    require(environment_constructed is False,'Compile contact matrix before environment construction only')
    require(isinstance(object_to_scene_key,dict) and len(object_to_scene_key)>=2
        and len(set(object_to_scene_key.values()))==len(object_to_scene_key),'Explicit unique candidate scene mapping required')
    require(sum(key=='box' for key in object_to_scene_key.values())==1,'Exactly one original A box role required')
    templates={name:value for name,value in vars(cfg.scene).items() if name.startswith('box_contact_') and value is not None}
    require('box_contact_hand' in templates and len(templates)>1,'Original hand AND non-hand sensor family required')
    for name,sensor in templates.items():
        require(sensor.filter_prim_paths_expr==[cfg.scene.box.prim_path],f'Exact original single-box contact filter required: {name}')
    pending=[];mapping={}
    for object_id,key in object_to_scene_key.items():
        require(isinstance(object_id,str) and object_id.isidentifier() and isinstance(key,str) and key.isidentifier(),'Explicit safe candidate names required')
        asset=getattr(cfg.scene,key,None)
        require(asset is not None and getattr(asset,'prim_path',None),'Candidate rigid-body cfg missing')
        mapping[object_id]={}
        for name,sensor in templates.items():
            new_name=name if key=='box' else 'wm_contact_'+object_id+'_'+name[len('box_contact_'):]
            if key!='box':
                require(not hasattr(cfg.scene,new_name),'Never overwrite a sensor cfg: '+new_name)
                new=deepcopy(sensor);new.filter_prim_paths_expr=[asset.prim_path]
                pending.append((new_name,new))
            mapping[object_id][name]=new_name
    # Validate all candidates before writing even software configuration.
    for name,value in pending:setattr(cfg.scene,name,value)
    return dict(schema='native-candidate-contact-matrix-v1',model_input_allowed=False,
        scene_keys=dict(object_to_scene_key),source_sensor_names=sorted(templates),per_candidate_sensor_names=mapping,
        added_sensors=len(pending),original_sensor_objects_unchanged=True,
        original_filter_paths_and_update_periods_preserved=True,environment_constructed=False,
        controller_retargeted=False,actual_SDK_or_contact_validated=False)


def selected_contact_keys(receipt,*,candidate,observed_scene_keys):
    """Metadata lookup only; not a live scene adapter or handoff certificate."""
    require(receipt['schema']=='native-candidate-contact-matrix-v1' and candidate in receipt['per_candidate_sensor_names'],
        'Registered candidate required')
    sensors=receipt['per_candidate_sensor_names'][candidate]
    required=set(sensors.values())|{receipt['scene_keys'][candidate]}
    require(required<=set(observed_scene_keys),'Selected candidate body/contact sensors missing from actual scene')
    return dict(sensors)
