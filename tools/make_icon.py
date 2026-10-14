#!/usr/bin/env python3
"""Draw the app icon (a d20 silhouette) as PNGs in site/src/icons/. Stdlib only; macOS sips downsamples."""
import math
import struct
import subprocess
import zlib
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "site" / "src" / "icons"
SIZE = 1024
BG = (29, 27, 24)
FACE = (224, 168, 79)
LINE_WIDTH = 0.022 * SIZE


def png(path, pixels, size):
    raw = b"".join(b"\x00" + bytes(c for px in row for c in px) for row in pixels)
    chunk = lambda tag, data: struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data))
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )


def seg_dist(p, a, b):
    (px, py), (ax, ay), (bx, by) = p, a, b
    dx, dy = bx - ax, by - ay
    t = max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - ax - t * dx, py - ay - t * dy)


def inside(p, poly):
    x, y = p
    hit = False
    for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]):
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            hit = not hit
    return hit


def main():
    c, r = SIZE / 2, SIZE * 0.36
    # Pointy-top hexagon: top, top-right, bottom-right, bottom, bottom-left, top-left.
    hexagon = [(c + r * math.cos(math.radians(a)), c - r * math.sin(math.radians(a))) for a in (90, 30, -30, -90, -150, 150)]
    top, tr, br, bottom, bl, tl = hexagon
    t_top, t_bl, t_br = (c, c - 0.52 * r), (c - 0.5 * r, c + 0.33 * r), (c + 0.5 * r, c + 0.33 * r)
    segments = [
        (t_top, t_bl), (t_bl, t_br), (t_br, t_top),
        (t_top, tl), (t_top, top), (t_top, tr),
        (t_bl, tl), (t_bl, bl), (t_bl, bottom),
        (t_br, tr), (t_br, br), (t_br, bottom),
    ]
    pixels = []
    for y in range(SIZE):
        row = []
        for x in range(SIZE):
            p = (x + 0.5, y + 0.5)
            on_face = inside(p, hexagon) and all(seg_dist(p, a, b) > LINE_WIDTH / 2 for a, b in segments)
            row.append(FACE if on_face else BG)
        pixels.append(row)

    OUT.mkdir(parents=True, exist_ok=True)
    master = OUT / "icon-1024.png"
    png(master, pixels, SIZE)
    for size, name in ((512, "icon-512.png"), (192, "icon-192.png"), (180, "apple-touch-icon.png")):
        subprocess.run(["sips", "-Z", str(size), str(master), "--out", str(OUT / name)], check=True, capture_output=True)
    master.unlink()


if __name__ == "__main__":
    main()
