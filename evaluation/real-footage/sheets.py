"""Reference contact sheets; these images are never inputs to the tracker."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "test-results" / "real-footage"
FONT = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 15)


def sheet(clip, kind, start, count, step, crop=None):
    source = DATA / kind
    first = Image.open(source / f"{clip}-{start:02}.png").convert("RGB")
    if crop:
        first = first.crop(crop)
    width, height = first.size
    columns, rows = 5, (count + 4) // 5
    canvas = Image.new("RGB", (columns * width, rows * (height + 26)), "white")
    draw = ImageDraw.Draw(canvas)
    for index in range(start, start + count):
        frame = Image.open(source / f"{clip}-{index:02}.png").convert("RGB")
        if crop:
            frame = frame.crop(crop)
        x, y = (index-start) % columns * width, (index-start) // columns * (height+26)
        canvas.paste(frame, (x, y+26))
        draw.text((x+6, y+4), f"{clip} {index:02} | {index*step:.2f}s", fill="black", font=FONT)
    output = DATA / "sheets" / f"{clip}-{kind}-{start:02}.png"
    output.parent.mkdir(exist_ok=True)
    canvas.save(output)
    print(str(output))


def main():
    for clip in ["daylight", "indoor", "strobe"]:
        crop = (0, 140, 320, 440) if clip == "daylight" else None
        sheet(clip, "frames", 0, 30, .1, crop)
        for start in [0, 25, 50]:
            sheet(clip, "contacts", start, 25, .04, crop)


if __name__ == "__main__":
    main()
