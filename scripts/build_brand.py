"""Render the original SEA sea-surface mark. Pillow is needed only for PNG builds."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
BACKGROUND = "#083B61"
FOREGROUND = "#72C3CA"
# Open, flowing wave lines; no closed curl or claw-like silhouette.
WAVES = [
    ((46, 91), [((76, 65), (105, 117), (135, 91)), ((164, 65), (188, 75), (210, 91))], "#238BB4", 14),
    ((46, 130), [((76, 104), (105, 156), (135, 130)), ((164, 104), (188, 114), (210, 130))], FOREGROUND, 14),
    ((63, 169), [((88, 153), (109, 188), (135, 169)), ((155, 153), (170, 154), (190, 164))], "#F2CB99", 10),
]


def points(start, curves):
    result = [start]
    p0 = start
    for p1, p2, p3 in curves:
        for step in range(1, 97):
            t = step / 96
            result.append(tuple((1-t)**3*p0[i] + 3*(1-t)**2*t*p1[i] +
                                3*(1-t)*t*t*p2[i] + t**3*p3[i] for i in (0, 1)))
        p0 = p3
    return result


def icon(size):
    scale = size * 4 / 256
    image = Image.new("RGBA", (size * 4, size * 4))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((0, 0, size*4-1, size*4-1), radius=56*scale, fill=BACKGROUND)
    for start, curves, color, width in WAVES:
        coords = [(x*scale, y*scale) for x, y in points(start, curves)]
        draw.line(coords, fill=color, width=round(width*scale), joint="curve")
        radius = width*scale/2
        for x, y in coords:
            draw.ellipse((x-radius, y-radius, x+radius, y+radius), fill=color)
    return image.resize((size, size), Image.Resampling.LANCZOS)


def font(size):
    for path in ("C:/Windows/Fonts/segoeui.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default(size=size)


def main():
    ASSETS.mkdir(exist_ok=True)
    paths = []
    for start, curves, color, width in WAVES:
        path = f"M{start[0]} {start[1]} " + " ".join(
            "C" + " ".join(str(n) for point in curve for n in point) for curve in curves)
        paths.append(f'<path d="{path}" fill="none" stroke="{color}" stroke-width="{width}" stroke-linecap="round"/>')
    (ASSETS / "sea-icon.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256" viewBox="0 0 256 256" role="img" aria-labelledby="title">'
        '<title id="title">SEA ocean ripples</title>'
        f'<rect width="256" height="256" rx="56" fill="{BACKGROUND}"/>' + ''.join(paths) + '</svg>\n', encoding="utf-8")
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
