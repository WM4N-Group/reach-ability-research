"""Encode verified recorded onboard RGB around legal soft failure and stow."""
import argparse
import hashlib
import json
from pathlib import Path

import imageio.v2 as imageio
import numpy as np
from PIL import Image,ImageDraw,ImageFont

from mujoco_zyh.render_scene_review import visual_frames


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--audit',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--from-sim-s',type=float,default=0.)
    args=parser.parse_args()
    root=args.root.resolve();output=args.output.resolve()
    if output.exists():raise FileExistsError(output)
    report=json.loads((root/'report.json').read_text())
    audit=json.loads(args.audit.read_text())
    closure=json.loads((root/'episode/closure.json').read_text())
    support=report['stall_stow_recovery']['supported_push']
    if (not closure['storage_complete'] or report['error'] is not None or
            support['mode']!='compact-supported-PUSH-v25' or
            not audit['actual_original_soft_failure_recovery_pass'] or
            not audit['actual_collector_exited_and_three_locks_available_now']):
        raise ValueError('Expected independently audited actual V25 soft failure and stow')
    soft_time=report['stall_stow_recovery']['abort']['time_s']
    support_rows={round(row['time_s'],2):row for row in map(json.loads,
        (root/'supported-push-200hz.jsonl').read_text().splitlines())}
    recovery_rows={round(row['time_s'],2):row for row in map(json.loads,
        (root/'stow-actual-200hz.jsonl').read_text().splitlines())}
    font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',20)
    writer=imageio.get_writer(output,fps=10,codec='libx264',quality=8,
                              macro_block_size=16)
    frames=0;first=last=None
    try:
        for _,stamp,rgb,_ in visual_frames(root/'episode'):
            if stamp+1e-8<args.from_sim_s:continue
            image=Image.fromarray(rgb).resize((768,512),Image.Resampling.NEAREST)
            canvas=Image.new('RGB',(768,560),(19,25,30))
            canvas.paste(image,(0,0))
            draw=ImageDraw.Draw(canvas)
            key=round(stamp,2)
            if stamp<soft_time:
                row=support_rows.get(key)
                stage=row['alignment_stage'] if row else 'PUSH'
                foot=f' | min foot {min(row["measured_foot_normal_N"]):.1f}N' if row else ''
                label=f'ACTUAL ONBOARD | {stamp:.2f}s | {stage}{foot}'
            else:
                row=recovery_rows.get(key)
                stage=row['phase'] if row else 'PUSH SOFT FAILURE'
                label=f'ACTUAL ONBOARD | {stamp:.2f}s | {stage}'
            draw.text((14,521),label,font=font,fill=(244,247,249))
            writer.append_data(np.asarray(canvas))
            first=stamp if first is None else first;last=stamp;frames+=1
    finally:
        writer.close()
    if not frames:raise ValueError('No recorded frames in selected interval')
    provenance=dict(schema='actual-onboard-v25-soft-failure-stow-review-v1',
        source_root=str(root),source_report_sha256=sha(root/'report.json'),
        source_visual_index_sha256=sha(root/'episode/index.json'),
        source_audit_sha256=sha(args.audit),video_sha256=sha(output),
        frames=frames,fps=10,first_source_sim_s=first,last_source_sim_s=last,
        soft_exit_sim_s=soft_time,terminal_sim_s=report['sim_seconds'],
        recorded_RGB_only=True,nearest_neighbor_enlargement_only=True,
        extra_physics_steps=0,terminal_frame_invented=False,
        actual_legal_contact_soft_exit_and_stow_audited=True,
        independent_generalization_or_reliability_claim=False)
    output.with_suffix('.provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
    print(json.dumps(provenance))


if __name__=='__main__':main()
