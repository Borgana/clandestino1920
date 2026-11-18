#!/usr/bin/env python3
"""
presentacion_build.py — Genera la presentación de 5 minutos de Clandestino 1920.

Salida: presentacion/CLANDESTINO1920.pptx  (16:9, tema speakeasy)
Las imágenes vienen del propio proyecto: assets/interior y el carrusel generado.

Uso:  python presentacion/presentacion_build.py
"""

from pathlib import Path

from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.oxml import parse_xml
from pptx.oxml.ns import nsdecls, qn
from pptx.util import Inches, Pt

ROOT = Path(__file__).parent.parent
OUT = Path(__file__).parent / "CLANDESTINO1920-definitiva.pptx"
BACKUP = Path(__file__).parent / "CLANDESTINO1920-sin-animaciones.pptx"
TMP = Path(__file__).parent / ".img"
TMP.mkdir(exist_ok=True)

BG = RGBColor(0x0E, 0x0C, 0x0A)
PANEL = RGBColor(0x17, 0x13, 0x0F)
PANEL2 = RGBColor(0x22, 0x1B, 0x12)
GOLD = RGBColor(0xC6, 0x9E, 0x60)
GOLD_SOFT = RGBColor(0xE3, 0xC7, 0x95)
CREAM = RGBColor(0xF2, 0xEA, 0xD9)
MUTED = RGBColor(0xA2, 0x91, 0x7A)

SERIF = "Georgia"
W, H = 13.333, 7.5


# ─── utilidades ──────────────────────────────────────────────────────────

def new_slide(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])  # blank
    fill = s.background.fill
    fill.solid()
    fill.fore_color.rgb = BG
    return s


def text(slide, x, y, w, h, contenido, size=18, color=CREAM, bold=False,
         font=SERIF, align=PP_ALIGN.LEFT, spacing=1.15, italic=False, anchor=MSO_ANCHOR.TOP):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    lineas = contenido.split("\n")
    for i, ln in enumerate(lineas):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.line_spacing = spacing
        r = p.add_run()
        r.text = ln
        r.font.size = Pt(size)
        r.font.bold = bold
        r.font.italic = italic
        r.font.name = font
        r.font.color.rgb = color
    return tb


def rect(slide, x, y, w, h, fill=PANEL, line=None, shape=MSO_SHAPE.RECTANGLE, radius=None):
    sh = slide.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
    sh.fill.solid()
    sh.fill.fore_color.rgb = fill
    if line:
        sh.line.color.rgb = line
        sh.line.width = Pt(1.25)
    else:
        sh.line.fill.background()
    sh.shadow.inherit = False
    if radius is not None and shape == MSO_SHAPE.ROUNDED_RECTANGLE:
        sh.adjustments[0] = radius
    sh.text_frame.word_wrap = True
    return sh


def barra(slide, x, y, w=1.1, color=GOLD):
    rect(slide, x, y, w, 0.035, fill=color)


def cover_image(slide, path, x, y, w, h):
    """Recorta la imagen a la relación w/h y la coloca sin deformar."""
    img = Image.open(path).convert("RGB")
    target = w / h
    src = img.width / img.height
    if src > target:                      # sobra ancho
        nw = int(img.height * target)
        left = (img.width - nw) // 2
        img = img.crop((left, 0, left + nw, img.height))
    else:                                 # sobra alto
        nh = int(img.width / target)
        top = (img.height - nh) // 2
        img = img.crop((0, top, img.width, top + nh))
    tmp = TMP / f"{Path(path).stem}_{int(w*100)}x{int(h*100)}.jpg"
    img.save(tmp, "JPEG", quality=92)
    return slide.shapes.add_picture(str(tmp), Inches(x), Inches(y),
                                    width=Inches(w), height=Inches(h))


def notas(slide, texto):
    slide.notes_slide.notes_text_frame.text = texto


def cabecera(slide, eyebrow, titulo, subtitulo=None):
    text(slide, 0.9, 0.55, 8, 0.32, eyebrow.upper(), size=11.5, color=GOLD, bold=True)
    text(slide, 0.9, 1.0, 10.5, 1.0, titulo, size=38, color=CREAM, bold=True)
    barra(slide, 0.9, 1.95)
    if subtitulo:
        text(slide, 0.9, 2.15, 9.5, 0.6, subtitulo, size=16.5, color=MUTED, italic=True)


# ─── diapositivas ────────────────────────────────────────────────────────

def s_portada(prs):
    s = new_slide(prs)
    cover_image(s, ROOT / "assets/interior/interior_01.jpg", 7.85, 0, 5.48, H)

    text(s, 0.9, 1.15, 6.6, 0.3, "PROYECTO FINAL · BOOTCAMP DE IA", size=11.5, color=GOLD, bold=True)
    text(s, 0.9, 1.7, 6.85, 2.1, "CLANDESTINO\n1920", size=58, color=CREAM, bold=True, spacing=1.0)
    barra(s, 0.9, 4.05, 1.6)
    text(s, 0.9, 4.35, 6.6, 0.7, "El bar que se cuenta solo", size=25, color=GOLD_SOFT, italic=True)
    text(s, 0.9, 5.2, 6.5, 1.0,
         "Un sistema de agentes que convierte la carta de un speakeasy\nde Salamanca en carruseles de Instagram listos para publicar.",
         size=14.5, color=MUTED, spacing=1.35)
    text(s, 0.9, 6.75, 6.5, 0.3, "Noviembre 2026", size=11.5, color=MUTED)

    notas(s, "0:00-0:20 · Arranque.\n"
             "«Esto es Clandestino 1920, un speakeasy de Salamanca inspirado en la Ley Seca. "
             "Mi proyecto no es una web ni una app: es un sistema que escribe y diseña el contenido "
             "del bar leyendo su propia carta. En cinco minutos os enseño cómo funciona y lo veis funcionar.»")


def s_problema(prs):
    s = new_slide(prs)
    cabecera(s, "El punto de partida", "Un bar pequeño, una carta enorme")

    stats = [("130", "referencias en carta"), ("23", "cócteles con historia"), ("0", "personas para redes")]
    for i, (num, label) in enumerate(stats):
        x = 0.9 + i * 3.95
        rect(s, x, 2.75, 3.5, 1.85, fill=PANEL)
        text(s, x + 0.35, 2.95, 3.0, 0.9, num, size=54, color=GOLD, bold=True)
        text(s, x + 0.35, 3.85, 2.9, 0.6, label, size=13.5, color=MUTED)

    text(s, 0.9, 5.05, 11.4, 1.4,
         "Publicar a diario exige foto, texto, hashtags y una voz que no cambie cada semana.\n"
         "En un bar de dos personas, eso simplemente no ocurre: se publica cuando hay un hueco, "
         "y la mayoría de las noches no hay hueco.",
         size=17, color=CREAM, spacing=1.4)
    notas(s, "0:20-1:00 · El problema.\n"
             "«130 referencias en carta, 23 cócteles, y cero personas dedicadas a redes. "
             "La cuenta del bar vive de lo que se publica a las once de la noche con el móvil. "
             "El resultado: contenido irregular y una voz que cambia según quién lo escriba.»")


def s_idea(prs):
    s = new_slide(prs)
    cabecera(s, "La idea", "No es pedirle un post a ChatGPT")

    rect(s, 0.9, 2.55, 5.55, 3.35, fill=PANEL)
    text(s, 1.25, 2.85, 4.9, 0.4, "UN CHATBOT CUALQUIERA", size=12.5, color=MUTED, bold=True)
    text(s, 1.25, 3.35, 4.9, 2.2,
         "· No sabe qué hay en la carta\n"
         "· Se inventa precios y cócteles\n"
         "· Cambia de tono cada día\n"
         "· Hay que corregirlo a mano",
         size=16.5, color=MUTED, spacing=1.6)

    rect(s, 6.85, 2.55, 5.55, 3.35, fill=PANEL2, line=GOLD)
    text(s, 7.2, 2.85, 4.9, 0.4, "UN SISTEMA CON MEMORIA", size=12.5, color=GOLD, bold=True)
    text(s, 7.2, 3.35, 4.9, 2.2,
         "· Lee la carta, el lore y los alérgenos\n"
         "· Respeta la voz del speakeasy\n"
         "· Cita de dónde sale cada dato\n"
         "· Se puntúa y se corrige solo",
         size=16.5, color=CREAM, spacing=1.6)

    text(s, 0.9, 6.25, 11.5, 0.5,
         "La diferencia no es la IA: es la información que le das y el control que le pones.",
         size=15, color=GOLD_SOFT, italic=True)
    notas(s, "1:00-1:40 · La idea y el diferencial.\n"
             "«Cualquiera puede pedirle un post a ChatGPT. Lo que no puede es que ese post diga el precio "
             "correcto, no invente un cóctel y suene al bar. Eso es lo que he construido: no un prompt, "
             "un sistema con la carta dentro y un control de calidad automático.»")


def s_arquitectura(prs):
    s = new_slide(prs)
    cabecera(s, "Cómo funciona", "Tres pasos y ya está")

    pasos = [
        ("01", "Eliges el cóctel", "En el panel, de la carta real\ndel bar: 130 referencias"),
        ("02", "El sistema lo documenta", "Busca en la carta y en la historia\ndel local lo que encaja con ese cóctel"),
        ("03", "Recibes el carrusel", "Cinco slides con texto, fotos\ny pie de foto listos para subir"),
    ]
    x0, wcard, gap = 0.9, 3.6, 0.3
    for i, (num, titulo, sub) in enumerate(pasos):
        x = x0 + i * (wcard + gap)
        rect(s, x, 2.5, wcard, 2.6, fill=PANEL)
        text(s, x + 0.35, 2.72, 1.2, 0.5, num, size=26, color=GOLD, bold=True)
        text(s, x + 0.35, 3.32, wcard - 0.6, 0.75, titulo, size=17.5, color=CREAM, bold=True)
        text(s, x + 0.35, 4.12, wcard - 0.55, 0.95, sub, size=12, color=MUTED, spacing=1.3)

    text(s, 0.9, 5.45, 11.4, 0.55,
         "Un cóctel · cinco slides · un minuto. Siempre con la misma luz, la misma tipografía y la misma voz.",
         size=16.5, color=GOLD_SOFT, italic=True)

    text(s, 0.9, 6.35, 11.4, 0.5,
         "Por debajo: base de datos vectorial (Qdrant) · modelo de lenguaje (Groq) · IA de imágenes (Google) · montaje local.",
         size=11.5, color=MUTED)
    notas(s, "1:40-2:20 · Cómo funciona.\n"
             "«Se usa en tres pasos. Uno: abro el panel y elijo el cóctel. Dos: el sistema lo documenta solo, "
             "buscando en la carta y en la historia del bar lo que encaja con ese cóctel. Tres: me devuelve un "
             "carrusel de cinco slides con su pie de foto. Un cóctel, cinco slides, un minuto.»\n"
             "Si te preguntan la tecnología, la línea de abajo la tienes memorizada: base vectorial, modelo de "
             "lenguaje, IA de imágenes y montaje local.")


def s_carta(prs):
    s = new_slide(prs)
    cabecera(s, "La regla de oro", "Si no está en la carta, no se dice")

    text(s, 0.9, 2.5, 6.4, 3.2,
         "· El precio sale del JSON de la carta, no del modelo\n"
         "· Los ingredientes y los alérgenos, de la misma ficha\n"
         "· Cada frase arrastra los identificadores de los documentos usados\n"
         "· Si falta un dato, se omite: no se rellena el hueco",
         size=16.5, color=CREAM, spacing=1.75)

    rect(s, 7.7, 2.4, 4.7, 3.5, fill=PANEL2, line=GOLD)
    text(s, 8.0, 2.65, 4.1, 0.35, "FICHA REAL DE LA CARTA", size=10.5, color=GOLD, bold=True)
    text(s, 8.0, 3.05, 4.1, 0.5, "Old Fashioned", size=22, color=CREAM, bold=True)
    text(s, 8.0, 3.6, 4.1, 0.35, "7,50 € · Cócteles", size=13, color=GOLD_SOFT)
    text(s, 8.0, 4.05, 4.05, 1.7,
         "Whisky, azúcar, angostura,\nralladura de naranja\n\nAlérgenos: sulfitos",
         size=12.5, color=MUTED, spacing=1.35)

    text(s, 0.9, 6.35, 11.4, 0.5,
         "Es lo que separa una demo bonita de algo que un bar se atrevería a publicar.",
         size=15, color=GOLD_SOFT, italic=True)
    notas(s, "2:20-2:55 · La fuente de verdad.\n"
             "«Aquí está la clave del proyecto: el modelo no opina sobre la carta, la consulta. "
             "El precio, los ingredientes y los alérgenos vienen de la ficha. Y cada frase lleva los "
             "identificadores de los documentos de los que sale, así que se puede auditar.»")


def s_demo(prs):
    """Última diapositiva: desde aquí se pasa a la demo en vivo y se cierra ahí."""
    s = new_slide(prs)
    cover_image(s, ROOT / "assets/interior/interior_03.jpg", 8.35, 0, 4.98, H)
    text(s, 0.9, 0.55, 7.0, 0.35, "DEMO EN VIVO · CIERRE", size=11.5, color=GOLD, bold=True)
    text(s, 0.9, 1.05, 7.2, 1.45, "Y ahora, lo\nhacemos", size=44, color=CREAM, bold=True, spacing=1.05)
    barra(s, 0.9, 3.05, 1.6)

    pasos = [("1", "Elijo un cóctel de la carta"),
             ("2", "Pulso «generar carrusel»"),
             ("3", "En un minuto: slides y pie de foto")]
    for i, (n, t) in enumerate(pasos):
        y = 3.45 + i * 0.8
        rect(s, 0.9, y, 0.5, 0.5, fill=PANEL2, line=GOLD, shape=MSO_SHAPE.OVAL)
        text(s, 0.9, y + 0.08, 0.5, 0.35, n, size=13, color=GOLD, bold=True, align=PP_ALIGN.CENTER)
        text(s, 1.62, y + 0.07, 6.2, 0.45, t, size=17, color=CREAM)

    text(s, 0.9, 6.05, 7.0, 0.4,
         "«El contenido no se inventa: se destila.»", size=14, color=GOLD_SOFT, italic=True)
    text(s, 0.9, 6.55, 7.0, 0.4, "Gracias · ¿preguntas?", size=15, color=CREAM, bold=True)
    notas(s, "4:25-5:00 · CIERRE CON DEMO (aquí se acaba la presentación).\n"
             "Di la frase de cierre y salta al panel: «El contenido no se inventa, se destila. Y para que no sea "
             "solo una frase, lo hago delante de vosotros.»\n"
             "En el panel: elige el cóctel, pulsa generar y deja que se vea el progreso. Al terminar, muestra los "
             "slides y el pie de foto. Cierra con «esto es lo que publicaría el bar esta noche. Gracias, ¿preguntas?».\n"
             "Si algo falla: usa los carruseles ya generados de la carpeta y di que los hiciste con el mismo botón.")


def s_resultado(prs):
    s = new_slide(prs)
    text(s, 0.9, 0.5, 8, 0.32, "EL RESULTADO", size=11.5, color=GOLD, bold=True)
    text(s, 0.9, 0.9, 9.0, 0.75, "Cuatro slides, una historia", size=34, color=CREAM, bold=True)

    carpetas = sorted((p for p in (ROOT / "carruseles").glob("old_fashioned_*") if p.is_dir()),
                      key=lambda p: p.stat().st_mtime)
    carpeta = carpetas[-1] if carpetas else None
    wimg, gap = 2.62, 0.22
    x0 = 0.9
    for i in range(1, 5):
        f = carpeta / f"slide_{i:02d}.jpg" if carpeta else None
        if f and f.exists():
            cover_image(s, f, x0 + (i - 1) * (wimg + gap), 1.95, wimg, wimg * 1.25)

    text(s, 0.9, 5.6, 11.5, 1.2,
         "1080 × 1350 · marca, numeración y «desliza» en cada slide · pie de foto con hashtags incluidos.\n"
         "El texto de cada slide lo escribe el agente; la foto, la IA de imágenes; el montaje es local.",
         size=14.5, color=MUTED, spacing=1.4)
    notas(s, "3:55-4:20 · Resultado.\n"
             "«Esto es lo que se publica: cuatro slides con la misma luz, la misma tipografía y una historia que "
             "se sigue deslizando. Y el pie de foto, con los hashtags del bar, ya escrito.»")


def s_juez(prs):
    s = new_slide(prs)
    cabecera(s, "El diferencial", "Un agente que puede suspender")

    criterios = [("Voz de marca", "8"), ("Seguridad (alérgenos, precios)", "7"),
                 ("Enganche", "8"), ("Objetivo (vender)", "7"), ("Uso de la carta", "8")]
    for i, (c, n) in enumerate(criterios):
        y = 2.55 + i * 0.62
        text(s, 0.9, y, 5.6, 0.4, c, size=14.5, color=CREAM)
        rect(s, 6.6, y + 0.12, 1.5, 0.16, fill=PANEL2)
        rect(s, 6.6, y + 0.12, 1.5 * (int(n) / 10), 0.16, fill=GOLD)
        text(s, 8.25, y, 0.8, 0.4, n + "/10", size=13.5, color=GOLD_SOFT)

    rect(s, 9.5, 2.5, 3.0, 1.75, fill=PANEL2, line=GOLD)
    text(s, 9.8, 2.7, 2.5, 0.35, "NOTA FINAL", size=10.5, color=GOLD, bold=True)
    text(s, 9.8, 3.05, 2.5, 0.9, "7,5", size=44, color=CREAM, bold=True)
    text(s, 9.8, 3.9, 2.5, 0.3, "APROBADO", size=11, color=GOLD_SOFT)

    text(s, 0.9, 5.9, 11.5, 1.1,
         "Si baja de 7, el feedback vuelve al agente creativo y se reescribe. Hasta tres intentos.\n"
         "El último feedback real pedía precio y alérgenos: exactamente lo que un community manager corregiría.",
         size=15, color=CREAM, spacing=1.4)
    notas(s, "4:20-4:45 · El juez.\n"
             "«Y aquí está lo que hace que esto sea un sistema y no una tubería: hay un segundo agente que "
             "puntúa. Cinco criterios, y si la nota baja de siete, se reescribe. El último feedback que dio pedía "
             "meter el precio y los alérgenos: lo mismo que corregiría una persona.»")


def s_valor(prs):
    s = new_slide(prs)
    cabecera(s, "El valor", "Qué cambia en el día a día del bar")

    bloques = [
        ("De una tarde a un minuto",
         "Antes: pensar, fotografiar, escribir, maquetar.\nAhora: elegir un cóctel y revisar."),
        ("Una sola voz",
         "El mismo tono, la misma luz y la misma tipografía en todo lo que publica el local."),
        ("Nada sale sin manos humanas",
         "El sistema propone; el bar elige, corrige y publica. La última palabra es del negocio."),
    ]
    x0, wcard, gap = 0.9, 3.6, 0.3
    for i, (titulo, sub) in enumerate(bloques):
        x = x0 + i * (wcard + gap)
        rect(s, x, 2.5, wcard, 2.7, fill=PANEL)
        barra(s, x + 0.35, 2.8, 0.9)
        text(s, x + 0.35, 3.05, wcard - 0.6, 1.0, titulo, size=18, color=CREAM, bold=True, spacing=1.15)
        text(s, x + 0.35, 4.15, wcard - 0.55, 0.9, sub, size=12, color=MUTED, spacing=1.35)

    text(s, 0.9, 5.55, 11.4, 0.55,
         "El community manager deja de escribir y empieza a elegir.",
         size=17, color=GOLD_SOFT, italic=True)
    text(s, 0.9, 6.35, 11.4, 0.5,
         "Lo que se publica sigue sonando al bar porque la materia prima —la carta, la historia, el tono— ya era del bar.",
         size=12, color=MUTED)
    notas(s, "4:45-5:05 · El valor.\n"
             "«¿Y qué cambia? Tres cosas. Una: lo que antes era una tarde, ahora es un minuto. Dos: todo lo que "
             "se publica tiene la misma voz y la misma estética, no depende de quién lo haga. Y tres: nada sale "
             "sin que el bar lo revise. El sistema propone, el negocio decide.»")


def s_cierre(prs):
    s = new_slide(prs)
    cover_image(s, ROOT / "assets/interior/interior_02.jpg", 8.35, 0, 4.98, H)
    text(s, 0.9, 1.3, 7.0, 0.35, "CIERRE", size=11.5, color=GOLD, bold=True)
    text(s, 0.9, 1.85, 7.0, 2.4,
         "«El contenido\nno se inventa:\nse destila.»",
         size=34, color=CREAM, bold=True, spacing=1.25)
    barra(s, 0.9, 4.55, 1.6)
    text(s, 0.9, 4.9, 6.8, 1.6,
         "Siguiente paso: publicar desde el propio panel (API de Instagram)\ny aprender de lo que funciona cada semana.",
         size=14, color=MUTED, spacing=1.4)
    text(s, 0.9, 6.6, 6.8, 0.4, "Gracias · ¿preguntas?", size=15, color=GOLD_SOFT, bold=True)
    notas(s, "5:05-5:20 · Cierre (si vas justo, sáltate la frase y di gracias).\n"
             "«El contenido no se inventa, se destila: la carta ya tiene las historias, solo había que darles forma. "
             "El siguiente paso sería publicar desde el mismo panel. Gracias, ¿preguntas?»")


def apply_transitions(prs, kinds: list[str], speed: str = "slow") -> None:
    """
    Añade la transición de diapositiva (lo que pasa al pasar de una a otra).
    python-pptx no lo soporta, así que se inyecta el XML directamente.
    kinds: nombre de la transición por diapositiva ('fade', 'push', 'wipe', 'cover', 'dissolve').
    """
    for slide, kind in zip(prs.slides, kinds):
        sld = slide.element
        for vieja in sld.findall(qn("p:transition")):
            sld.remove(vieja)

        tr = parse_xml(f'<p:transition {nsdecls("p")} spd="{speed}"><p:{kind}/></p:transition>')

        # el orden del esquema es obligatorio: cSld, clrMapOvr, transition, timing
        ancla = sld.find(qn("p:clrMapOvr"))
        if ancla is None:
            ancla = sld.find(qn("p:cSld"))
        ancla.addnext(tr)


def apply_animations(prs, stagger_ms: int = 320, dur_ms: int = 550) -> None:
    """
    Animación de entrada por diapositiva: cada texto aparece con un fundido,
    escalonado de arriba abajo y de izquierda a derecha (lectura natural).
    Las tarjetas y las fotos se quedan fijas para que no parpadeen huecos vacíos.

    Se inyecta el XML de <p:timing>: python-pptx no tiene API para animaciones.
    """
    for slide in prs.slides:
        objetivos = [sh for sh in slide.shapes
                     if sh.has_text_frame and sh.text_frame.text.strip()]
        if not objetivos:
            continue

        # fila (arriba) y luego columna (izquierda)
        objetivos.sort(key=lambda sh: (int(sh.top / 250000), sh.left))

        # el cascade nunca dura más de ~2,2 s, aunque haya muchos textos
        paso = min(stagger_ms, max(90, int(2200 / max(1, len(objetivos)))))

        efectos = []
        uid = 3
        for i, sh in enumerate(objetivos):
            delay = i * paso
            spid = sh.shape_id
            efectos.append(f"""
            <p:par><p:cTn id="{uid}" fill="hold"><p:stCondLst><p:cond delay="{delay}"/></p:stCondLst>
              <p:childTnLst><p:par><p:cTn id="{uid+1}" fill="hold"><p:stCondLst><p:cond delay="0"/></p:stCondLst>
                <p:childTnLst><p:par><p:cTn id="{uid+2}" presetID="10" presetClass="entr" presetSubtype="0" fill="hold" nodeType="withEffect">
                  <p:stCondLst><p:cond delay="0"/></p:stCondLst>
                  <p:childTnLst>
                    <p:set><p:cBhvr><p:cTn id="{uid+3}" dur="1" fill="hold"><p:stCondLst><p:cond delay="0"/></p:stCondLst></p:cTn>
                      <p:tgtEl><p:spTgt spid="{spid}"/></p:tgtEl>
                      <p:attrNameLst><p:attrName>style.visibility</p:attrName></p:attrNameLst>
                    </p:cBhvr><p:to><p:strVal val="visible"/></p:to></p:set>
                    <p:animEffect transition="in" filter="fade"><p:cBhvr><p:cTn id="{uid+4}" dur="{dur_ms}"/>
                      <p:tgtEl><p:spTgt spid="{spid}"/></p:tgtEl>
                    </p:cBhvr></p:animEffect>
                  </p:childTnLst></p:cTn></p:par></p:childTnLst>
              </p:cTn></p:par></p:childTnLst>
            </p:cTn></p:par>""")
            uid += 5

        xml = f"""<p:timing {nsdecls("p", "a")}><p:tnLst><p:par>
          <p:cTn id="1" dur="indefinite" restart="never" nodeType="tmRoot"><p:childTnLst>
            <p:seq concurrent="1" nextAc="seek">
              <p:cTn id="2" dur="indefinite" nodeType="mainSeq"><p:childTnLst>
                {"".join(efectos)}
              </p:childTnLst></p:cTn>
              <p:prevCondLst><p:cond evt="onPrev" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:prevCondLst>
              <p:nextCondLst><p:cond evt="onNext" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:nextCondLst>
            </p:seq>
          </p:childTnLst></p:cTn>
        </p:par></p:tnLst></p:timing>"""

        sld = slide.element
        for viejo in sld.findall(qn("p:timing")):
            sld.remove(viejo)
        timing = parse_xml(xml)

        ancla = sld.find(qn("p:transition"))
        if ancla is None:
            ancla = sld.find(qn("p:clrMapOvr"))
        ancla.addnext(timing)


def main():
    prs = Presentation()
    prs.slide_width = Inches(W)
    prs.slide_height = Inches(H)

    # Orden: primero todo el contenido, y la demo en vivo como cierre.
    s_portada(prs)
    s_problema(prs)
    s_idea(prs)
    s_arquitectura(prs)
    s_carta(prs)
    s_juez(prs)
    s_valor(prs)
    s_resultado(prs)
    s_demo(prs)          # última: se acaba demostrando

    total = len(prs.slides._sldIdLst)

    # Copia de seguridad SIN animaciones ni transiciones, por si PowerPoint
    # se queja al abrir la versión animada.
    prs.save(BACKUP)

    # 1) Transición entre diapositivas: un fundido suave y uniforme.
    apply_transitions(prs, ["fade"] * total, speed="med")

    # 2) Animaciones dentro de cada diapositiva: los textos entran en cascada.
    apply_animations(prs, stagger_ms=320, dur_ms=550)

    prs.save(OUT)
    print(f"✅ {OUT}  ({total} diapositivas)")
    print(f"🛟 {BACKUP}  (sin animaciones, por si acaso)")


if __name__ == "__main__":
    main()
