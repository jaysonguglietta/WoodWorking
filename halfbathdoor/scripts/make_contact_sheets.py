#!/usr/bin/env python3
"""Create legible contact sheets for manual visual QC."""
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
source = ROOT / "build/reports/page-images"
output = ROOT / "build/reports/contact-sheets"
output.mkdir(parents=True, exist_ok=True)

for folder in sorted(p for p in source.iterdir() if p.is_dir()):
    for prior in output.glob(f"{folder.name}-*.jpg"):
        prior.unlink()
    pages = sorted(folder.glob("*.png"))
    for batch, start in enumerate(range(0, len(pages), 12), 1):
        selected = pages[start:start+12]
        thumb_w, thumb_h = 255, 330
        sheet = Image.new("RGB", (4*thumb_w, 3*(thumb_h+22)), "white")
        draw = ImageDraw.Draw(sheet)
        for idx, page in enumerate(selected):
            with Image.open(page) as im:
                im.thumbnail((thumb_w-10, thumb_h-10))
                x=(idx%4)*thumb_w+(thumb_w-im.width)//2
                y=(idx//4)*(thumb_h+22)+5
                sheet.paste(im,(x,y))
                draw.text(((idx%4)*thumb_w+5, y+thumb_h), page.stem, fill="black")
        sheet.save(output/f"{folder.name}-{batch:02d}.jpg", quality=88)
print(f"PASS: contact sheets written to {output}")
