"""Deterministic ball markers, with exact visibility/positions; not real athlete or weather validation."""
import hashlib
import io
import json
import math
from pathlib import Path
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
DATA = ROOT / "test-results" / HERE.name
sys.path.insert(0, str(ROOT))
from football.store import Store

CASES = [
    ("control-football", "football", "clear", 16, 1, 4),
    ("control-basket", "basket", "clear", 16, 1, 4),
    ("control-tennis", "tennis", "clear", 10, 1, 4),
    ("control-small", "football", "clear", 5, 1, 4),
    ("control-fast", "football", "clear", 16, 2.5, 4),
    ("control-dark", "football", "dark", 16, 1, 4),
    ("control-rain", "football", "rain-overlay", 16, 1, 4),
    ("control-blur", "football", "blur", 16, 1, 4),
    ("control-occlusion", "football", "occlusion", 16, 1, 4),
    ("control-edge-decoy", "football", "edge-decoy", 16, 1, 4),
    ("control-cut-decoy", "football", "cut-decoy", 16, 1, 4),
    ("control-30s", "football", "clear", 16, 1, 30),
]


def sphere(style, radius):
    side = radius * 2 + 1
    yy,xx=np.mgrid[-radius:radius+1,-radius:radius+1]
    shade=np.clip(1-.35*(xx+yy+2*radius)/(4*radius),.6,1)
    colour={"football":(245,245,228),"basket":(218,116,38),"tennis":(208,233,49)}[style]
    arr=np.zeros((side,side,4),dtype=np.uint8)
    arr[:,:,:3]=(shade[:,:,None]*np.array(colour)).astype(np.uint8)
    arr[:,:,3]=np.where(xx*xx+yy*yy<=radius*radius,255,0)
    ball=Image.fromarray(arr)
    draw=ImageDraw.Draw(ball)
    if style == "football":
        for cx,cy in [(radius,radius),(radius//3,radius//3),(radius*1.7,radius*.4),(radius*.4,radius*1.7),(radius*1.7,radius*1.7)]:
            draw.regular_polygon((cx,cy,max(2,radius*.27)),5,fill="#202523",rotation=18)
    elif style == "basket":
        draw.arc((1,1,side-2,side-2),0,359,fill="#4d2918",width=2)
        draw.line((radius,0,radius,side),fill="#4d2918",width=2);draw.line((0,radius,side,radius),fill="#4d2918",width=2)
    else:
        draw.arc((-radius,1,radius*1.2,side-2),-90,90,fill="#fff8bf",width=2)
        draw.arc((radius*.8,1,radius*3,side-2),90,270,fill="#fff8bf",width=2)
    return ball


def position(t, radius, speed, effect):
    if effect == "edge-decoy":
        x=160+80*t
        return x,90, x-radius<320
    if effect == "cut-decoy":
        return 160,90,t<1.5
    x=160+35*math.sin(t*1.4)
    phase=(t*speed+.5)%1
    y=135-75*4*phase*(1-phase)
    return x,y,not (effect == "occlusion" and 1.5<=t<2)


def main():
    binary=next((DATA / "tools").glob("ffmpeg*.exe"))
    store=Store(DATA / "app-data")
    assert store.get("profile")["name"] == "Validation 2026-10-14"
    reference=json.loads((HERE / "reference.json").read_text(encoding="utf-8"))
    existing={c["id"] for c in reference["clips"]}
    rng=np.random.default_rng(42)
    background=np.full((180,320,3),[24,62,43],dtype=np.int16)+rng.integers(-4,5,(180,320,1))
    background=Image.fromarray(np.clip(background,0,255).astype(np.uint8))
    sources=[]
    for identifier,style,effect,radius,speed,duration in CASES:
        target=DATA / "footage" / (identifier+".mp4")
        if identifier in existing:
            continue
        ball=sphere(style,radius)
        process=subprocess.Popen([str(binary),"-y","-hide_banner","-loglevel","error","-f","rawvideo","-pix_fmt","rgb24","-s","320x180","-r","30","-i","pipe:0","-an","-c:v","libx264","-crf","18","-pix_fmt","yuv420p","-g","15",str(target)],stdin=subprocess.PIPE)
        for index in range(int((duration+.1)*30)):
            t=index/30
            image=background.copy();draw=ImageDraw.Draw(image)
            draw.line((0,150,320,150),fill="#c7d2c3",width=2)
            x,y,visible=position(t,radius,speed,effect)
            if visible:image.paste(ball,(round(x-radius),round(y-radius)),ball)
            if effect == "edge-decoy" and t>=2.2:image.paste(ball,(272-radius,90-radius),ball)
            if effect == "cut-decoy" and t>=1.5:
                image=Image.new('RGB',(320,180),(45,53,79));image.paste(ball,(170-radius,90-radius),ball)
            if effect == "rain-overlay":
                rain=ImageDraw.Draw(image)
                for k in range(25):
                    px=(k*43+index*3)%320;py=(k*71+index*11)%180;rain.line((px,py,px+3,py+12),fill="#829991",width=1)
            if effect == "blur":image=image.filter(ImageFilter.GaussianBlur(3))
            if effect == "dark":image=Image.fromarray((np.asarray(image)*.25).astype(np.uint8))
            process.stdin.write(image.tobytes())
        process.stdin.close();assert process.wait()==0
        digest=hashlib.sha256(target.read_bytes()).hexdigest()
        filename=digest[:32]+'.mp4';(store.media / filename).write_bytes(target.read_bytes())
        store.append('media',{'name':target.name,'filename':filename,'size':target.stat().st_size,'sha256':digest,'mime':'video/mp4'})
        x,y,_=position(0,radius,speed,effect)
        reference['clips'].append({'id':identifier,'file':target.name,'window':[0,duration],'seed_time':0,'click_normalized':[x/320,y/180],'radius':radius,'kind':f'CONTROLLED: {style}; {effect}; radius {radius}px; speed {speed}; exact generated ground truth; not real weather or contact evidence'})
        frames=[]
        for i in range(duration*10):
            t=i/10;x,y,visible=position(t,radius,speed,effect)
            status='visible' if visible else 'absent'
            if effect=='edge-decoy' and visible and (x-radius<0 or x+radius>320):status='occluded'
            frames.append({'time':t,'status':status,'x':max(0,min(1,x/320)),'y':y/180,'radius':radius})
        labels={'format':'football-evaluation-1','clip':{'id':identifier,'sha256':digest,'width':320,'height':180,'start':0,'end':duration},'annotator':{'id':'deterministic-generator','role':'implementer','independent':False},'conditions':[style,effect],'frames':frames,'contacts':[], 'notes':'Exact generated marker positions/visibility. Turning points are not human foot contacts.'}
        (HERE / (identifier+'-labels.json')).write_text(json.dumps(labels,indent=2),encoding='utf-8')
        sources.append({'id':identifier,'file':target.name,'sha256':digest,'generator':'controlled.py','origin':'original deterministic synthetic marker, not real athlete/weather footage'})
        print('generated',identifier,flush=True)
    (HERE / 'reference.json').write_text(json.dumps(reference,indent=2),encoding='utf-8')
    (HERE / 'controlled-sources.json').write_text(json.dumps(sources,indent=2),encoding='utf-8')


if __name__ == '__main__':main()
