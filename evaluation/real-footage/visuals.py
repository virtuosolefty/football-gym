"""Render diagnostic evidence, keeping it separate from tracker input frames."""
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
DATA = ROOT / "test-results" / "real-footage"


def main():
    runs = {r["id"]: r["analysis"] for r in json.loads((HERE / "runs.json").read_text())}
    font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 17)
    small = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 14)
    examples = [("daylight", 0, (244,332,37), "Background patch selected"),
                ("indoor", 3, (138,148,8), "Jersey patch selected"),
                ("strobe", 5, (149,19,13), "Body/clothing patch selected")]
    canvas = Image.new("RGB", (1080, 780), "#f5f6f0")
    draw = ImageDraw.Draw(canvas)
    draw.text((25, 16), "Real-footage evaluation: selected patch versus active ball", fill="#133c30", font=font)
    draw.text((25, 47), "Red cross = tracker output. Green circle = approximate human reference. Production inputs are unchanged.", fill="#45554a", font=small)
    for row,(clip,index,(x,y,radius),caption) in enumerate(examples):
        frame = Image.open(DATA / "frames" / f"{clip}-{index:02}.png").convert("RGB")
        sample = runs[clip]["samples"][index]
        box = (0, 0, 320, 400) if clip=="daylight" else (0,0,frame.width,frame.height)
        visual = frame.crop(box)
        annotation = ImageDraw.Draw(visual)
        annotation.ellipse((x-radius,y-radius,x+radius,y+radius), outline="#43e585", width=2)
        px,py=sample["x"]*frame.width,sample["y"]*frame.height
        annotation.line((px-7,py-7,px+7,py+7), fill="#ff5e65", width=3)
        annotation.line((px-7,py+7,px+7,py-7), fill="#ff5e65", width=3)
        # Uniform fit for the evidence panel; this resized image is never evaluated.
        visual.thumbnail((450,200))
        offset=(25,100+row*225)
        canvas.paste(visual,offset)
        draw.text((500,110+row*225), f"{clip.upper()} · {index/10:.1f}s", fill="#133c30", font=font)
        draw.text((500,145+row*225),caption,fill="#45554a",font=font)
        draw.text((500,177+row*225),"The report evaluates the software, not the player's skill.",fill="#6b776d",font=small)
    canvas.save(HERE / "examples.png")
    print(str(HERE / "examples.png"))


if __name__ == "__main__":
    main()
