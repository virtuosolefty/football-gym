"""Overlay output crosses on decoder-exact frames for an explicitly implementer-led audit."""
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
DATA=ROOT / 'test-results' / HERE.name


def main():
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',18)
    for method in ['detector','colour','followup']:
        path=HERE / f'runs-{method}.json'
        if not path.exists():continue
        for entry in json.loads(path.read_text(encoding='utf-8'))['clips']:
            run=entry.get('analysis')
            if not run or entry['id'].startswith('control-'):continue
            samples=[(i,s) for i,s in enumerate(run['samples']) if s['found']]
            sheets=DATA / 'audit-sheets';sheets.mkdir(exist_ok=True)
            for offset in range(0,len(samples),12):
                selected=samples[offset:offset+12]
                tall=run['height']>run['width']
                tile_width,tile_height=(340,640) if tall else (640,380)
                sheet=Image.new('RGB',(tile_width*3,tile_height*4),'#f5f5eb');draw=ImageDraw.Draw(sheet)
                for k,(index,sample) in enumerate(selected):
                    frame=DATA / 'reference-frames' / entry['id'] / (f"{sample['time']:.3f}.png")
                    assert frame.exists(), f'Missing audit frame: {frame}'
                    image=Image.open(frame).convert('RGB');anno=ImageDraw.Draw(image)
                    px,py=sample['x']*image.width,sample['y']*image.height
                    r=max(6,image.width/160)
                    anno.line((px-r,py,px+r,py),fill='#ff1f36',width=max(2,round(image.width/640)))
                    anno.line((px,py-r,px,py+r),fill='#ff1f36',width=max(2,round(image.width/640)))
                    image.thumbnail((tile_width-10,tile_height-40))
                    x,y=k%3*tile_width,k//3*tile_height
                    sheet.paste(image,(x,y+35));draw.text((x+4,y+4),f"{index}: {sample['time']:.2f}s score={sample.get('score','n/a')}",fill='#123e30',font=font)
                sheet.save(sheets / f"{entry['id']}-{method}-{offset:03}.jpg",quality=92)
    print('Audit sheets prepared for frames already captured.')


if __name__=='__main__':main()
