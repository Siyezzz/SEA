"""Render SEA's original vector wave mark and PNG exports. Requires Pillow (build only)."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
BACKGROUND = "#082F49"
FOREGROUND = "#5EEAD4"
START = (43, 157)
CURVES = [((80, 164), (85, 111), (121, 97)),
          ((153, 84), (183, 100), (187, 126)),
          ((167, 108), (148, 119), (151, 137)),
          ((154, 157), (179, 164), (213, 150)),
          ((204, 184), (177, 204), (139, 204)),
          ((97, 204), (64, 185), START)]


def wave_points():
    points = [START]
    p0 = START
    for p1, p2, p3 in CURVES:
        for step in range(1, 65):
            t = step / 64
            points.append(tuple((1-t)**3*p0[i] + 3*(1-t)**2*t*p1[i] +
                                3*(1-t)*t*t*p2[i] + t**3*p3[i] for i in (0, 1)))
        p0 = p3
    return points


def icon(size):
    scale = size * 4 / 256
    image = Image.new("RGBA", (size * 4, size * 4))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((0, 0, size*4-1, size*4-1), radius=56*scale, fill=BACKGROUND)
    draw.polygon([(x*scale, (y-13)*scale) for x, y in wave_points()], fill=FOREGROUND)
    return image.resize((size, size), Image.Resampling.LANCZOS)


def font(size):
    for path in ("C:/Windows/Fonts/segoeui.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default(size=size)


def main():
    ASSETS.mkdir(exist_ok=True)
    path = f"M{START[0]} {START[1]} " + " ".join(
        "C" + " ".join(str(n) for point in curve for n in point) for curve in CURVES) + " Z"
    (ASSETS / "sea-icon.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256" viewBox="0 0 256 256" role="img" aria-labelledby="title">'
        '<title id="title">SEA wave</title>'
        f'<rect width="256" height="256" rx="56" fill="{BACKGROUND}"/>'
        f'<path d="{path}" transform="translate(0 -13)" fill="{FOREGROUND}"/></svg>\n', encoding="utf-8")
    icon(512).save(ASSETS / "sea-icon.png")
    card = Image.new("RGB", (1280, 640), BACKGROUND)
    mark = icon(256)
    card.paste(mark, (100, 132), mark)
    draw = ImageDraw.Draw(card)
    draw.text((416, 180), "SEA", font=font(104), fill="#F0FDFA")
    draw.text((423, 316), "Learn. Remember. Give back.", font=font(32), fill=FOREGROUND)
    draw.text((113, 530), "SELF-EVOLVING AGENT", font=font(21), fill="#A5C9D7")
    card.save(ASSETS / "sea-social.png")


if __name__ == "__main__":
    main()
