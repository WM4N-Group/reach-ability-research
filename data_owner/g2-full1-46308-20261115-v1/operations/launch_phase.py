from pathlib import Path
import sys,subprocess,shlex,json
M=Path(__file__).parent;c,phase=sys.argv[1:];assert phase in ('zero','main');freeze=json.loads((M/'freeze-CAS-receipt.json').read_bytes());program=freeze['programs'][c]
script=f'''set -o noclobber
export LD_PRELOAD=/mnt/yuanyue/data-team/deployments/46308-20261114/dependencies/native-expat-overlay-20261115-v1/lib/libexpat.so.1
export CUDA_VISIBLE_DEVICES=GPU-6d66aa68-9a3f-fdcf-89b7-f98d4106fa39 MUJOCO_GL=egl MUJOCO_EGL_DEVICE_ID=1
export OPENBLAS_NUM_THREADS=2 OMP_NUM_THREADS=2 DATA_PREFIX_CONDITION={shlex.quote(c)}
M=/mnt/yuanyue/data-team/deployments/46308-20261114/workspace/manifests/g2-full1-46308-20261115-v1/{shlex.quote(c)}
/mnt/yuanyue/data-team/env-native-v1/bin/python -I -B /mnt/yuanyue/data-team/deployments/46308-20261114/workspace/workers/g2-full1-46308-20261115-v1/full_host_worker.py --phase {phase} --program-sha256 {program} > "$M/{phase}-launch.stdout" 2> "$M/{phase}-launch.stderr"
e=$?
printf '%s\\n' "$e" > "$M/{phase}-launch.exit"
cat "$M/{phase}-launch.stdout"
cat "$M/{phase}-launch.stderr" >&2
exit "$e"
'''
r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','-o','ControlMaster=auto','-o','ControlPersist=120','-o','ControlPath=/tmp/data-team-46308-01a1d3aa-ssh','-p','46308','root@180.97.68.228','bash -c '+shlex.quote(script)],capture_output=True,text=True,timeout=5500)
(M/c).mkdir(exist_ok=True)
for suffix,text in [('stdout',r.stdout),('stderr',r.stderr),('exit',str(r.returncode)+'\n')]:
 with (M/c/(phase+'-launch-local.'+suffix)).open('x') as f:f.write(text)
print(r.stdout);print(r.stderr,file=sys.stderr);print('PHASE_EXIT',r.returncode);sys.exit(r.returncode)
