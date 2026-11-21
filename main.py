#!/usr/bin/env python3
"""VELMORA — a travel poster for a place that isn't there.

Draws an original 1024x1024 travel poster with only the Python standard
library: a sunset lagoon where the sea rises upward into the sky as the
great Upward Falls of Velmora. Writes /output/entry.png (or
$MAKEFUN_OUTPUT_DIR/entry.png). Fully deterministic, no network.
"""

import math
import os
import struct
import zlib

W = 1024
H = 1024
HORIZON = 620

# ---------------------------------------------------------------- canvas
canvas = [bytearray(W * 3) for _ in range(H)]


def lerp(c1, c2, t):
    return (
        int(c1[0] + (c2[0] - c1[0]) * t),
        int(c1[1] + (c2[1] - c1[1]) * t),
        int(c1[2] + (c2[2] - c1[2]) * t),
    )


def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


def hline(y, x0, x1, color):
    if y < 0 or y >= H:
        return
    x0 = clamp(int(x0), 0, W)
    x1 = clamp(int(x1), 0, W)
    if x1 <= x0:
        return
    row = canvas[y]
    row[x0 * 3:x1 * 3] = bytes(color) * (x1 - x0)


def hline_alpha(y, x0, x1, color, alpha):
    """Alpha fill. Fast path: the scenes this draws over are vertically
    graded, so the base colour is (near-)uniform across a row span; blend
    once per row against the span's centre pixel."""
    if y < 0 or y >= H or alpha <= 0:
        return
    x0 = clamp(int(x0), 0, W)
    x1 = clamp(int(x1), 0, W)
    if x1 <= x0:
        return
    row = canvas[y]
    mid = ((x0 + x1) // 2) * 3
    inv = 1.0 - alpha
    blended = (
        int(row[mid] * inv + color[0] * alpha),
        int(row[mid + 1] * inv + color[1] * alpha),
        int(row[mid + 2] * inv + color[2] * alpha),
    )
    row[x0 * 3:x1 * 3] = bytes(blended) * (x1 - x0)


def fill_rect(x0, y0, x1, y1, color):
    for y in range(clamp(int(y0), 0, H), clamp(int(y1), 0, H)):
        hline(y, x0, x1, color)


def circle(cx, cy, r, color, alpha=1.0):
    r = int(r)
    for dy in range(-r, r + 1):
        y = cy + dy
        if y < 0 or y >= H:
            continue
        dx = int(math.sqrt(max(0, r * r - dy * dy)))
        if alpha >= 1.0:
            hline(y, cx - dx, cx + dx, color)
        else:
            hline_alpha(y, cx - dx, cx + dx, color, alpha)


def ellipse(cx, cy, rx, ry, color, alpha=1.0):
    for dy in range(-int(ry), int(ry) + 1):
        y = cy + dy
        if y < 0 or y >= H:
            continue
        t = 1.0 - (dy * dy) / float(ry * ry)
        if t <= 0:
            continue
        dx = int(rx * math.sqrt(t))
        if alpha >= 1.0:
            hline(y, cx - dx, cx + dx, color)
        else:
            hline_alpha(y, cx - dx, cx + dx, color, alpha)


def poly(points, color):
    """Scanline fill of a simple polygon."""
    ys = [p[1] for p in points]
    y0, y1 = int(min(ys)), int(max(ys))
    n = len(points)
    for y in range(max(0, y0), min(H, y1 + 1)):
        xs = []
        for i in range(n):
            x_a, y_a = points[i]
            x_b, y_b = points[(i + 1) % n]
            if (y_a <= y < y_b) or (y_b <= y < y_a):
                t = (y - y_a) / float(y_b - y_a)
                xs.append(x_a + t * (x_b - x_a))
        xs.sort()
        for i in range(0, len(xs) - 1, 2):
            hline(y, xs[i], xs[i + 1], color)


def line(x0, y0, x1, y1, color, width=1):
    """Simple Bresenham line with square brush."""
    x0, y0, x1, y1 = (int(round(v)) for v in (x0, y0, x1, y1))
    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    x, y = x0, y0
    while True:
        fill_rect(x - width // 2, y - width // 2,
                  x + width // 2 + 1, y + width // 2 + 1, color)
        if x == x1 and y == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x += sx
        if e2 <= dx:
            err += dx
            y += sy


# ------------------------------------------------------------- 5x7 font
# Each glyph: 7 rows, 5 bits each (bit 4 = leftmost pixel).
FONT = {
    'A': (0x0E, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11),
    'B': (0x1E, 0x11, 0x11, 0x1E, 0x11, 0x11, 0x1E),
    'C': (0x0E, 0x11, 0x10, 0x10, 0x10, 0x11, 0x0E),
    'D': (0x1E, 0x11, 0x11, 0x11, 0x11, 0x11, 0x1E),
    'E': (0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x1F),
    'F': (0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x10),
    'G': (0x0E, 0x11, 0x10, 0x17, 0x11, 0x11, 0x0F),
    'H': (0x11, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11),
    'I': (0x0E, 0x04, 0x04, 0x04, 0x04, 0x04, 0x0E),
    'J': (0x07, 0x02, 0x02, 0x02, 0x02, 0x12, 0x0C),
    'K': (0x11, 0x12, 0x14, 0x18, 0x14, 0x12, 0x11),
    'L': (0x10, 0x10, 0x10, 0x10, 0x10, 0x10, 0x1F),
    'M': (0x11, 0x1B, 0x15, 0x15, 0x11, 0x11, 0x11),
    'N': (0x11, 0x19, 0x15, 0x13, 0x11, 0x11, 0x11),
    'O': (0x0E, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E),
    'P': (0x1E, 0x11, 0x11, 0x1E, 0x10, 0x10, 0x10),
    'Q': (0x0E, 0x11, 0x11, 0x11, 0x15, 0x12, 0x0D),
    'R': (0x1E, 0x11, 0x11, 0x1E, 0x14, 0x12, 0x11),
    'S': (0x0F, 0x10, 0x10, 0x0E, 0x01, 0x01, 0x1E),
    'T': (0x1F, 0x04, 0x04, 0x04, 0x04, 0x04, 0x04),
    'U': (0x11, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E),
    'V': (0x11, 0x11, 0x11, 0x11, 0x11, 0x0A, 0x04),
    'W': (0x11, 0x11, 0x11, 0x15, 0x15, 0x1B, 0x11),
    'X': (0x11, 0x11, 0x0A, 0x04, 0x0A, 0x11, 0x11),
    'Y': (0x11, 0x11, 0x0A, 0x04, 0x04, 0x04, 0x04),
    'Z': (0x1F, 0x01, 0x02, 0x04, 0x08, 0x10, 0x1F),
    ' ': (0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00),
}


def text_width(s, scale, spacing):
    return len(s) * (5 * scale + spacing) - spacing if s else 0


def draw_text(s, cx, y, scale, color, spacing=None):
    if spacing is None:
        spacing = scale
    total = text_width(s, scale, spacing)
    x = int(cx - total / 2)
    for ch in s:
        glyph = FONT.get(ch.upper(), FONT[' '])
        for r in range(7):
            bits = glyph[r]
            for c in range(5):
                if bits & (1 << (4 - c)):
                    fill_rect(x + c * scale, y + r * scale,
                              x + (c + 1) * scale, y + (r + 1) * scale,
                              color)
        x += 5 * scale + spacing


# ------------------------------------------------------------------ scene
CREAM = (255, 243, 214)
INK = (26, 22, 64)


def draw():
    # --- sky: deep indigo -> violet -> amber at the horizon
    stops = [
        (0.00, (22, 30, 84)),
        (0.35, (74, 54, 128)),
        (0.52, (146, 82, 128)),
        (0.62, (238, 150, 88)),
        (0.85, (232, 132, 80)),
        (1.00, (214, 110, 74)),
    ]
    for y in range(0, HORIZON):
        t = y / float(HORIZON)
        for i in range(len(stops) - 1):
            if stops[i][0] <= t <= stops[i + 1][0]:
                f = (t - stops[i][0]) / (stops[i + 1][0] - stops[i][0])
                hline(y, 0, W, lerp(stops[i][1], stops[i + 1][1], f))
                break

    # --- sun glow + sun (low, right of centre, above the horizon)
    sun_x, sun_y, sun_r = 712, 500, 82
    circle(sun_x, sun_y, 210, (244, 164, 96), alpha=0.20)
    circle(sun_x, sun_y, 140, (250, 196, 120), alpha=0.35)
    circle(sun_x, sun_y, sun_r, (255, 233, 168))
    circle(sun_x, sun_y, 58, (255, 246, 214))

    # --- drifting clouds, warm-lit underneath
    for (cx, cy, rx, ry, col, al) in [
        (180, 300, 150, 22, (196, 120, 140), 0.55),
        (300, 330, 110, 16, (232, 160, 130), 0.5),
        (830, 250, 130, 18, (150, 96, 150), 0.5),
        (560, 180, 90, 14, (120, 80, 140), 0.45),
        (120, 470, 120, 16, (220, 140, 110), 0.45),
    ]:
        ellipse(cx, cy, rx, ry, col, alpha=al)

    # --- the Upward Falls of Velmora: a river of light climbing the sky
    fx = 330
    top_y, base_y = 238, HORIZON
    for y in range(top_y, base_y):
        # rises from the lagoon, narrowing as it climbs
        f = (y - top_y) / float(base_y - top_y)  # 0 top -> 1 base
        wob = 10 * math.sin(y * 0.045) + 6 * math.sin(y * 0.013 + 1.7)
        half = 16 + 26 * f
        col = lerp((226, 246, 240), (168, 216, 214), f)
        hline(y, fx - half + wob, fx + half + wob, col)
        # bright core
        hline(y, fx - half * 0.45 + wob, fx + half * 0.45 + wob,
              (244, 252, 248))
    # spray where the falls leave the sky, mist where they leave the sea
    ellipse(fx, top_y - 6, 74, 26, (240, 248, 250), alpha=0.75)
    ellipse(fx - 30, top_y + 18, 40, 16, (240, 248, 250), alpha=0.5)
    ellipse(fx + 34, top_y + 26, 34, 13, (240, 248, 250), alpha=0.5)
    ellipse(fx, base_y - 4, 96, 26, (226, 244, 240), alpha=0.6)

    # --- island at the foot of the falls
    ellipse(fx, HORIZON + 8, 128, 22, (30, 78, 70))
    ellipse(fx, HORIZON + 2, 100, 14, (52, 110, 92))
    # tiny lantern posts on the island
    for lx in (fx - 70, fx - 20, fx + 34, fx + 78):
        line(lx, HORIZON - 2, lx, HORIZON - 26, (255, 226, 150), width=2)
        circle(lx, HORIZON - 30, 5, (255, 226, 150))

    # --- sea: warm reflection near the horizon, deep teal below
    for y in range(HORIZON, H):
        t = (y - HORIZON) / float(H - HORIZON)
        hline(y, 0, W, lerp((198, 112, 72), (14, 50, 78), t ** 0.8))
    # sun's reflection column, broken by gentle waves
    for y in range(HORIZON + 6, H - 30, 7):
        wob = 26 * math.sin(y * 0.05) + 12 * math.sin(y * 0.021 + 2.0)
        width = 46 + (y - HORIZON) * 0.12
        alpha = max(0.05, 0.5 - (y - HORIZON) / 900.0)
        hline_alpha(y, sun_x - width + wob, sun_x + width + wob,
                    (255, 214, 140), alpha)
    # wave glints
    for i in range(46):
        y = HORIZON + 26 + (i * 37) % 360
        x = (i * 197) % 980 + 10
        ln = 18 + (i * 53) % 46
        hline_alpha(y, x, x + ln, (255, 226, 170), 0.28)

    # --- cliff headland on the right, dark silhouette, amber rim light
    cliff = [(1024, 1024), (1024, 648), (936, 596), (884, 668),
             (896, 780), (936, 872), (962, 1024)]
    poly(cliff, (20, 28, 56))
    line(936, 596, 884, 668, (242, 166, 90), width=3)
    line(884, 668, 896, 780, (242, 166, 90), width=2)
    # a lone watch-tower on the cliff top
    poly([(928, 596), (944, 596), (940, 556), (932, 556)], (20, 28, 56))
    circle(936, 550, 7, (255, 226, 150))

    # --- sailboats on the lagoon
    def boat(bx, by, s):
        poly([(bx - 16 * s, by), (bx + 16 * s, by), (bx + 10 * s, by + 8 * s),
              (bx - 10 * s, by + 8 * s)], (24, 24, 48))
        poly([(bx, by - 26 * s), (bx, by), (bx + 15 * s, by)],
             (255, 243, 214))
        poly([(bx - 2 * s, by - 20 * s), (bx - 2 * s, by),
              (bx - 13 * s, by)], (242, 190, 130))
        line(bx, by - 28 * s, bx, by, (24, 24, 48), width=2)

    boat(560, 792, 1.0)
    boat(838, 884, 0.7)
    boat(150, 872, 0.8)

    # --- birds
    for (bx, by, s) in [(500, 330, 14), (560, 300, 11), (620, 350, 9),
                        (210, 210, 10), (760, 330, 12)]:
        line(bx - s, by, bx, by - s // 2, (30, 26, 66), width=2)
        line(bx, by - s // 2, bx + s, by, (30, 26, 66), width=2)

    # --- poster frame
    fill_rect(18, 18, W - 18, 26, CREAM)
    fill_rect(18, H - 26, W - 18, H - 18, CREAM)
    fill_rect(18, 18, 26, H - 18, CREAM)
    fill_rect(W - 26, 18, W - 18, H - 18, CREAM)

    # --- the name, big and legible, with a soft shadow
    draw_text("VELMORA", 512, 76, 17, (18, 16, 56), spacing=17)
    draw_text("VELMORA", 512, 70, 17, CREAM, spacing=17)
    # rule under the name
    fill_rect(362, 208, 662, 212, CREAM)

    # --- tagline at the foot of the poster
    draw_text("WHERE THE SEA RISES TO MEET THE SKY",
              512, 946, 4, (18, 16, 56), spacing=4)
    draw_text("WHERE THE SEA RISES TO MEET THE SKY",
              512, 943, 4, CREAM, spacing=4)


# -------------------------------------------------------------------- png
def write_png(path):
    raw = b"".join(b"\x00" + bytes(row) for row in canvas)
    comp = zlib.compress(raw, 9)

    def chunk(typ, data):
        return (struct.pack(">I", len(data)) + typ + data +
                struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF))

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", comp)
    png += chunk(b"IEND", b"")
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "wb") as f:
        f.write(png)


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    draw()
    write_png(os.path.join(out_dir, "entry.png"))


if __name__ == "__main__":
    main()
