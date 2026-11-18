#!/usr/bin/env python3
"""
preview.py — Render aproximado del .pptx a PNG para revisar la maquetación
sin necesidad de PowerPoint ni LibreOffice.

Lee el propio .pptx (posiciones, colores, fuentes e imágenes) y dibuja con Pillow.
No es PowerPoint, pero sirve para detectar solapes, texto cortado y colores mal puestos.

Uso: python presentacion/preview.py
"""

import io
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from pptx import Presentation

DIR = Path(__file__).parent
DECK_CANDIDATES = sorted(
    (p for p in DIR.glob("*.pptx") if not p.name.startswith("~$")),
    key=lambda p: p.stat().st_mtime,
)
DECK = DECK_CANDIDATES[-1]
OUT = DIR / "preview"
DPI = 96
EMU_IN = 914400

FONTS = {
    (False, False): "C:/Windows/Fonts/georgia.ttf",
    (True, False): "C:/Windows/Fonts/georgiab.ttf",
    (False, True): "C:/Windows/Fonts/georgiai.ttf",
    (True, True): "C:/Windows/Fonts/georgiab.ttf",
}


def px(inches):
    return int(round(inches * DPI))


def color_of(fill_or_line, default):
    try:
        rgb = fill_or_line.fore_color.rgb
        return (rgb[0], rgb[1], rgb[2])
    except Exception:  # noqa: BLE001
        return default


def font_for(run, size_px):
    key = (bool(run.font.bold), bool(run.font.italic))
    path = FONTS.get(key, FONTS[(False, False)])
    try:
        return ImageFont.truetype(path, size_px)
    except Exception:  # noqa: BLE001
        return ImageFont.load_default()


def draw_text(draw, tf, x, y, w, h):
    cy = y
    for p in tf.paragraphs:
        runs = p.runs
        if not runs:
            cy += 14
            continue
        r0 = runs[0]
        size_pt = r0.font.size.pt if r0.font.size else 18
        size_px = int(round(size_pt * DPI / 72))
        font = font_for(r0, size_px)
        col = color_of(r0.font.color, (242, 234, 217))
        linea = "".join(x.text for x in runs)

        palabras, lineas, cur = linea.split(), [], ""
        for word in palabras:
            prueba = (cur + " " + word).strip()
            if draw.textlength(prueba, font=font) <= w:
                cur = prueba
            else:
                if cur:
                    lineas.append(cur)
                cur = word
        if cur:
            lineas.append(cur)

        ls = p.line_spacing if isinstance(p.line_spacing, float) else 1.15
        alto = size_px * ls
        for ln in lineas:
            tw = draw.textlength(ln, font=font)
            if p.alignment is not None and "CENTER" in str(p.alignment):
                draw.text((x + (w - tw) / 2, cy), ln, font=font, fill=col)
            else:
                draw.text((x, cy), ln, font=font, fill=col)
            cy += alto


def render_slide(slide, w_px, h_px, bg):
    img = Image.new("RGB", (w_px, h_px), bg)
    draw = ImageDraw.Draw(img)

    for sh in slide.shapes:
        x, y = px(sh.left / EMU_IN), px(sh.top / EMU_IN)
        w, h = px(sh.width / EMU_IN), px(sh.height / EMU_IN)

        if sh.shape_type == 13:  # imagen
            pic = Image.open(io.BytesIO(sh.image.blob)).convert("RGB")
            img.paste(pic.resize((max(w, 1), max(h, 1)), Image.LANCZOS), (x, y))
            continue

        if sh.shape_type is not None and "TEXT_BOX" not in str(sh.shape_type):
            fill = color_of(sh.fill, None)
            try:
                sin_linea = sh.line.fill.type is None or str(sh.line.fill.type).startswith("BACKGROUND")
            except Exception:  # noqa: BLE001
                sin_linea = True
            line = None if sin_linea else color_of(sh.line.color, None)
            es_oval = sh.shape_type == 9  # MSO_SHAPE.OVAL
            if fill or line:
                if es_oval:
                    draw.ellipse([x, y, x + w, y + h], fill=fill, outline=line, width=2)
                else:
                    draw.rectangle([x, y, x + w, y + h], fill=fill, outline=line, width=2)

        if sh.has_text_frame and sh.text_frame.text.strip():
            draw_text(draw, sh.text_frame, x, y, w, h)

    return img


def main():
    prs = Presentation(str(DECK))
    OUT.mkdir(exist_ok=True)
    w_px = px(prs.slide_width / EMU_IN)
    h_px = px(prs.slide_height / EMU_IN)

    for i, slide in enumerate(prs.slides, start=1):
        try:
            bg = color_of(slide.background.fill, (14, 12, 10))
        except Exception:  # noqa: BLE001
            bg = (14, 12, 10)
        img = render_slide(slide, w_px, h_px, bg)
        dest = OUT / f"slide_{i:02d}.png"
        img.save(dest)
        print(f"  {dest.name}")


if __name__ == "__main__":
    main()
