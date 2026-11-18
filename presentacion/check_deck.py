#!/usr/bin/env python3
"""Comprueba que ningún texto se salga de su caja y que nada se solape con fotos."""

from pathlib import Path

from PIL import ImageFont
from pptx import Presentation
from pptx.util import Emu

DIR = Path(__file__).parent
DECK_CANDIDATES = sorted(
    (p for p in DIR.glob("*.pptx") if not p.name.startswith("~$")),
    key=lambda p: p.stat().st_mtime,
)
DECK = DECK_CANDIDATES[-1]
FONTS = {
    (False, False): "C:/Windows/Fonts/georgia.ttf",
    (True, False): "C:/Windows/Fonts/georgiab.ttf",
    (False, True): "C:/Windows/Fonts/georgiai.ttf",
    (True, True): "C:/Windows/Fonts/georgiab.ttf",
}
EMU_IN = 914400


def inches(v):
    return v / EMU_IN


def measure(shape):
    """Devuelve (alto_necesario_in, alto_caja_in, ancho_in, texto)."""
    tf = shape.text_frame
    w_in = inches(shape.width)
    inner_w = w_in - 0.0  # margins puestos a 0 al crear
    total_h = 0.0
    texto = []
    for p in tf.paragraphs:
        runs = p.runs
        if not runs:
            total_h += 0.14
            continue
        r = runs[0]
        size = r.font.size.pt if r.font.size else 18
        px = int(round(size))  # 1pt = 1px a 72 dpi
        key = (bool(r.font.bold), bool(r.font.italic))
        path = FONTS.get(key, FONTS[(False, False)])
        font = ImageFont.truetype(path, px)
        line = "".join(x.text for x in runs)
        texto.append(line)
        # ancho útil en px (1in = 72pt)
        max_px = inner_w * 72
        lineas = 1
        cur = ""
        for word in line.split():
            prueba = (cur + " " + word).strip()
            if font.getlength(prueba) <= max_px:
                cur = prueba
            else:
                lineas += 1
                cur = word
        ls = p.line_spacing if isinstance(p.line_spacing, float) else 1.15
        total_h += lineas * (size * ls) / 72
    return total_h, inches(shape.height), w_in, " | ".join(texto)


def main():
    prs = Presentation(str(DECK))
    problemas = 0
    for i, slide in enumerate(prs.slides, start=1):
        fotos = [(inches(s.left), inches(s.top), inches(s.width), inches(s.height))
                 for s in slide.shapes if s.shape_type == 13]
        for sh in slide.shapes:
            if sh.shape_type == 13 or not sh.has_text_frame:
                continue
            if not sh.text_frame.text.strip():
                continue
            need, box, w, txt = measure(sh)
            if need > box * 1.02:
                problemas += 1
                print(f"⚠ slide {i}: texto más alto que su caja "
                      f"({need:.2f}in > {box:.2f}in) · {txt[:70]}")
            # solape con foto
            x, y = inches(sh.left), inches(sh.top)
            for fx, fy, fw, fh in fotos:
                if x < fx + fw and x + w > fx and y < fy + fh and y + box > fy:
                    problemas += 1
                    print(f"⚠ slide {i}: texto encima de la foto · {txt[:60]}")
    print(f"\n{'✅ sin problemas de maquetación' if problemas == 0 else f'{problemas} avisos'}")
    print(f"diapositivas: {len(prs.slides)}")


if __name__ == "__main__":
    main()
