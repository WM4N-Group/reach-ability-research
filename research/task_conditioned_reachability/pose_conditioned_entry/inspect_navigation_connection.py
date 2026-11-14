"""Read-only source contract for connecting this LOCAL pilot to full navigation.

No scene/actor/physics imports; do not confuse missing probe-level route IO
with absence of a planner elsewhere in the project. This is not a new trial.
"""
import argparse,ast,hashlib,json
from pathlib import Path


def inspect(source):
    manifest=json.loads((source/'manifest.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    for name,digest in manifest['files'].items():
        if sha(source/name)!=digest:raise ValueError('Changed frozen source '+name)
    file=source/'probe.py';text=file.read_text();tree=ast.parse(text)
    funcs={n.name:n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
    required=["cfg.observations.nav_policy.velocity_commands.func=nav_command",
        "cfg.observations.nav_policy.pos_commands.func=nav_pose",
        "native=nav_actor(obs['nav_policy'])",
        "term.return_nav_goal[:,:2]=torch.tensor([-.25,0.]",
        "world=-pos[:,:2]", "error=term.return_nav_goal[:,:2]-robot.data.root_pos_w[:,:2]"]
    for fragment in required:
        if fragment not in text:raise ValueError('Native connection changed: '+fragment)
    def ref(name):
        node=funcs[name];fragment=ast.get_source_segment(text,node)
        return dict(name=name,start_line=node.lineno,end_line=node.end_lineno,sha256=hashlib.sha256(fragment.encode()).hexdigest())
    return dict(schema='actual-Isaac-local-to-full-navigation-interface-contract-v1',source_manifest_sha256=sha(source/'manifest.json'),probe_sha256=sha(file),
        scope='Read-only actual frozen probe/command interface; NOT complete navigation implementation or trial',
        existing=dict(command_input='nav_policy.velocity_commands <- nav_command, body-frame vx/vy/yaw-rate request',
            arm_pose_input='nav_policy.pos_commands <- nav_pose; existing desired arm pose, not route waypoint',
            initial_nav_target='environment origin, not a general route waypoint consumer',
            return_nav_target='fixed world(-.25,0) and yaw0, consumed by original position/heading velocity request',
            actor_feedback='existing frozen NAV actor owns all18 axes through native adapters; do not retrain/replace',
            phase_chain='NAV -> preparation -> PUSH -> native settled -> stow -> fixed-world return NAV'),
        full_navigation_ready=False,source_functions=[ref(n) for n in ['nav_command','nav_pose','Router','main']],
        currently_NOT_claimed=['current probe consumes a map/route/A* interface','pushed obstacle is passed to a goal beyond it','generic MuJoCo OraclePlanner already executes through this Isaac caller','new local8-cell pilot is a complete obstacle-navigation ablation'],
        required_future_interfaces=[
            dict(name='shared_route_provider',input='same fixed map/start/final goal/ideal-state obstacle query for all arms',output='world-SE2 waypoints, route cost, map/obstacle identity + query time',existing_in_this_probe=False),
            dict(name='waypoint_request_adapter',input='current waypoint + measured robot state',output='existing bounded vx/vy/yaw-rate request; no direct state/PD/history writes',existing_in_this_probe=False),
            dict(name='push_exit_to_route_resume',input='actual native settled/stowed/READY + fresh current obstacle pose',output='resume/replan shared route to same preregistered final goal',existing_in_this_probe=False),
            dict(name='whole_task_evaluator',input='actual route/skill/entry/goal events and all failed/missing starts',output='fixed-goal task completion + whole wall/sim/path/preparation cost and original safety',existing_in_this_probe=False)],
        next_order=['finish approved8 local mechanism starts without changing frozen source','review nonzero request consumption/goal results including zero or negative gains',
            'bind existing project route provider to native waypoint request contract before claiming integration','register independent full-navigation scene and budget; not automatic from remaining6'],
        new_App_or_FK_or_physical_or_actor=0,execution_authorized_by_this_contract=False)


def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    value=inspect(a.source)
    with a.output.open('x') as f:json.dump(value,f,indent=2);f.write('\n')

if __name__=='__main__':main()
