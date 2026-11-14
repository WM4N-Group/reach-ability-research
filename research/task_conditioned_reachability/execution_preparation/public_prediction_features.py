"""Physical-only input view for a FUTURE qualified successor predictor.

No model/training/dataset reads, Data contract or execution. Candidate/reference
and source hashes still bind the surrounding Problem, but are NOT feature values.
This prevents accidental metadata shortcuts; it is NOT a sandbox for hostile
Python evaluators or permission to relabel historical observations as online.
"""
from dataclasses import dataclass
from .successor_aware_choice import need,number
from .public_preparation_selector import Problem


@dataclass(frozen=True)
class PhysicalFeatures:
    names: tuple
    values: tuple
    known_mask: tuple
    units: tuple
    frames: tuple
    unavailable_capabilities: tuple = (
        'registered_reference_relative_pose', 'world_to_body_heading',
        'native_position_yaw_latch_history', 'qualified_skill_elapsed_clock', 'complete_successor_predictor',
    )
    def __post_init__(self):
        columns=(self.names,self.values,self.known_mask,self.units,self.frames)
        need(all(type(c) is tuple for c in columns) and len({len(c) for c in columns})==1,
             'Fixed physical feature columns, not a metadata dictionary')
        need(len(set(self.names))==len(self.names),'Unique semantic feature names')
        need(all(type(m) is bool and (number(v) if m else v is None)
                 for v,m in zip(self.values,self.known_mask)),
             'Unknown physical values remain None with a false mask, never zero imputation')


def physical_features(problem, candidate):
    """Project existing legal Problem to candidate-action + measured-proprio view.

    48 fixed slots: 2 actual nominal world-reference offsets, 45 permitted
    proprio channels, 1 acquisition AGE. No absolute simulation time, UUID,
    source path/SHA, candidate label, task status text or retrospective outcome.
    Body-frame measurements and world-frame offsets stay explicitly separate;
    lacking public heading does not authorize rotating one into the other.
    """
    need(type(problem) is Problem,'Existing public selector problem')
    need(any(candidate is c for c in problem.domain.candidates),'Exact candidate from this problem, not foreign action/metadata')
    problem.information_schema.validate(problem.inputs)
    need(problem.inputs.audience=='HIGH_LEVEL_PLANNER','Existing legal public audience only')
    fields={v.name:v for v in problem.inputs.values}
    need(all(v.visibility in ('ONLINE_PUBLIC','UNKNOWN') for v in fields.values()),
         'No private/local/audit channels in model feature view')
    rows=[g for g in problem.geometry if g['candidate_id']==candidate.candidate_id]
    need(len(rows)==1,'One existing source-generated geometry row')
    row=rows[0];goal=row['NAV_goal_xy'];center=row['original_CLIMB_reference_xy']
    registered=fields.get('registered_CLIMB.approach_xy')
    need(registered is not None and registered.visibility=='ONLINE_PUBLIC' and
         registered.value==list(center),'Geometry reference must match the same registered public input')
    need(len(goal)==len(center)==2 and all(number(v) for v in list(goal)+list(center)),
         'Finite original public reference geometry')
    names=['candidate_reference_offset_x','candidate_reference_offset_y']
    values=[goal[0]-center[0],goal[1]-center[1]]
    units=['m','m'];frames=['WORLD_REGISTERED_REFERENCE','WORLD_REGISTERED_REFERENCE']
    layout=(('q',18,'rad','JOINT_ORDER_AS_ORIGINAL_PUBLIC_PACKET'),
            ('dq',18,'rad/s','JOINT_ORDER_AS_ORIGINAL_PUBLIC_PACKET'),
            ('gravity',3,'1','BODY_PROJECTED_GRAVITY'),
            ('angular_velocity',3,'rad/s','BODY'),
            ('linear_velocity',3,'m/s','BODY'))
    present=[fields.get('public_state.'+name) for name,_,_,_ in layout]
    any_present=any(v is not None for v in present)
    if any_present:
        need(all(v is not None and v.visibility=='ONLINE_PUBLIC' for v in present),
             'Complete actual public 45D packet required, not partial or imputed proprio')
        clocks={v.observed_time_s for v in present}
        need(len(clocks)==1,'One actual acquisition clock for the public packet')
        acquired=next(iter(clocks));age=problem.inputs.decision_time_s-acquired
        need(0<=age<=.100001,'Fresh causal public packet, not an audit/future/stale feature row')
    else:age=None
    for (name,size,unit,frame),value in zip(layout,present):
        vector=None if value is None else value.value
        if vector is not None:
            need(type(vector) is list and len(vector)==size and all(number(v) for v in vector),
                 'Original finite public vector: '+name)
        for i in range(size):
            names.append('public_'+name+'_'+str(i));values.append(None if vector is None else vector[i])
            units.append(unit);frames.append(frame)
    names.append('measurement_age');values.append(age);units.append('s');frames.append('ACQUISITION_AGE_NOT_SKILL_ELAPSED')
    need(all(v is None or number(v) for v in values),'Finite physical values only')
    return PhysicalFeatures(tuple(names),tuple(values),tuple(v is not None for v in values),tuple(units),tuple(frames))
