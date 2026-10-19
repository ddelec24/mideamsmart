"""Generate the plugin icon and the device images.

Usage: python3 tools/make_icons.py <path to plugin-template template_icon.png>

The rounded-square shape is taken from the alpha channel of the official
plugin-template icon (309x348, transparent band at the bottom), so the result
follows the Jeedom icon model.
"""

import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

SCALE = 4
WIDTH, HEIGHT = 309, 348
SQUARE = 309
TOP_COLOR = (14, 74, 140)
BOTTOM_COLOR = (32, 160, 220)
WHITE = (255, 255, 255, 255)
PLUGIN_DIR = Path(__file__).resolve().parent.parent


def gradient(size, top, bottom):
    w, h = size
    img = Image.new('RGBA', size)
    draw = ImageDraw.Draw(img)
    for y in range(h):
        t = y / (h - 1)
        color = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
        draw.line([(0, y), (w, y)], fill=color + (255,))
    return img


def draw_wave(draw, x0, x1, y, amplitude, periods, width):
    """Draw a smooth thick sine wave with round caps by stamping discs along the curve."""
    r = width / 2
    steps = int((x1 - x0) / 2)
    for i in range(steps + 1):
        x = x0 + (x1 - x0) * i / steps
        py = y + amplitude * math.sin(2 * math.pi * periods * i / steps)
        draw.ellipse([x - r, py - r, x + r, py + r], fill=WHITE)


def draw_droplet(draw, cx, cy, radius):
    draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], fill=WHITE)
    tip = cy - radius * 2.3
    draw.polygon([(cx - radius * 0.93, cy - radius * 0.38), (cx, tip), (cx + radius * 0.93, cy - radius * 0.38)], fill=WHITE)


def draw_ac_unit(draw, box, color_slot, with_droplet):
    s = SCALE
    x0, y0, x1, y1 = box
    draw.rounded_rectangle([x0, y0, x1, y1], radius=22 * s, fill=WHITE)
    # Air outlet
    draw.rounded_rectangle([x0 + 22 * s, y1 - 30 * s, x1 - 22 * s, y1 - 18 * s], radius=6 * s, fill=color_slot)
    # Status led
    draw.ellipse([x1 - 34 * s, y0 + 16 * s, x1 - 22 * s, y0 + 28 * s], fill=color_slot)
    # Airflow
    wave_x1 = x1 - (70 * s if with_droplet else 30 * s)
    for i in range(3):
        draw_wave(draw, x0 + 30 * s, wave_x1, y1 + (34 + i * 30) * s, 7 * s, 2, 11 * s)
    if with_droplet:
        draw_droplet(draw, x1 - 30 * s, y1 + 92 * s, 20 * s)


def make_plugin_icon(template_icon):
    s = SCALE
    mask = Image.open(template_icon).convert('RGBA').split()[3].resize((WIDTH * s, HEIGHT * s), Image.LANCZOS)
    background = gradient((WIDTH * s, HEIGHT * s), TOP_COLOR, BOTTOM_COLOR)
    pictogram = Image.new('RGBA', (WIDTH * s, HEIGHT * s), (0, 0, 0, 0))
    draw = ImageDraw.Draw(pictogram)
    draw_ac_unit(draw, (52 * s, 62 * s, 257 * s, 140 * s), TOP_COLOR + (255,), True)
    shadow = pictogram.split()[3].filter(ImageFilter.GaussianBlur(6 * s))
    shadow_layer = Image.new('RGBA', pictogram.size, (0, 0, 0, 0))
    shadow_layer.putalpha(shadow.point(lambda a: a * 0.35))
    shadow_layer = shadow_layer.transform(shadow_layer.size, Image.AFFINE, (1, 0, -3 * s, 0, 1, -4 * s))
    icon = Image.alpha_composite(background, shadow_layer)
    icon = Image.alpha_composite(icon, pictogram)
    icon.putalpha(mask)
    icon = icon.resize((WIDTH, HEIGHT), Image.LANCZOS)
    icon.save(PLUGIN_DIR / 'plugin_info' / 'mideamsmart_icon.png', optimize=True)


def make_device_image(name):
    """Square device image shown on the equipment card."""
    s = SCALE
    size = SQUARE * s
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    disc = Image.new('L', (size, size), 0)
    ImageDraw.Draw(disc).ellipse([0, 0, size - 1, size - 1], fill=255)
    bg = gradient((size, size), TOP_COLOR, BOTTOM_COLOR)
    img.paste(bg, (0, 0), disc)
    draw = ImageDraw.Draw(img)
    slot = TOP_COLOR + (255,)
    if name == 'a1':
        # Free-standing dehumidifier with its water tank
        draw.rounded_rectangle([96 * s, 60 * s, 213 * s, 250 * s], radius=20 * s, fill=WHITE)
        draw.rounded_rectangle([114 * s, 80 * s, 195 * s, 92 * s], radius=6 * s, fill=slot)
        draw.rounded_rectangle([114 * s, 168 * s, 195 * s, 232 * s], radius=10 * s, fill=slot)
        draw_droplet(draw, 154.5 * s, 212 * s, 12 * s)
    elif name == 'cc':
        # Ceiling cassette: square panel with four air outlets
        draw.rounded_rectangle([70 * s, 70 * s, 239 * s, 239 * s], radius=18 * s, fill=WHITE)
        draw.rounded_rectangle([100 * s, 86 * s, 209 * s, 98 * s], radius=6 * s, fill=slot)
        draw.rounded_rectangle([100 * s, 211 * s, 209 * s, 223 * s], radius=6 * s, fill=slot)
        draw.rounded_rectangle([86 * s, 100 * s, 98 * s, 209 * s], radius=6 * s, fill=slot)
        draw.rounded_rectangle([211 * s, 100 * s, 223 * s, 209 * s], radius=6 * s, fill=slot)
        draw.rounded_rectangle([118 * s, 118 * s, 191 * s, 191 * s], radius=10 * s, outline=slot, width=6 * s)
    elif name == 'scheduler':
        # Calendar with a clock: the schedule equipment
        draw.rounded_rectangle([72 * s, 82 * s, 237 * s, 232 * s], radius=18 * s, fill=WHITE)
        draw.rectangle([72 * s, 112 * s, 237 * s, 120 * s], fill=slot)
        for x in (110, 199):
            draw.rounded_rectangle([(x - 7) * s, 66 * s, (x + 7) * s, 98 * s], radius=7 * s, fill=WHITE, outline=slot, width=4 * s)
        for row in range(2):
            for column in range(3):
                x, y = 96 + column * 34, 138 + row * 30
                draw.rounded_rectangle([x * s, y * s, (x + 18) * s, (y + 16) * s], radius=4 * s, fill=slot)
        cx, cy, r = 212 * s, 214 * s, 46 * s
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=WHITE, outline=slot, width=8 * s)
        draw.line([(cx, cy), (cx, cy - 28 * s)], fill=slot, width=8 * s)
        draw.line([(cx, cy), (cx + 22 * s, cy)], fill=slot, width=8 * s)
    else:
        draw_ac_unit(draw, (52 * s, 82 * s, 257 * s, 160 * s), slot, False)
    img = img.resize((SQUARE, SQUARE), Image.LANCZOS)
    out = PLUGIN_DIR / 'desktop' / 'img'
    out.mkdir(parents=True, exist_ok=True)
    img.save(out / f'{name}.png', optimize=True)


if __name__ == '__main__':
    make_plugin_icon(sys.argv[1])
    for device_type in ('ac', 'cc', 'a1', 'scheduler'):
        make_device_image(device_type)
