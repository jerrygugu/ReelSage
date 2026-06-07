"""从项目根目录 rr.png 生成各尺寸 PNG 与 app.ico。"""

from __future__ import annotations

from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "rr.png"
OUT_DIR = ROOT / "cinescribe" / "assets" / "icons"
SIZES = (16, 20, 32, 48, 64, 88, 128, 256)
ICO_SIZES = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]


def main() -> None:
    if not SRC.is_file():
        raise SystemExit(f"未找到源图标: {SRC}")

    img = Image.open(SRC).convert("RGBA")
    side = max(img.size)
    if img.size[0] != img.size[1]:
        canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
        ox = (side - img.size[0]) // 2
        oy = (side - img.size[1]) // 2
        canvas.paste(img, (ox, oy), img)
        img = canvas

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for size in SIZES:
        out = img.resize((size, size), Image.Resampling.LANCZOS)
        out.save(OUT_DIR / f"icon_{size}.png")
        print(f"icon_{size}.png")

    img.save(OUT_DIR / "app.ico", format="ICO", sizes=ICO_SIZES)
    img.save(ROOT / "app.ico", format="ICO", sizes=ICO_SIZES)
    print("app.ico")


if __name__ == "__main__":
    main()
