#!/usr/bin/env python
"""Генератор иконок приложения Kuji (Задача 6).

Создаёт в assets/:
  * icon.svg            – векторная монограмма «Qj» (рукописный SVG,
                          геометрия 1:1 с eta/ui/icons.py::draw_qj);
  * icon_16/24/32/48/64/128/256.png – растровые копии (QPainter);
  * icon.ico            – сборка МИНИМАЛЬНЫМ самописным энкодером
                          (icondir + BMP-entries 32bpp + PNG-entry 256),
                          без внешних pip-пакетов.

Запуск:  runtime\\python\\python.exe tools_make_icons.py
"""

from __future__ import annotations

import os
import struct
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from eta.ui.icons import ASSETS_DIR  # noqa: E402

SVG = """<?xml version="1.0" encoding="UTF-8"?>
<!-- Kuji (Куджи) – монограмма приложения. Swiss Utilitarian: плоско,
     1px-элементы, без градиентов/теней; Q – TEXT_PRIMARY, j – ACCENT. -->
<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256" viewBox="0 0 256 256">
  <rect width="256" height="256" fill="#FFFFFF"/>
  <g stroke-linecap="butt" stroke-linejoin="miter" fill="none">
    <!-- «Q»: кольцо + диагональная ножка -->
    <circle cx="104" cy="112" r="66" stroke="#0F172A" stroke-width="20"/>
    <line x1="150" y1="158" x2="196" y2="206" stroke="#0F172A" stroke-width="20"/>
    <!-- «j»: подстрочная, крючок пересекает ножку Q -->
    <line x1="196" y1="66" x2="196" y2="170" stroke="#2563EB" stroke-width="20"/>
    <path d="M 196 170 Q 198 204 156 196" stroke="#2563EB" stroke-width="20"/>
  </g>
  <circle cx="196" cy="34" r="17" fill="#2563EB"/>
</svg>
"""


def make_pngs(sizes: list[int]) -> None:
    from eta.ui.icons import qj_pixmap
    for px in sizes:
        img = qj_pixmap(px)
        img.save(str(ASSETS_DIR / f"icon_{px}.png"))
        print(f"icon_{px}.png – {img.width()}x{img.height()}")


def _bmp_entry(img) -> bytes:
    """Запись ICO в формате BITMAPINFOHEADER + BGRA-пиксели + AND-маска."""
    w, h = img.width(), img.height()
    and_row = ((w + 31) // 32) * 4
    pixel_data = bytearray()
    mask = bytes(and_row * h)           # нулевая маска: прозрачность по альфе
    for y in range(h - 1, -1, -1):      # снизу вверх
        for x in range(w):
            px = img.pixel(x, y)
            b, g, r, a = px & 255, (px >> 8) & 255, (px >> 16) & 255, (px >> 24) & 255
            pixel_data += bytes((b, g, r, a))
    header = struct.pack(
        "<IiiHHIIiiII", 40, w, h * 2, 1, 32, 0,
        40 + len(pixel_data) + len(mask), 0, 0, 0, 0)
    return header + bytes(pixel_data) + mask


def make_ico(bmp_sizes: list[int], png_size: int = 256) -> None:
    entries: list[tuple[bytes, int, int]] = []   # (data, width, height)
    from eta.ui.icons import qj_pixmap
    for px in bmp_sizes:
        img = qj_pixmap(px).convertToFormat(
            __import__("PySide6.QtGui", fromlist=["QImage"]).QImage.Format.Format_ARGB32)
        entries.append((_bmp_entry(img), px, px))
    png_path = ASSETS_DIR / f"icon_{png_size}.png"
    entries.append((png_path.read_bytes(), png_size, png_size))

    count = len(entries)
    header = struct.pack("<HHH", 0, 1, count)
    dir_bytes = bytearray()
    offset = 6 + 16 * count
    for data, w, h in entries:
        dir_bytes += struct.pack("<BBBBHHII", 0 if w >= 256 else w,
                                 0 if h >= 256 else h, 0, 0, 1, 32,
                                 len(data), offset)
        offset += len(data)
    out = ASSETS_DIR / "icon.ico"
    out.write_bytes(header + dir_bytes + b"".join(d for d, _, _ in entries))
    print(f"icon.ico – {count} записей, {out.stat().st_size} байт")


def main() -> int:
    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication(sys.argv)
    ASSETS_DIR.mkdir(exist_ok=True)
    (ASSETS_DIR / "icon.svg").write_text(SVG, encoding="utf-8")
    print("icon.svg")
    make_pngs([16, 24, 32, 48, 64, 128, 256])
    make_ico([16, 24, 32, 48])
    # контроль: ICO читается и отдаёт все размеры
    icon = QIcon(str(ASSETS_DIR / "icon.ico"))
    sizes = sorted({(s.width(), s.height()) for s in icon.availableSizes()})
    print("ICO availableSizes:", sizes)
    assert icon.isNull() is False
    assert (16, 16) in sizes and (48, 48) in sizes, sizes
    print("ICONS OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
