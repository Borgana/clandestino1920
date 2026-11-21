#!/usr/bin/env python3
"""
carousel_agent.py — Genera un carrusel de Instagram para un cóctel de la carta.

Qué hace:
  1. Lee el cóctel de data/carta.json (nombre, precio, ingredientes, alérgenos).
  2. Pide al LLM (Groq) la estructura del carrusel: título y texto de cada slide.
  3. Genera una imagen vertical 4:5 por slide con Gemini (nano banana).
  4. Le escribe el texto encima con Pillow (tipografía serif, estilo speakeasy).
  5. Guarda todo en carruseles/<slug>_<fecha>/ + caption.txt + .zip

Uso por consola:
    python carousel_agent.py "Old Fashioned"
    python carousel_agent.py "Al Capone Sour" --slides 6 --objetivo vender
"""

import json
import os
import re
import sys
import time
import zipfile
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from creative_agent import build_context_str, search_context
from image_client import generate_image
from quality_agent import groq, LLM_MODEL

ROOT = Path(__file__).parent
CARTA_PATH = ROOT / "data" / "carta.json"
OUT_ROOT = ROOT / "carruseles"
ASSETS = ROOT / "assets"

W, H = 1080, 1350          # 4:5, el formato de carrusel de Instagram
MARGIN = 72
FONT_DIR = Path("C:/Windows/Fonts")
F_TITLE = FONT_DIR / "georgiab.ttf"   # Georgia Bold
F_BODY = FONT_DIR / "georgia.ttf"     # Georgia
F_ITALIC = FONT_DIR / "georgiai.ttf"

SLIDES_TEMPLATE = """CONTEXTO DE LA CARTA Y DEL BAR (usa SOLO esto):
{context}

FICHA DEL CÓCTEL:
- Nombre: {nombre}
- Precio: {precio}
- Ingredientes: {ingredientes}
- Alérgenos: {alergenos}
- Descripción de la carta: {descripcion}

TAREA: diseña un carrusel de Instagram de {n} slides para este cóctel, objetivo "{objetivo}".
Estructura: slide 1 = gancho que pare el scroll; slides del medio = historia, ingredientes, ritual;
último slide = llamada a la acción suave.

Devuelve SOLO este JSON:
{{
  "slides": [
    {{
      "titulo": "máximo 5 palabras, sin comillas ni punto final",
      "texto": "máximo 18 palabras, una o dos frases",
      "prompt_imagen": "descripción visual en español del plano: qué se ve, ángulo y luz. SIEMPRE dentro del bar (barra, botellas, copas, manos del barman). Nada de barcos, mares, mapas ni metáforas literales. Sin texto en la imagen."
    }}
  ],
  "caption": "pie de foto de Instagram: 2-3 párrafos cortos con la voz de Clandestino, con CTA y sin hashtags",
  "hashtags": ["#clandestino1920", "..."]
}}
Exactamente {n} slides."""


def load_carta() -> list[dict]:
    return json.loads(CARTA_PATH.read_text(encoding="utf-8"))


def find_item(nombre: str) -> dict:
    items = load_carta()
    objetivo = nombre.strip().lower()
    for it in items:
        if it["nombre"].strip().lower() == objetivo:
            return it
    for it in items:  # coincidencia parcial
        if objetivo in it["nombre"].strip().lower():
            return it
    raise SystemExit(f"No encuentro '{nombre}' en la carta. Revisa data/carta.json")


def mensaje_red(error: Exception | str, servicio: str = "el servicio") -> str:
    """
    Traduce errores técnicos de red a algo que se entienda en el panel.
    getaddrinfo / DNS / timeout / 429 son los cuatro casos que aparecen de verdad.
    """
    texto = str(error)
    bajo = texto.lower()
    if "getaddrinfo" in bajo or "name resolution" in bajo or "nameresolution" in bajo:
        return (f"No hay conexión con {servicio}: el DNS no resuelve el dominio. "
                f"Comprueba internet y vuelve a intentarlo (el error fue «getaddrinfo failed»).")
    if "connection" in bajo or "timeout" in bajo or "timed out" in bajo:
        return (f"Se ha cortado la conexión con {servicio}. Revisa la red y reinténtalo.")
    if "429" in texto or "rate limit" in bajo or "quota" in bajo:
        return (f"{servicio} ha alcanzado su límite de peticiones. "
                f"Espera un minuto (o al día siguiente, si es la cuota diaria) y reinténtalo.")
    if "insufficient_quota" in bajo or "credit" in bajo:
        return f"{servicio} no tiene saldo o créditos disponibles."
    return f"Error en {servicio}: {texto}"


def _json_loose(txt: str) -> dict:
    """Parsea JSON aunque venga con ```json ... ``` o texto alrededor."""
    txt = (txt or "").strip()
    txt = re.sub(r"^```(?:json)?\s*|\s*```$", "", txt, flags=re.S).strip()
    try:
        return json.loads(txt)
    except json.JSONDecodeError:
        pass
    i, j = txt.find("{"), txt.rfind("}")
    if i != -1 and j > i:
        return json.loads(txt[i:j + 1])
    raise ValueError("La respuesta no contiene JSON")


def _llm_json(system: str, prompt: str, max_tokens: int = 2000) -> dict:
    """Pide JSON al LLM con dos intentos: modo JSON estricto y, si falla, texto libre."""
    intentos = [
        {"response_format": {"type": "json_object"}, "sufijo": ""},
        {"response_format": None, "sufijo": "\n\nDevuelve SOLO el JSON, sin explicaciones."},
        {"response_format": {"type": "json_object"}, "sufijo": ""},
    ]
    ultimo = None
    for n, cfg in enumerate(intentos):
        try:
            kwargs = dict(
                model=LLM_MODEL,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt + cfg["sufijo"]},
                ],
                temperature=0.6,
                max_tokens=max_tokens,
            )
            if cfg["response_format"]:
                kwargs["response_format"] = cfg["response_format"]
            completion = groq.chat.completions.create(**kwargs)
            return _json_loose(completion.choices[0].message.content)
        except Exception as e:  # noqa: BLE001
            ultimo = e
            if n < len(intentos) - 1:
                espera = 2 * (n + 1)
                print(f"  ⚠ el modelo no respondió ({type(e).__name__}), reintento en {espera}s...")
                time.sleep(espera)
    raise RuntimeError(mensaje_red(ultimo, "el modelo de texto (Groq)"))


def build_carousel(tema: str, objetivo: str = "vender", n_slides: int = 5,
                   progress=None) -> dict:
    """Devuelve la estructura del carrusel (slides + caption)."""

    def log(msg: str, stage: str | None = None, **extra):
        if progress:
            progress(msg, stage, **extra)
        else:
            print(msg)

    item = find_item(tema)
    ctx = search_context(f"{item['nombre']} {' '.join(item.get('ingredientes') or [])}", top_k=6)
    context_str = build_context_str(ctx)[:2500]
    if not context_str:
        context_str = ("(No hay contexto recuperado del local en este momento. "
                       "Usa SOLO la ficha del cóctel que viene abajo.)")

    prompt = SLIDES_TEMPLATE.format(
        context=context_str,
        nombre=item["nombre"],
        precio=f"{item['precio']}€" if item.get("precio") else "consultar",
        ingredientes=", ".join(item.get("ingredientes") or []) or "no especificados",
        alergenos=", ".join(item.get("alergenos") or []) or "ninguno declarado",
        descripcion=item.get("descripcion", ""),
        objetivo=objetivo,
        n=n_slides,
    )

    log(f"Escribiendo la historia de «{item['nombre']}»…", "writing")

    completion = _llm_json(
        (
            "Eres el Community Manager de Clandestino 1920, speakeasy de Salamanca "
            "inspirado en la Ley Seca. Voz misteriosa, elegante y cómplice: 'nosotros', "
            "'vosotros', 'guardianes', 'ritual', 'secreto'. Escribes en español de España. "
            "Respondes siempre JSON válido."
        ),
        prompt,
        max_tokens=2200,
    )

    data = completion
    slides = data.get("slides") or []
    if not slides:
        raise RuntimeError("El LLM no devolvió slides")

    return {
        "tema": item["nombre"],
        "precio": item.get("precio"),
        "alergenos": item.get("alergenos") or [],
        "slides": slides[:n_slides],
        "caption": data.get("caption", "").strip(),
        "hashtags": list(dict.fromkeys(
            (data.get("hashtags") or []) + ["#clandestino1920", "#salamanca", "#speakeasy"]
        )),
    }


# ─── RENDER ──────────────────────────────────────────────────────────────

def _wrap(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_w: int) -> list[str]:
    words, lines, cur = text.split(), [], ""
    for w in words:
        prueba = f"{cur} {w}".strip()
        if draw.textlength(prueba, font=font) <= max_w:
            cur = prueba
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def _cover(img: Image.Image, w: int, h: int) -> Image.Image:
    """Escala y recorta para llenar exactamente w×h sin deformar."""
    ratio = max(w / img.width, h / img.height)
    nw, nh = int(img.width * ratio + 1), int(img.height * ratio + 1)
    img = img.resize((nw, nh), Image.LANCZOS)
    left, top = (nw - w) // 2, (nh - h) // 2
    return img.crop((left, top, left + w, top + h))


def _gradient_overlay(w: int, h: int, start: float = 0.45) -> Image.Image:
    """Degradado negro de abajo arriba para que el texto se lea siempre."""
    grad = Image.new("L", (1, h), 0)
    for y in range(h):
        p = y / h
        if p < start:
            grad.putpixel((0, y), 0)
        else:
            grad.putpixel((0, y), int(230 * ((p - start) / (1 - start)) ** 1.3))
    grad = grad.resize((w, h))
    overlay = Image.new("RGB", (w, h), (0, 0, 0))
    return overlay, grad


def render_slide(image_path: Path, titulo: str, texto: str, index: int,
                 total: int, out_path: Path, marca: str = "CLANDESTINO 1920") -> Path:
    img = Image.open(image_path).convert("RGB")
    img = _cover(img, W, H)

    overlay, mask = _gradient_overlay(W, H, start=0.40)
    img = Image.composite(overlay, img, mask)

    draw = ImageDraw.Draw(img)

    # bloque de texto abajo
    y = H - MARGIN
    f_body = ImageFont.truetype(str(F_BODY), 42)
    f_title = ImageFont.truetype(str(F_TITLE), 74)
    f_marca = ImageFont.truetype(str(F_BODY), 26)

    body_lines = _wrap(draw, texto, f_body, W - 2 * MARGIN) if texto else []
    title_lines = _wrap(draw, titulo.upper(), f_title, W - 2 * MARGIN) if titulo else []

    line_h_body = 58
    line_h_title = 88
    total_h = len(title_lines) * line_h_title + (18 if body_lines else 0) + len(body_lines) * line_h_body

    y_text = y - total_h

    # filete decorativo
    draw.rectangle([MARGIN, y_text - 34, MARGIN + 90, y_text - 30], fill=(198, 158, 96))

    for ln in title_lines:
        draw.text((MARGIN, y_text), ln, font=f_title, fill=(255, 250, 240))
        y_text += line_h_title

    if body_lines:
        y_text += 18
        for ln in body_lines:
            draw.text((MARGIN, y_text), ln, font=f_body, fill=(238, 230, 215))
            y_text += line_h_body

    # marca arriba
    draw.text((MARGIN, 56), marca, font=f_marca, fill=(230, 214, 186))

    # contador y aviso de deslizar
    contador = f"{index}/{total}"
    draw.text((W - MARGIN - draw.textlength(contador, font=f_marca), 56),
              contador, font=f_marca, fill=(230, 214, 186))

    if index < total:
        aviso = "DESLIZA"
        ancho_txt = draw.textlength(aviso, font=f_marca)
        x0 = W - MARGIN - ancho_txt - 62
        y0 = H - MARGIN - 8
        draw.text((x0, H - MARGIN - 20), aviso, font=f_marca, fill=(198, 158, 96))
        # flecha dibujada a mano (la fuente no trae el carácter →)
        ax, ay = x0 + ancho_txt + 18, y0 - 12
        draw.line([(ax, ay), (ax + 34, ay)], fill=(198, 158, 96), width=3)
        draw.line([(ax + 22, ay - 9), (ax + 34, ay)], fill=(198, 158, 96), width=3)
        draw.line([(ax + 22, ay + 9), (ax + 34, ay)], fill=(198, 158, 96), width=3)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, "JPEG", quality=90, optimize=True)
    return out_path


def _limpiar_raw_antiguos(minutos: int = 10) -> None:
    """Borra carpetas .raw de ejecuciones anteriores que quedaron bloqueadas."""
    if not OUT_ROOT.exists():
        return
    limite = time.time() - minutos * 60
    for viejo in OUT_ROOT.glob("*/.raw"):
        try:
            if viejo.is_dir() and viejo.stat().st_mtime < limite:
                for f in viejo.glob("*"):
                    f.unlink(missing_ok=True)
                viejo.rmdir()
        except OSError:
            pass


def evaluar_carrusel(data: dict) -> dict | None:
    """
    Quinto agente: corrige el carrusel como un profesor exigente.
    Devuelve nota, criterios y un comentario. Si falla la red, devuelve None
    (no rompe el carrusel: evaluar es opcional).
    """
    slides_txt = "\n".join(
        f"{i}. {s.get('titulo','')} — {s.get('texto','')}"
        for i, s in enumerate(data.get("slides", []), start=1)
    )
    prompt = f"""CARRUSEL PARA INSTAGRAM DE CLANDESTINO 1920 (speakeasy, Salamanca)

Cóctel: {data.get('tema','')}
Slides:
{slides_txt}

Pie de foto: {(data.get('caption') or '')[:700]}
Hashtags: {' '.join((data.get('hashtags') or [])[:12])}

Corrige este carrusel como un profesor exigente de marketing digital de un bootcamp.
Sé concreto y justo. Devuelve SOLO este JSON:
{{
  "nota": 8.4,
  "criterios": {{
    "voz_de_marca": 8,
    "claridad": 9,
    "gancho": 8,
    "precio_y_alergenos": 8,
    "llamada_a_la_accion": 7
  }},
  "comentario": "Dos frases: una con lo que está bien y otra con lo que mejoraría."
}}"""

    try:
        res = _llm_json(
            "Eres un profesor de marketing digital. Evalúas contenido de marcas "
            "con criterio profesional y devuelves siempre JSON válido.",
            prompt,
            max_tokens=700,
        )
    except Exception as e:  # noqa: BLE001
        print(f"  ⚠ no se pudo evaluar el carrusel: {type(e).__name__}")
        return None

    try:
        res["nota"] = round(float(res.get("nota", 0)), 1)
    except (TypeError, ValueError):
        res["nota"] = 0.0
    return res


def _slug(texto: str) -> str:
    """'Café solo' → 'cafe_solo' (sin acentos: las URLs y rutas se rompen con tildes)."""
    import unicodedata
    limpio = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return limpio.lower().replace(" ", "_").replace("/", "-").replace("'", "")


def make_carousel(tema: str, objetivo: str = "vender", n_slides: int = 5,
                  progress=None) -> dict:
    """
    Genera el carrusel completo y devuelve rutas + textos.

    `progress` recibe (mensaje, etapa, **datos). Las etapas son las que se ven
    en el panel: research, writing, images, layout, export, done.
    """
    def log(msg: str, stage: str | None = None, **extra):
        if progress:
            progress(msg, stage, **extra)
        else:
            print(msg)

    _limpiar_raw_antiguos()

    # 1. INVESTIGADOR: carta + base de conocimiento
    log("Buscando en la carta y en la historia del local…", "research")
    data = build_carousel(tema, objetivo, n_slides, progress=progress)

    slug = _slug(data["tema"])
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir = OUT_ROOT / f"{slug}_{stamp}"
    tmp_dir = out_dir / ".raw"
    out_dir.mkdir(parents=True, exist_ok=True)

    total = len(data["slides"])
    slides_files = []

    # 2. ILUSTRADOR: una foto por slide (todas antes de montar, así se ven aparecer)
    for i, slide in enumerate(data["slides"], start=1):
        log(f"Generando la foto {i} de {total}…", "images",
            total=total, dir=out_dir.name)
        raw = tmp_dir / f"raw_{i:02d}.png"
        try:
            generate_image(slide.get("prompt_imagen", data["tema"]), raw, style=(
                "Photograph taken inside a 1920s speakeasy cocktail bar: dark walnut, brass, "
                "warm amber lamp light, bottles and glassware, film grain, shallow depth of field, "
                "photorealistic, vertical composition, no text, no watermark. "
                "The scene must happen at the bar or in the lounge, never on a ship, at sea or outdoors."
            ))
        except Exception as e:  # noqa: BLE001
            raise RuntimeError(mensaje_red(e, "la IA de imágenes (Google Gemini)")) from e
        log(f"Foto {i} lista", "images", slide=i, total=total, dir=out_dir.name)

    # 3. MONTADOR: tipografía, marca y numeración encima de cada foto
    for i, slide in enumerate(data["slides"], start=1):
        log(f"Montando el slide {i} de {total}…", "layout", total=total, dir=out_dir.name)
        out = out_dir / f"slide_{i:02d}.jpg"
        render_slide(tmp_dir / f"raw_{i:02d}.png", slide.get("titulo", ""),
                     slide.get("texto", ""), i, total, out)
        slides_files.append(out)
        log(f"Slide {i} montado", "layout", slide=i, total=total, dir=out_dir.name)

    # limpiar la carpeta temporal. En Windows puede estar bloqueada: el panel
    # sirve esas mismas fotos en directo mientras se generan. Se reintenta y,
    # si sigue ocupada, se deja (se barre al principio de la siguiente ejecución).
    for _intento in range(4):
        try:
            for f in tmp_dir.glob("*"):
                f.unlink()
            tmp_dir.rmdir()
            break
        except OSError:
            time.sleep(0.5)
    else:
        print("  · las fotos .raw siguen en uso: se limpian en la próxima ejecución")

    caption = f"{data['caption']}\n\n{' '.join(data['hashtags'])}\n"
    caption_path = out_dir / "caption.txt"
    caption_path.write_text(caption, encoding="utf-8")

    info = out_dir / "info.json"
    info.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    # 4. EMPAQUETADO: ZIP listo para subir/entregar
    log("Empaquetando el carrusel y el pie de foto…", "export")
    zip_path = out_dir.with_suffix(".zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(out_dir.glob("slide_*.jpg")):
            z.write(f, f.name)
        z.write(caption_path, "caption.txt")

    # 5. PROFESOR: corrige el carrusel (si la red lo permite)
    log("El profesor está corrigiendo el carrusel…", "review")
    evaluacion = evaluar_carrusel(data)
    if evaluacion:
        log(f"Nota del profesor: {evaluacion['nota']}/10", "review", nota=evaluacion["nota"])

    log("Carrusel listo.", "done", evaluacion=evaluacion)
    return {
        "tema": data["tema"],
        "dir": str(out_dir),
        "zip": str(zip_path),
        "caption": caption,
        "slides": [str(p) for p in slides_files],
        "estructura": data,
        "evaluacion": evaluacion,
    }


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        print('Uso: python carousel_agent.py "<cóctel>" [--slides N] [--objetivo vender]')
        sys.exit(1)

    pos = [a for a in args if not a.startswith("--")]
    tema = pos[0]
    n = 5
    if "--slides" in args:
        n = int(args[args.index("--slides") + 1])
    obj = "vender"
    if "--objetivo" in args:
        obj = args[args.index("--objetivo") + 1]

    res = make_carousel(tema, obj, n)
    print(f"\n✅ {res['tema']}")
    print(f"📁 {res['dir']}")
    print(f"🗜  {res['zip']}")
    print(f"🖼  {len(res['slides'])} slides")
