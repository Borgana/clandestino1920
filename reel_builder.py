#!/usr/bin/env python3
"""
reel_builder.py — Convierte el JSON del pipeline en un reel MP4 vertical.

Flujo:
    FINAL_reel_*.json  →  lista de planos (shots_list)
                       →  una imagen por plano (Gemini / nano banana)
                       →  cada imagen con movimiento de cámara (Ken Burns, ffmpeg)
                       →  todo unido con fundidos  →  videos/reel_<tema>.mp4
                       →  + videos/reel_<tema>_caption.txt (copy + hashtags)

Uso:
    python reel_builder.py                          # usa el FINAL_reel_*.json más reciente
    python reel_builder.py FINAL_reel_old_fashioned.json
    python reel_builder.py FINAL_reel_old_fashioned.json --segundos 3 --sin-transiciones
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

from image_client import generate_image

ROOT = Path(__file__).parent
TMP = ROOT / ".build"
OUT_DIR = ROOT / "videos"

W, H = 1080, 1920
FPS = 30
SHOT_SECONDS = 3.0
XFADE = 0.5


def ffmpeg_exe() -> str:
    """Busca ffmpeg: variable FFMPEG → tools/ del proyecto → PATH → copia de Hermes."""
    import os

    env = os.environ.get("FFMPEG")
    if env and Path(env).exists():
        return env

    local = ROOT / "tools" / "ffmpeg.exe"
    if local.exists():
        return str(local)

    found = shutil.which("ffmpeg")
    if found and "WindowsApps" not in found:
        return found

    # copia que instala Hermes en el usuario (fallback)
    fallback = Path.home() / "AppData/Local/hermes/tools/ffmpeg-9.0.1-win32-x64/bin/ffmpeg.exe"
    if fallback.exists():
        return str(fallback)

    raise RuntimeError(
        "No encuentro ffmpeg. Instálalo con:  winget install Gyan.FFmpeg  "
        "(y vuelve a abrir la terminal)"
    )


def run(cmd: list[str]) -> None:
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"ffmpeg falló:\n{p.stderr[-1500:]}")


def clean_shot(text: str) -> str:
    """'Plano detalle de la botella' → 'detalle de la botella' (limpia numeración)."""
    t = text.strip()
    for pref in ("Plano ", "plano ", "PLANO "):
        if t.startswith(pref):
            t = t[len(pref):]
            # quita "1:" o "1 -" tras el prefijo
            t = t.lstrip("0123456789").lstrip(":.-) ").strip()
    return t


def make_clip(image: Path, out: Path, seconds: float, index: int, n: int) -> Path:
    """Imagen quieta → clip con zoom/pan lento. Alterna zoom-in y zoom-out."""
    frames = int(seconds * FPS)
    zoom_in = index % 2 == 0

    if zoom_in:
        zexpr = "min(1+0.0012*on,1.25)"
        xexpr = "iw/2-(iw/zoom/2)"
        yexpr = "ih/2-(ih/zoom/2)"
    else:
        zexpr = "max(1.25-0.0012*on,1.0)"
        xexpr = "iw/2-(iw/zoom/2)"
        yexpr = "ih/2-(ih/zoom/2)"

    vf = (
        # 1) sube a 4K vertical recortando lo que sobre
        f"scale={W*2}:{H*2}:force_original_aspect_ratio=increase,"
        f"crop={W*2}:{H*2},setsar=1,"
        # 2) movimiento lento sobre la imagen
        f"zoompan=z='{zexpr}':x='{xexpr}':y='{yexpr}':d={frames}:s={W}x{H}:fps={FPS},"
        f"format=yuv420p"
    )

    run([
        ffmpeg_exe(), "-y", "-loglevel", "error",
        "-i", str(image),
        "-vf", vf,
        "-t", f"{seconds}",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        str(out),
    ])
    return out


def join_clips(clips: list[Path], out: Path, seconds: float, transitions: bool) -> Path:
    """Une los clips. Con transiciones usa xfade; si no, corte directo (concat)."""
    if len(clips) == 1 or not transitions:
        lista = TMP / "lista.txt"
        lista.write_text(
            "".join(f"file '{c.as_posix()}'\n" for c in clips), encoding="utf-8"
        )
        run([
            ffmpeg_exe(), "-y", "-loglevel", "error",
            "-f", "concat", "-safe", "0", "-i", str(lista),
            "-c", "copy", str(out),
        ])
        return out

    cmd = [ffmpeg_exe(), "-y", "-loglevel", "error"]
    for c in clips:
        cmd += ["-i", str(c)]

    # cadena de fundidos: cada xfade recorta "XFADE" segundos del total
    parts, offset, prev = [], 0.0, "[0:v]"
    for i in range(1, len(clips)):
        offset += seconds - XFADE
        label = f"[v{i}]" if i < len(clips) - 1 else "[vout]"
        parts.append(
            f"{prev}[{i}:v]xfade=transition=fade:duration={XFADE}:offset={offset:.3f}{label}"
        )
        prev = label

    cmd += [
        "-filter_complex", ";".join(parts),
        "-map", "[vout]",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        str(out),
    ]
    run(cmd)
    return out


def build(creative_json: Path, shot_seconds: float = SHOT_SECONDS,
          transitions: bool = True, max_shots: int | None = None) -> Path:
    data = json.loads(creative_json.read_text(encoding="utf-8"))
    shots = data.get("shots_list") or []
    if not shots:
        raise RuntimeError("El JSON no tiene shots_list: genera un 'reel', no un post.")

    if max_shots:
        shots = shots[:max_shots]

    tema = creative_json.stem.replace("FINAL_reel_", "").replace("_", " ")
    slug = tema.replace(" ", "_").lower()
    OUT_DIR.mkdir(exist_ok=True)
    if TMP.exists():
        shutil.rmtree(TMP)
    TMP.mkdir(parents=True)

    print(f"🎬 {len(shots)} planos · {shot_seconds}s cada uno · {W}x{H}")
    clips = []
    for i, shot in enumerate(shots, start=1):
        desc = clean_shot(shot)
        img = TMP / f"shot_{i:02d}.png"
        print(f"  [{i}/{len(shots)}] imagen: {desc[:60]}")
        generate_image(desc, img)

        clip = TMP / f"shot_{i:02d}.mp4"
        print(f"  [{i}/{len(shots)}] movimiento")
        make_clip(img, clip, shot_seconds, i - 1, len(shots))
        clips.append(clip)

    out = OUT_DIR / f"reel_{slug}.mp4"
    print("🔗 Montando el vídeo final...")
    join_clips(clips, out, shot_seconds, transitions)

    # Texto listo para pegar en Instagram
    caption = OUT_DIR / f"reel_{slug}_caption.txt"
    hashtags = " ".join(data.get("hashtags", []))
    caption.write_text(
        f"{data.get('copy','')}\n\n{hashtags}\n", encoding="utf-8"
    )
    print(f"✅ Vídeo:  {out}")
    print(f"📝 Copy:   {caption}")
    return out


def latest_json() -> Path:
    files = sorted(ROOT.glob("FINAL_reel_*.json"), key=lambda p: p.stat().st_mtime)
    if not files:
        raise RuntimeError("No hay ningún FINAL_reel_*.json. Ejecuta antes pipeline.py")
    return files[-1]


def parse_args(argv: list[str]) -> dict:
    """Lee los argumentos: [json] [--segundos N] [--planos N] [--sin-transiciones]."""
    opts = {"json": None, "segundos": SHOT_SECONDS, "planos": None, "transiciones": True}
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--segundos":
            opts["segundos"] = float(argv[i + 1]); i += 2; continue
        if a == "--planos":
            opts["planos"] = int(argv[i + 1]); i += 2; continue
        if a == "--sin-transiciones":
            opts["transiciones"] = False; i += 1; continue
        if a.startswith("--"):
            raise SystemExit(f"Opción desconocida: {a}")
        opts["json"] = Path(a); i += 1
    return opts


if __name__ == "__main__":
    o = parse_args(sys.argv[1:])
    build(
        o["json"] or latest_json(),
        shot_seconds=o["segundos"],
        transitions=o["transiciones"],
        max_shots=o["planos"],
    )
