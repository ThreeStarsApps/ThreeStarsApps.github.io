"""Render the site's share image from its existing app icons (optional asset tool)."""
import argparse
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--regular-font", type=Path, default=Path("C:/Windows/Fonts/segoeui.ttf"))
    parser.add_argument("--bold-font", type=Path, default=Path("C:/Windows/Fonts/segoeuib.ttf"))
    parser.add_argument("--output", type=Path, default=ROOT / "assets/images/social-card.png")
    args = parser.parse_args()
    if not args.regular_font.is_file() or not args.bold_font.is_file():
        parser.error("Segoe UI fonts were not found. Supply --regular-font and --bold-font paths.")

    def bold(size):
        return ImageFont.truetype(str(args.bold_font), size)

    def regular(size):
        return ImageFont.truetype(str(args.regular_font), size)

    image = Image.new("RGB", (1200, 630), "#f5f5f7")
    draw = ImageDraw.Draw(image)
    draw.text((78, 64), "THREESTARS APPS", font=bold(21), fill="#65676d")
    draw.text((72, 131), "Your buttons.", font=bold(81), fill="#202124")
    draw.text((72, 224), "Your rules.", font=bold(81), fill="#202124")
    draw.text((78, 356), "Apps built to customize hardware and", font=regular(29), fill="#65676d")
    draw.text((78, 400), "S Pen buttons on your Android devices.", font=regular(29), fill="#65676d")
    draw.text((78, 536), "threestarsapps.com", font=regular(24), fill="#202124")
    for app, y in (("keystar", 145), ("penstar", 340)):
        with Image.open(ROOT / f"assets/images/{app}_icon.png") as source:
            tile = source.convert("RGB").resize((135, 135), Image.Resampling.LANCZOS)
            mask = Image.new("L", tile.size)
            ImageDraw.Draw(mask).rounded_rectangle((0, 0, 135, 135), radius=30, fill=255)
            image.paste(tile, (940, y), mask)
        draw.text((940 + 135 / 2, y + 143), "KeyStar" if app == "keystar" else "PenStar", font=bold(22), fill="#202124", anchor="ma")
    destination = args.output.resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name("social-card.new.png")
    image.save(temporary, optimize=True)
    temporary.replace(destination)
    print(f"Created {destination.name}: {destination.stat().st_size:,} bytes")


if __name__ == "__main__":
    main()
