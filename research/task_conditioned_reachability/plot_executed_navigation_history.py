"""Paper-development figure from original recorded outcomes; no new trials."""
import hashlib
import json
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,PngImagePlugin

ROOT=Path(__file__).resolve().parents[2]
EV=ROOT/'evidence/2026-10-20'
SOURCE=EV/'executed-v316-v317-navigation-binding-v1/all8_historical_pairs.json'
SUMMARY=EV/'executed-v316-v317-navigation-binding-v1/summary.json'
OUT=EV/'executed-navigation-history-development-v1.png'


def main():
    if OUT.exists():raise ValueError('Keep archived figure, no overwrite')
    pairs=json.loads(SOURCE.read_text());m=json.loads(SUMMARY.read_text())['metrics']
    im=Image.new('RGB',(1900,1080),'#f5f7fa');d=ImageDraw.Draw(im)
    def text(x,y,s,size=25,color='#26354c',bold=False):
        f='/usr/share/fonts/truetype/dejavu/DejaVuSans'+('-Bold' if bold else '')+'.ttf'
        d.text((x,y),s,font=ImageFont.truetype(f,size),fill=color)
    text(55,35,'Isaac NAV-PUSH-stow-NAV: historical simulation evidence',36,bold=True)
    text(55,92,'8 already-used starts | time = simulation seconds | geometry + support-bookkeeping bundle',25)
    d.rounded_rectangle((40,155,1165,875),18,fill='white')
    d.rounded_rectangle((1190,155,1860,875),18,fill='white')
    text(70,180,'Case',25,bold=True);text(220,180,'v316 original outcome',25,bold=True)
    text(575,180,'v317 original outcome',25,bold=True);text(930,180,'Shift request',25,bold=True)
    text(930,215,'v316 -> v317',22)
    for i,p in enumerate(pairs):
        y=275+i*69
        text(75,y,str(p['seed']),26,bold=True)
        for x,side in [(220,'left'),(575,'right')]:
            a=p[side];color='#168671' if a['success'] else '#bc4f45'
            label='DONE' if a['success'] else 'FAILED'
            text(x,y,f"{label}  {a['end_time_s']:.2f} s",25,color,bold=True)
        text(935,y,f"{1000*p['left']['support_shift_m']:.0f} -> {1000*p['right']['support_shift_m']:.0f} mm",25)
        d.line((70,y+50,1132,y+50),fill='#e6eaf0',width=1)
    text(1220,185,'Whole original cycle completion',25,bold=True)
    text(1280,245,'7/8  ->  8/8',51,'#168671',True)
    text(1220,325,'+12.5 percentage points',27,bold=True)
    text(1220,366,'One changed outcome: case 3703',23)
    text(1220,408,'Tuned development, NOT independent',23,'#9b6641',True)
    d.line((1220,460,1825,460),fill='#e6eaf0',width=2)
    text(1220,490,'Time trade-off, not blanket speedup',25,bold=True)
    text(1220,540,f"Common successes (7): +{m['common_success_time_delta_right_minus_left_s']:.3f} s",25,'#9b6641',True)
    text(1220,595,'Failure-penalized time (96 s cap):',23)
    text(1220,638,f"{m['failure_penalized_time_delta_right_minus_left_s']:.3f} s  (descriptive only)",27,'#168671',True)
    text(1220,714,'Same policy/actuator/startup records;',22)
    text(1220,748,'NOT a pure one-flag causal ablation.',22,bold=True)
    text(55,920,'Critical case: 19.33 mm tip-envelope need -> original support selector requests 25 mm.',26,bold=True)
    text(55,968,'Selected recorded robot/command values agree through decision step 942; first difference is step 944.',23)
    text(55,1008,'State-relative return goal, not a fixed map goal. Query-time box/cloud stay unknown; no native safety claim.',23)
    meta=PngImagePlugin.PngInfo()
    meta.add_text('source_sha256',hashlib.sha256(SOURCE.read_bytes()).hexdigest())
    meta.add_text('role','exposed_tuned_development_NOT_independent_or_single_factor_ablation')
    im.save(OUT,pnginfo=meta);print(OUT)


if __name__=='__main__':main()
