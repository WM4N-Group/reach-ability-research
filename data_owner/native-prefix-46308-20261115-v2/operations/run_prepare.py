from pathlib import Path
import sys,json,subprocess,shlex
M=Path(__file__).parent;c=sys.argv[1];program=json.loads((M/'freeze-CAS-receipt.json').read_bytes())['programs'][c]
script=f'''set -o noclobber
M=/mnt/yuanyue/data-team/deployments/46308-20261114/workspace/manifests/native-prefix-46308-20261115-v2/{shlex.quote(c)}
LD_PRELOAD=/mnt/yuanyue/data-team/deployments/46308-20261114/dependencies/native-expat-overlay-20261115-v1/lib/libexpat.so.1 CUDA_VISIBLE_DEVICES="" MUJOCO_GL=disable OPENBLAS_NUM_THREADS=2 OMP_NUM_THREADS=2 DATA_PREFIX_CONDITION={shlex.quote(c)} /mnt/yuanyue/data-team/env-native-v1/bin/python -I -B /mnt/yuanyue/data-team/deployments/46308-20261114/workspace/workers/native-prefix-46308-20261115-v2/full_host_worker.py --phase prepare --program-sha256 {program} > "$M/fenced-prepare.stdout" 2> "$M/fenced-prepare.stderr"
e=$?
printf '%s\\n' "$e" > "$M/fenced-prepare.exit"
cat "$M/fenced-prepare.stdout"; cat "$M/fenced-prepare.stderr" >&2
exit "$e"
'''
r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','-o','ControlMaster=auto','-o','ControlPersist=120','-o','ControlPath=/tmp/data-team-46308-01a1d3aa-ssh','-p','46308','root@180.97.68.228','bash -c '+shlex.quote(script)],capture_output=True,text=True,timeout=180);(M/c).mkdir(exist_ok=True)
for suffix,text in [('stdout',r.stdout),('stderr',r.stderr),('exit',str(r.returncode)+'\n')]:
 with (M/c/('fenced-prepare-local.'+suffix)).open('x') as f:f.write(text)
print(r.stdout);print(r.stderr,file=sys.stderr);sys.exit(r.returncode)
