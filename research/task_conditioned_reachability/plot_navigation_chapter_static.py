"""Render recorded STATIC development numbers, never physical navigation gains."""
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, PngImagePlugin
from piper_kinematics import REPO, sha

SRC = REPO/'evidence/2026-10-20/piper-state-height-static-ablations-posthoc-v1.json'
NAV = REPO/'evidence/2026-10-20/original-planner-navigation-shadow-v1/state_packets_and_shadow_proposals.json'
OUT = REPO/'evidence/2026-10-20/navigation-chapter-static-development-v1.png'


def main():
    if OUT.exists():
        raise ValueError('Keep archived figure; do not overwrite')
    report = json.loads(SRC.read_text())
    nav = json.loads(NAV.read_text())
    im = Image.new('RGB', (1800, 1030), '#f5f7fa')
    d = ImageDraw.Draw(im)
    regular = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
    bold = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
    def text(x, y, value, size=24, color='#25344a', heavy=False):
        d.text((x, y), value, font=ImageFont.truetype(bold if heavy else regular, size), fill=color)
    text(60, 35, 'Piper operational navigation goals: static shadow evidence', 37, heavy=True)
    text(60, 93, 'STATIC MODEL ONLY  |  0 navigation rollouts  |  same 75 SE2 candidates per height', 25)
    d.rounded_rectangle((45, 155, 850, 865), 18, fill='white')
    d.rounded_rectangle((880, 155, 1755, 865), 18, fill='white')
    text(75, 180, 'A  State-conditioned candidate coverage', 26, heavy=True)
    text(75, 225, 'Height is a condition, NOT an executable action.', 22)
    colors = ['#587aa6', '#23a185', '#efa63c']
    names = ['Task pose IK found', 'Endpoint gate', 'All 21 path samples']
    for i, (color, name) in enumerate(zip(colors, names)):
        d.rectangle((90, 277+i*34, 108, 295+i*34), fill=color)
        text(120, 273+i*34, name, 22)
    x0, y0, w, h = 125, 755, 650, 345
    for count in [0, 15, 30, 45, 60, 75]:
        y = y0-h*count/75
        d.line((x0, y, x0+w, y), fill='#e3e8f0', width=2)
        text(80, y-12, str(count), 20)
    for j, s in enumerate(report['states']):
        values = [s['task_pose_found'], s['endpoint_pass'], s['sampled_path_pass']]
        for i, value in enumerate(values):
            x = x0+50+j*215+i*43
            y = y0-h*value/75
            if value:
                d.rectangle((x, y, x+31, y0), fill=colors[i])
            else:
                d.line((x, y0, x+31, y0), fill=colors[i], width=5)
            text(x+2, y-31, str(value), 21, heavy=True)
        text(x0+42+j*215, 785, f"h={s['height_m']:.2f} m", 23)
    text(910, 180, 'B  Selected goal: model minimum clearance', 26, heavy=True)
    text(910, 225, 'h=0.28 m; cost = original A* grid-path length (static)', 22)
    arms = nav['0.28']['selections']
    x0, y0, w, h = 990, 755, 710, 390
    ymin, ymax = -50, 80
    py = lambda v: y0-h*(v-ymin)/(ymax-ymin)
    for v in [-50, -25, 0, 25, 50, 75]:
        d.line((x0, py(v), x0+w, py(v)), fill='#e3e8f0', width=2)
        text(930, py(v)-12, str(v), 20)
    d.line((x0, py(35), x0+w, py(35)), fill='#596579', width=3)
    for i, a in enumerate(arms):
        v = 1000*a['sampled_min_model_clearance_m']
        x = x0+25+i*115
        d.rectangle((x, min(py(v), py(0)), x+60, max(py(v), py(0))), fill='#d87167' if v < 35 else '#23a185')
        text(x-8, py(v)-32 if v >= 0 else py(v)+8, f'{v:.2f}', 20, heavy=True)
        text(x+6, 788, ['N0','N1','N2','N3','M','G'][i], 22, heavy=True)
    d.line((x0, py(35), x0+w, py(35)), fill='#596579', width=3)
    text(x0+5, py(35)-31, '35 mm required', 20)
    text(930, 330, 'mm', 20)
    text(910, 828, 'N0 route; N1 task; N2 end; N3 path; M margin; G gate', 20)
    text(60, 900, 'Observed: 39 task-pose paths, but only 8 meet the nominal joint/35 mm checks.', 25, heavy=True)
    text(60, 942, 'Original A* on synthetic geometry, not robot motion. No extra path-gate selection benefit observed here.', 22)
    meta = PngImagePlugin.PngInfo()
    meta.add_text('coverage_source_sha256', sha(SRC))
    meta.add_text('original_planner_shadow_source_sha256', sha(NAV))
    meta.add_text('role', 'static_development_NOT_navigation_success_or_safety')
    im.save(OUT, pnginfo=meta)
    print(OUT)


if __name__ == '__main__':
    main()
