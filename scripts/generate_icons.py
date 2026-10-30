"""Generate PWA icons for the frontend (run from the repository root).

Usage: python scripts/generate_icons.py
Requires Pillow.
"""

from pathlib import Path

from PIL import Image, ImageDraw

OUT_DIR = Path(__file__).resolve().parent.parent / "frontend" / "public" / "icons"
INDIGO_TOP = (129, 140, 248)  # #818cf8
INDIGO_BOTTOM = (79, 70, 229)  # #4f46e5
BOLT = [
    (0.57, 0.13),
    (0.28, 0.56),
    (0.46, 0.56),
    (0.38, 0.87),
    (0.72, 0.42),
    (0.53, 0.42),
]


def gradient(size: int) -> Image.Image:
    image = Image.new("RGB", (size, size))
    pixels = image.load()
    for y in range(size):
        ratio = y / max(size - 1, 1)
        color = tuple(
            round(top + (bottom - top) * ratio)
            for top, bottom in zip(INDIGO_TOP, INDIGO_BOTTOM)
        )
        for x in range(size):
            pixels[x, y] = color
    return image


def make_icon(size: int, bolt_scale: float = 1.0, radius_ratio: float = 0.22) -> Image.Image:
    base = gradient(size).convert("RGBA")

    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        (0, 0, size - 1, size - 1), radius=int(size * radius_ratio), fill=255
    )
    base.putalpha(mask)

    draw = ImageDraw.Draw(base)
    cx = cy = size / 2
    points = []
    for x, y in BOLT:
        points.append((cx + (x - 0.5) * size * bolt_scale, cy + (y - 0.5) * size * bolt_scale))
    draw.polygon(points, fill=(255, 255, 255, 255))
    return base


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    make_icon(192).save(OUT_DIR / "icon-192.png")
    make_icon(512).save(OUT_DIR / "icon-512.png")
    # Maskable icons need the artwork inside the safe zone (~80%).
    make_icon(512, bolt_scale=0.78, radius_ratio=0.5).save(OUT_DIR / "icon-maskable-512.png")
    make_icon(180, bolt_scale=0.9, radius_ratio=0.22).save(OUT_DIR / "apple-touch-icon.png")
    print(f"Icons written to {OUT_DIR}")


if __name__ == "__main__":
    main()
