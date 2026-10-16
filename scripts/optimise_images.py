"""Create responsive WebP copies from the original screenshots (optional asset tool)."""
import argparse
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "assets/images")
    destination_dir = parser.parse_args().output_dir.resolve()
    destination_dir.mkdir(parents=True, exist_ok=True)
    original_bytes = 0
    web_bytes = 0
    for source in sorted((ROOT / "assets/images").glob("*_ss_*.png")):
        original_bytes += source.stat().st_size
        with Image.open(source) as original:
            for width in (360, 720):
                image = original.convert("RGB")
                image.thumbnail((width, 2000), Image.Resampling.LANCZOS)
                destination = destination_dir / f"{source.stem}-{width}.webp"
                image.save(destination, "WEBP", quality=84, method=6)
                if width == 720:
                    web_bytes += destination.stat().st_size
    print(f"Screenshot originals: {original_bytes:,} bytes; 720px web copies: {web_bytes:,} bytes")


if __name__ == "__main__":
    main()
