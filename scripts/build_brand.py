"""Render SEA's filled heart-wave identity. Pillow is needed only for PNG builds."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
BACKGROUND = "#083B61"
BLUE = "#238BB4"
CYAN = "#72C3CA"
PEACH = "#F2CB99"

HEART_START = (128, 201)
HEART_CURVES = [((112, 174), (99, 154), (78, 141)),
                ((54, 126), (42, 104), (48, 80)),
                ((54, 54), (78, 39), (102, 47)),
                ((115, 51), (124, 60), (128, 70)),
                ((132, 60), (141, 51), (154, 47)),
                ((178, 39), (202, 54), (208, 80)),
                ((214, 104), (202, 126), (178, 141)),
                ((157, 154), (144, 174), (128, 201))]
WAVE_START = (45, 132)
WAVE_CURVES = [((72, 105), (98, 108), (124, 139)),
               ((149, 169), (176, 144), (211, 124))]


def curve_points(start, curves, steps=96):
    result = [start]
    p0 = start
    for p1, p2, p3 in curves:
        for step in range(1, steps + 1):
            t = step / steps
            result.append(tuple((1-t)**3*p0[i] + 3*(1-t)**2*t*p1[i] +
                                3*(1-t)*t*t*p2[i] + t**3*p3[i] for i in (0, 1)))
        p0 = p3
    return result


def icon(size):
    factor = size * 4 / 256
    canvas_size = size * 4
    image = Image.new("RGBA", (canvas_size, canvas_size), BACKGROUND)
    mask = Image.new("L", image.size, 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.polygon([(x * factor, y * factor)
                       for x, y in curve_points(HEART_START, HEART_CURVES)], fill=255)
    wave = [(x * factor, y * factor) for x, y in curve_points(WAVE_START, WAVE_CURVES)]
    cut_radius = 19 * factor / 2
    for x, y in wave:
        mask_draw.ellipse((x-cut_radius, y-cut_radius, x+cut_radius, y+cut_radius), fill=0)
    gradient = Image.new("RGBA", image.size)
    pixels = gradient.load()
    top, bottom = (35, 139, 180), (114, 195, 202)
    for y in range(canvas_size):
        ratio = y / max(1, canvas_size - 1)
        color = tuple(round(top[i] * (1-ratio) + bottom[i] * ratio) for i in range(3)) + (255,)
        for x in range(canvas_size):
            pixels[x, y] = color
    image.alpha_composite(Image.composite(gradient, Image.new("RGBA", image.size), mask))
    draw = ImageDraw.Draw(image)
    accent_radius = 5 * factor / 2
    for x, y in wave:
        draw.ellipse((x-accent_radius, y-accent_radius, x+accent_radius, y+accent_radius), fill=PEACH)
    return image.resize((size, size), Image.Resampling.LANCZOS)


def font(size):
    for path in ("C:/Windows/Fonts/segoeui.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default(size=size)


def main():
    ASSETS.mkdir(exist_ok=True)
    heart = "M128 201 " + " ".join(
        "C" + " ".join(str(n) for point in curve for n in point) for curve in HEART_CURVES) + " Z"
    wave = f"M{WAVE_START[0]} {WAVE_START[1]} " + " ".join(
        "C" + " ".join(str(n) for point in curve for n in point) for curve in WAVE_CURVES)
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256" viewBox="0 0 256 256" role="img" aria-labelledby="title">'
        '<title id="title">SEA heart wave</title><defs><linearGradient id="ocean" x1="0" y1="0" x2="0" y2="1">'
        f'<stop stop-color="{BLUE}"/><stop offset="1" stop-color="{CYAN}"/></linearGradient></defs>'
        f'<rect width="256" height="256" rx="56" fill="{BACKGROUND}"/>'
        f'<path d="{heart}" fill="url(#ocean)"/>'
        f'<path d="{wave}" fill="none" stroke="{BACKGROUND}" stroke-width="19" stroke-linecap="round"/>'
        f'<path d="{wave}" fill="none" stroke="{PEACH}" stroke-width="5" stroke-linecap="round"/>'
        '</svg>\n')
    (ASSETS / "sea-icon.svg").write_text(svg, encoding="utf-8")
    icon(512).save(ASSETS / "sea-icon.png")
    card = Image.new("RGB", (1280, 640), BACKGROUND)
    mark = icon(256)
    card.paste(mark, (100, 132), mark)
    draw = ImageDraw.Draw(card)
    draw.text((416, 180), "SEA", font=font(104), fill="#F0FDFA")
    draw.text((423, 316), "Learn. Remember. Give back.", font=font(32), fill=CYAN)
    draw.text((113, 530), "SELF-EVOLVING AGENT", font=font(21), fill="#A5C9D7")
    card.save(ASSETS / "sea-social.png")


if __name__ == "__main__":
    main()
