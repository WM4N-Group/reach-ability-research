"""Recorded-cloud figure with existing Pillow; no dependencies installed/trials."""
import argparse,hashlib,json,math
from PIL import Image,ImageDraw,ImageFont,PngImagePlugin
from pathlib import Path


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--diagnosis',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise FileExistsError('Never overwrite a diagnostic figure')
    qs=[v for line in (a.root/'runs/seed120401-E1/entry_geometry.jsonl').read_text().splitlines() if (v:=json.loads(line))['event']=='finite_tip_query']
    report=json.loads(a.diagnosis.read_text());image=Image.new('RGB',(1900,1080),'#f5f7fa');draw=ImageDraw.Draw(image)
    def text(x,y,s,size=24,color='#26354c',bold=False):
        font='/usr/share/fonts/truetype/dejavu/DejaVuSans'+('-Bold' if bold else '')+'.ttf'
        draw.text((x,y),s,font=ImageFont.truetype(font,size),fill=color)
    blue='#377eb8';orange='#d97526'
    text(55,30,'Stopped pilot: pose mismatch, not a measured collision',36,bold=True)
    text(55,90,'E0: common-goal success | E1: final-preview refusal | 2/16 starts used; 14 not run',25)
    draw.rounded_rectangle((40,150,940,905),18,fill='white');draw.rounded_rectangle((965,150,1860,905),18,fill='white')
    text(65,175,'A  Same endpoint sample, different pose',27,bold=True)
    cloud=[]
    for q in qs:cloud.append([[p[0]*1000,p[2]*1000] for p,k in zip(q['tip_cloud_box_m'],q['nominal_indices']) if k==40])
    xmin=5*math.floor(min(p[0] for c in cloud for p in c)/5)-5;xmax=5*math.ceil(max(p[0] for c in cloud for p in c)/5)+5
    zmin=5*math.floor(min(p[1] for c in cloud for p in c)/5)-5;zmax=5*math.ceil(max(p[1] for c in cloud for p in c)/5)+5
    px=lambda x:145+720*(x-xmin)/(xmax-xmin);py=lambda z:720-420*(z-zmin)/(zmax-zmin)
    text(65,245,'tip z (mm)',20)
    for z in range(int(zmin),int(zmax)+1,10):
        draw.line((145,py(z),865,py(z)),fill='#e6eaf0',width=2);text(87,py(z)-12,str(z),19)
    for x in range(int(xmin),int(xmax)+1,10):
        draw.line((px(x),300,px(x),720),fill='#e6eaf0',width=1);text(px(x)-23,733,str(x),18)
    for band,color in [(120,blue),(115,orange)]:draw.line((145,py(band),865,py(band)),fill=color,width=3)
    draw.line((px(-615),300,px(-615),720),fill='#777777',width=2)
    for points,color in zip(cloud,[blue,orange]):
        for x,z in points:draw.ellipse((px(x)-4,py(z)-4,px(x)+4,py(z)+4),fill=color)
    w=report['cloud_change']['witness'];start=w['forecast_point_box_m'];end=w['measured_point_box_m']
    sx,sy=px(start[0]*1000),py(start[2]*1000);ex,ey=px(end[0]*1000),py(end[2]*1000)
    draw.line((sx,sy,ex,ey),fill='#222222',width=3)
    angle=math.atan2(ey-sy,ex-sx)
    draw.polygon([(ex,ey),(ex-14*math.cos(angle-.4),ey-14*math.sin(angle-.4)),(ex-14*math.cos(angle+.4),ey-14*math.sin(angle+.4))],fill='#222222')
    for x,y in [(sx,sy),(ex,ey)]:draw.ellipse((x-9,y-9,x+9,y+9),outline='#222222',width=2)
    text(320,773,'Box-local tip x (mm)',22)
    text(80,818,'Blue: forecast / z band 120 mm',22,blue);text(80,853,'Orange: measured / z band 115 mm',22,orange)
    text(990,175,'B  Scalar request on the logged E1 cloud',26,bold=True)
    text(990,220,'Not four physical outcomes',22,color='#9b6641',bold=True)
    by=lambda v:720-v/1.8*380
    for v in [0,.5,1.,1.5]:
        draw.line((1080,by(v),1795,by(v)),fill='#e6eaf0',width=2);text(1010,by(v)-12,f'{v:.1f}',20)
    text(990,265,'Retreat request (mm)',22)
    arms=['E0','E1','E2','E3'];replay=report['counterfactual_scalar_queries'][1]['requests']
    for i,arm in enumerate(arms):
        x=1120+i*175;v=replay[arm]['request_m']*1000;y=by(v)
        if v:draw.rectangle((x,y,x+90,720),fill=orange)
        else:draw.line((x,720,x+90,720),fill='#777777',width=5)
        if i>=2:
            for yy in range(int(y)+10,720,20):draw.line((x,yy,x+90,min(720,yy+35)),fill='#ffffff',width=3)
        text(x+3,y-37,f'{v:.3f}',23,bold=True);text(x+25,746,arm,25,bold=True)
    text(1005,815,'E0/E1: observed selected outputs',22)
    text(1005,851,'Hatched E2/E3: offline replay only',22,color='#9b6641')
    text(55,942,'Witness: forecast z = 122.311 mm (excluded) -> measured z = 114.472 mm (included).',25,bold=True)
    text(55,989,'No new FK or physical run. This negative development result is not evidence of navigation gain.',23)
    meta=PngImagePlugin.PngInfo();meta.add_text('diagnosis_sha256',hashlib.sha256(a.diagnosis.read_bytes()).hexdigest());meta.add_text('role','stopped_development_pilot_diagnostic_NOT_four_episodes_or_positive_gain')
    image.save(a.output,pnginfo=meta);print(a.output)

if __name__=='__main__':main()
