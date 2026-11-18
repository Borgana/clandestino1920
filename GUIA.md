# Clandestino 1920 — sistema de contenido automático

Guía de uso. Léela de arriba abajo la primera vez.

---

## 1. Qué hace el sistema (en cristiano)

```
   data/  (carta, lore, técnicas, alérgenos, eventos)
        │
        ▼
   ingest.py      → trocea esos documentos y los guarda como "vectores"
        │           en Qdrant (una base de datos que busca por significado)
        ▼
   pipeline.py    → 1. busca en Qdrant lo que tenga que ver con el tema
                    2. creative_agent.py  escribe el copy y los planos
                    3. quality_agent.py   lo puntúa del 0 al 10
                    4. si no llega a 7, se lo devuelve al creativo y repite (máx. 3)
        │
        ▼
   FINAL_reel_<tema>.json   ← EL JSON que te faltaba
        │
        ▼
   reel_builder.py → una imagen por plano + movimiento de cámara + fundidos
        │
        ▼
   videos/reel_<tema>.mp4  +  videos/reel_<tema>_caption.txt
```

Hay **tres agentes**, cada uno con un trabajo:

| Agente | Archivo | Qué hace |
|---|---|---|
| Ingesta | `ingest.py` | Mete tu carta y tus documentos en la base de datos vectorial. Solo se ejecuta cuando cambias los datos. |
| Creativo | `creative_agent.py` | Escribe el copy, los hashtags y la lista de planos. Usa Groq (LLM gratuito). |
| Calidad | `quality_agent.py` | Puntúa en 5 criterios y devuelve feedback. Si suspende, el creativo reescribe. |

---

## 2. El comando que buscabas (generar el JSON)

Abre una terminal en VS Code (**Terminal → Nueva terminal**), comprueba que estás en
`C:\Proyectos\Clandestino1920` y activa el entorno:

```powershell
.\.venv\Scripts\Activate.ps1
```

Y luego:

```powershell
python pipeline.py "Old Fashioned" reel vender
```

Estructura del comando:

```
python pipeline.py    "<tema>"    <formato>    <objetivo>
                       ↑           ↑            ↑
                       lo que      reel |       vender | educar |
                       quieras     story |      entretener |
                                   post |       fidelizar |
                                   blog         anunciar
```

Ejemplos que funcionan tal cual:

```powershell
python pipeline.py "Old Fashioned" reel vender
python pipeline.py "Gin Tonic de la casa" story entretener
python pipeline.py "Noche de jazz" post anunciar
```

Tarda entre 20 y 60 segundos. Al terminar verás algo así:

```
🔄 INTENTO 1/3
   Score: 7.5/10  ✅
✅ APROBADO EN INTENTO 1
💾 Guardado en: FINAL_reel_old_fashioned.json
📊 Score final: 7.5/10
```

Ese `FINAL_reel_old_fashioned.json` **es** el JSON del que hablabas. No lo escribes tú a mano:
lo escribe el agente.

### Qué hay dentro del JSON

| Campo | Qué es |
|---|---|
| `copy` | El texto del post, con emojis y CTA. Va en el pie de foto de Instagram. |
| `shots_list` | Los planos del reel, en orden: "detalle de la botella", "azúcar en cubo"... |
| `hashtags` | Lista de hashtags ya con el fijo del bar. |
| `alt_text` | Descripción accesible (por si algún día lo subes por API a Instagram). |
| `citations` | IDs de los documentos de Qdrant que ha usado. Es tu prueba antifake. |
| `_quality` | Las notas del agente de calidad y el feedback. |

Si quieres que **no** repita la generación aunque suspenda, o cambiar el listón del 7,
se toca en `pipeline.py` (`THRESHOLD` y `MAX_ATTEMPTS`).

---

## 3. El comando del vídeo (el reel)

Con el JSON ya generado:

```powershell
python reel_builder.py
```

Coge el `FINAL_reel_*.json` más reciente y produce:

- `videos/reel_<tema>.mp4` → 1080×1920, 30 fps, listo para subir
- `videos/reel_<tema>_caption.txt` → el copy + hashtags para copiar y pegar

Opciones útiles:

```powershell
python reel_builder.py FINAL_reel_old_fashioned.json   # un JSON concreto
python reel_builder.py --planos 3                      # solo los 3 primeros (prueba rápida)
python reel_builder.py --segundos 2.5                  # planos más cortos
python reel_builder.py --sin-transiciones              # corte directo, sin fundidos
```

Tarda ~2-3 minutos con 7 planos (una imagen por plano + montaje).

Necesita **ffmpeg** para montar el vídeo. Ya está puesto en `tools\ffmpeg.exe` (dentro del
propio proyecto, así no depende de nada instalado en el sistema). Si algún día falta:

```powershell
# descarga la build estática y copia ffmpeg.exe a tools\
# https://github.com/BtbN/FFmpeg-Builds/releases  → ffmpeg-master-latest-win64-gpl.zip
```


**Cómo se genera cada imagen:** con la API de imágenes de Google (modelo
`gemini-2.5-flash-image`, el "nano banana"), usando la clave `GEMINI_API_KEY` que ya
está puesta en el `.env`. Todos los planos comparten el mismo estilo (luz ámbar, madera,
granos de película) para que parezcan del mismo local.

---

## 4. Carruseles de Instagram (el panel interactivo)

Esto es lo que vas a presentar. Un carrusel es lo que de verdad funciona en Instagram
para un bar: 4-6 fotos con texto, la gente desliza, y no depende de ningún vídeo de pago.

### Arrancar el panel

```powershell
.\.venv\Scripts\Activate.ps1
python app.py
```

Se abre el navegador solo en `http://127.0.0.1:5000` (para parar: `Ctrl+C` en la terminal).

En el panel tienes:

- **Arriba**: las fotos del local (`assets/interior/`). Se generan solas la primera vez.
- **Izquierda**: la carta completa (130 referencias), con pestañas por categoría y buscador.
- **Derecha**: el cóctel elegido, el objetivo, el número de slides y el botón
  **GENERAR CARRUSEL**.
- **Al terminar**: las miniaturas, un botón para descargar el **ZIP** y el pie de foto
  ya escrito (se copia solo al pulsarlo).

Tarda entre 30 y 90 segundos. Mientras genera, el panel va contando qué slide está haciendo.

### Qué hace por dentro

```
cóctel elegido
   → busca la ficha en data/carta.json (precio, ingredientes, alérgenos)
   → busca contexto del bar en Qdrant (lore, técnicas, eventos)
   → el LLM escribe: título + texto de cada slide + pie de foto
   → Gemini (nano banana) genera una foto 4:5 por slide
   → Pillow escribe el texto encima (Georgia, degradado para que se lea siempre)
   → carruseles/<cóctel>_<fecha>/slide_01.jpg … + caption.txt + .zip
```

Salida típica: `carruseles/old_fashioned_20261117-193602/`

| Archivo | Qué es |
|---|---|
| `slide_01.jpg` … | 1080×1350 px (4:5), con la marca, el número de slide y el "desliza". |
| `caption.txt` | El pie de foto con hashtags, listo para pegar. |
| `info.json` | La estructura que generó el LLM (por si quieres retocar textos). |
| `../<mismo nombre>.zip` | Todo junto, para descargar o entregar. |

### Por consola, sin panel

```powershell
python carousel_agent.py "Al Capone Sour"
python carousel_agent.py "Old Fashioned" --slides 6 --objetivo educar
```

### Notas

- Los textos salen de la carta real, así que no se inventa precios ni ingredientes.
- El cóctel "Al Capone Sour" genera una imagen con una pistola de adorno: es coherente
  con el nombre, pero si Instagram te la marca, cambia la palabra "Capone" en el prompt
  o elige otro cóctel.
- Si cambias la carta, ejecuta `python ingest.py` para que el contexto se actualice.
- Otro puerto o sin abrir navegador: `python app.py --port 8000 --no-browser`

---

## 5. Por qué no te funcionaban Runway, Luma y Kling

Lo he probado todo contra las APIs reales. Resumen honesto:

| Servicio | Qué pasaba |
|---|---|
| **Runway** | La clave **es válida**, pero el código apuntaba a `api.runwayml.com` (mal) en vez de `api.dev.runwayml.com`. Aun arreglándolo, la cuenta responde: *"You do not have enough credits to run this task"*. **Falta dinero en la cuenta, no código.** Ya está corregido (`runway_client.py`), listo para cuando recargues. |
| **Luma** | La clave del `.env` no vale: la API contesta `403 Not authenticated`. Hay que generar una nueva en el panel de Luma (y su API es de pago). |
| **Kling** | La clave que tienes (`KLING_API_KEY`) **no sirve para la API oficial**: Kling no usa una clave simple, sino un par *Access Key / Secret Key* que hay que firmar como token JWT en cada petición. Además su API es de pago. He reescrito `kling_client.py` con la autenticación correcta, pero **no lo he podido probar** porque no hay cuenta con créditos. |

Conclusión: **ninguno de los tres fallaba por tu proyecto, fallaba por accesos/créditos.**
Por eso el proyecto ahora genera el vídeo sin depender de ellos.

---

## 6. Si algún día quieres vídeo de IA de verdad (Kling)

1. Entra en <https://app.klingai.com/global/dev> y crea la cuenta.
2. Compra un paquete de créditos (con 5-10 € hay de sobra para varios reels).
3. En el panel, **API Keys** → genera *Access Key* y *Secret Key*.
4. Añádelas al `.env`:

```
KLING_ACCESS_KEY=tu_access_key
KLING_SECRET_KEY=tu_secret_key
```

5. Prueba un plano:

```powershell
python -c "from kling_client import generate_and_download; from pathlib import Path; generate_and_download('Barman vertiendo whisky en un vaso, speakeasy 1920, luz ámbar', Path('videos/test_kling.mp4'), duration=5, mode='std')"
```

Cada plano de 5 s cuesta unos 0,20-0,40 €. Un reel de 5 planos ≈ 1-2 €.

Se puede mezclar: los planos que quieras de IA y el resto con el método gratis,
pegándolos luego con ffmpeg.

---

## 7. Archivos del proyecto

| Archivo | Para qué |
|---|---|
| `ingest.py` | (Re)carga la base de conocimiento. Ejecútalo si cambias `data/`. |
| `pipeline.py` | **El comando principal**: tema + formato + objetivo → JSON. |
| `creative_agent.py` | Agente que escribe. También se puede usar solo. |
| `quality_agent.py` | Agente que puntúa. `python quality_agent.py FINAL_reel_x.json` para re-evaluar. |
| `reel_builder.py` | **JSON → vídeo MP4.** |
| `carousel_agent.py` | **Cóctel → carrusel de 4-6 slides + caption + ZIP.** |
| `app.py` | **El panel interactivo** (servidor local con Flask). |
| `templates/panel.html` | La cara del panel: carta, fotos del local y botón de generar. |
| `assets/interior/` | Fotos del local que salen en el panel (se generan una vez). |
| `carruseles/` | Los carruseles generados, cada uno en su carpeta. |
| `image_client.py` | Genera una imagen suelta (por si quieres probar un plano). |
| `video_prompt_builder.py` | Convierte `shots_list` en prompts de vídeo (lo usan los clientes de IA). |
| `kling_client.py` / `runway_client.py` / `luma_client.py` | Clientes de vídeo IA (necesitan créditos). |
| `test_video.py`, `test_search.py`, `check_models.py` | Pruebas antiguas, ya no hacen falta. Ignóralos. |
| `data/` | Carta, lore, técnicas, alérgenos, eventos. La fuente de la verdad. |
| `.env` | Claves. **No lo subas a GitHub.** |

---

## 8. Avisos

- Si añades cócteles o cambias precios en `data/carta.json`, ejecuta `python ingest.py`
  o el agente seguirá hablando de la carta vieja.
- El `.env` tiene claves reales. Si el proyecto va a un repo público, mételo en
  `.gitignore` y usa un `.env.example` sin valores.
- Los MP4 se guardan en `videos/` y las imágenes temporales en `.build/` (se borra solo
  en cada ejecución). Puedes añadir ambas a `.gitignore`.

---

## 9. Publicado: GitHub + Vercel

| Qué | Dónde |
|---|---|
| **Presentación** (HTML) | <https://clandestino1920.vercel.app> |
| **Carta y galería de carruseles** | <https://clandestino1920.vercel.app/demo.html> |
| **Código** | <https://github.com/Borgana/clandestino1920> |

**Para presentar** se usan dos pestañas: la presentación (Vercel) y el panel
(`python app.py` → `127.0.0.1:5000`). El panel **no** puede estar en Vercel: necesita
Python, torch y 60 s por petición; Vercel es solo para la parte estática.

### Cuando generes carruseles nuevos

```powershell
python sync_web.py                          # pasa los carruseles a web/
git add -A
git commit -m "nuevos carruseles"
git push
vc deploy web --prod --project clandestino1920
```

`sync_web.py` copia las imágenes, refresca `web/data/carruseles.json` y quita las
tildes de los nombres (una carpeta `café_solo` rompe las URLs).

### La presentación en HTML

`web/index.html` es la versión web de las diapositivas: 9 slides, tema oscuro, mismas
fotos y textos. Se maneja con:

| Tecla | Acción |
|---|---|
| `→` `espacio` `Intro` | siguiente |
| `←` `Retroceso` | anterior |
| `N` | mostrar/ocultar las notas del orador |
| `F` | pantalla completa |

Dentro de cada diapositiva los textos entran **solos en cascada** (no hay que clicar
diez veces): es una animación automática al cambiar de slide. Los cambios de diapositiva
son un fundido suave.

### Editar la presentación

Se edita `web/index.html` directamente (texto plano, sin compilar). Después:

```powershell
git add web/index.html && git commit -m "presentacion" && git push
vc deploy web --prod --project clandestino1920
```
