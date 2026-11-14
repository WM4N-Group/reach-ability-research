"""Render verified actual onboard RGB and measured support labels, without physics."""
import argparse
import hashlib
import json
from pathlib import Path

import imageio.v2 as imageio
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from mujoco_zyh.render_scene_review import visual_frames


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--from-sim-s', type=float, default=0.)
    args = parser.parse_args()
    root = args.root.resolve()
    output = args.output.resolve()
    if output.exists():
        raise FileExistsError(output)
    report = json.loads((root / 'report.json').read_text())
    closure = json.loads((root / 'episode/closure.json').read_text())
    if (not closure['storage_complete'] or
            report['error'] != "RuntimeError('supported_PUSH_arm_contact_support_below_12N')" or
            report['stall_stow_recovery']['supported_push']['mode'] != 'compact-supported-PUSH-v22'):
        raise ValueError('Expected complete actual V22 support-stop episode')
    rows = [json.loads(line) for line in (root / 'supported-push-200hz.jsonl').open()]
    stage_by_time = {round(row['time_s'], 2): row for row in rows}
    output.parent.mkdir(parents=True, exist_ok=True)
    font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 20)
    writer = imageio.get_writer(output, fps=10, codec='libx264', quality=8,
                                macro_block_size=16)
    frames = 0
    first = last = None
    try:
        for _, stamp, rgb, _ in visual_frames(root / 'episode'):
            if stamp + 1e-8 < args.from_sim_s:
                continue
            image = Image.fromarray(rgb).resize((768, 512), Image.Resampling.NEAREST)
            canvas = Image.new('RGB', (768, 560), (19, 25, 30))
            canvas.paste(image, (0, 0))
            draw = ImageDraw.Draw(canvas)
            support = stage_by_time.get(round(stamp, 2))
            label = f'ACTUAL ONBOARD  |  {stamp:.2f}s'
            if support:
                label += f'  |  {support["alignment_stage"]}'
                label += f'  |  min foot {min(support["measured_foot_normal_N"]):.1f}N'
            draw.text((14, 521), label, font=font, fill=(244, 247, 249))
            writer.append_data(np.asarray(canvas))
            first = stamp if first is None else first
            last = stamp
            frames += 1
    finally:
        writer.close()
    if frames == 0:
        raise ValueError('No recorded frames in selected interval')
    provenance = dict(schema='actual-onboard-v22-failure-review-v1',
                      source_root=str(root), source_report_sha256=sha(root / 'report.json'),
                      source_visual_index_sha256=sha(root / 'episode/index.json'),
                      source_support_stream_sha256=sha(root / 'supported-push-200hz.jsonl'),
                      video_sha256=sha(output), frames=frames, fps=10,
                      first_source_sim_s=first, last_source_sim_s=last,
                      terminal_sim_s=report['sim_seconds'],
                      actual_recorded_rgb=True, nearest_neighbor_enlargement_only=True,
                      extra_physics_steps=0, model_or_actor_forwards=0,
                      terminal_frame_invented=False, task_success=False,
                      legal_contact_or_soft_failure_or_stow_claimed=False)
    output.with_suffix('.provenance.json').write_text(json.dumps(provenance, indent=2) + '\n')
    print(json.dumps(provenance))


if __name__ == '__main__':
    main()
