"""Generate assets/icon.ico - a rounded neon tile carrying the Shard mark."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parent.parent / "assets" / "icon.ico"
SIZES = [16, 24, 32, 48, 64, 128, 256]

# Matches the default "Neon Crystal" palette.
ACCENT = (255, 45, 149, 255)
ACCENT_DARK = (34, 211, 238, 255)
GLYPH = (8, 6, 15, 255)


def render(size: int) -> Image.Image:
    # Supersample for clean edges, then downscale.
    scale = 8
    box = size * scale
    img = Image.new("RGBA", (box, box), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    radius = int(box * 0.22)
    # Simple vertical gradient behind a rounded-rect mask.
    grad = Image.new("RGBA", (box, box))
    gdraw = ImageDraw.Draw(grad)
    for y in range(box):
        t = y / max(1, box - 1)
        gdraw.line(
            [(0, y), (box, y)],
            fill=tuple(round(a + (b - a) * t) for a, b in zip(ACCENT, ACCENT_DARK)),
        )
    mask = Image.new("L", (box, box), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, box - 1, box - 1], radius, fill=255)
    img.paste(grad, (0, 0), mask)

    # Crystal shard, authored on a 24x24 grid.
    u = box / 24.0
    draw.polygon(
        [(12 * u, 3.0 * u), (17.6 * u, 9.6 * u), (14.2 * u, 21.0 * u),
         (9.8 * u, 21.0 * u), (6.4 * u, 9.6 * u)],
        fill=GLYPH,
    )
    return img.resize((size, size), Image.LANCZOS)


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    frames = [render(s) for s in SIZES]
    frames[-1].save(OUT, format="ICO", sizes=[(s, s) for s in SIZES])
    print(f"wrote {OUT}  ({OUT.stat().st_size / 1024:.1f} KiB)")


if __name__ == "__main__":
    main()
