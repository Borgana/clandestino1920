# Guion de la presentación · 5 minutos

Deck: `presentacion/CLANDESTINO1920-definitiva.pptx` (9 diapositivas, 16:9).
Las notas del orador van dentro del PPTX: **Vista → Notas**.

Las animaciones (textos que entran en cascada) y la transición entre diapositivas
**solo se ven en Presentación con diapositivas (F5)**, no en la vista de edición.
Si al abrir PowerPoint pidiera "reparar", usa `CLANDESTINO1920-sin-animaciones.pptx`
(mismo diseño, sin animación).

---

## Antes de entrar

- [ ] Abrir el PPTX y comprobar que se ve el tema oscuro (si no, es que el proyector lava los negros: sube brillo).
- [ ] Tener abierta **una pestaña** con el panel ya arrancado: `python app.py`
  (arrancarlo antes de entrar, no delante de la clase: tarda 30-40 s en cargar los modelos).
- [ ] Tener abierta la carpeta `carruseles/` con 2-3 carruseles ya hechos (plan B).
- [ ] Un carrusel generado **el día anterior**, por si el wifi del aula falla o Gemini da error 429.
- [ ] Cerrar notificaciones y Slack/WhatsApp.

---

## Reparto del tiempo (5:00)

| Min | Diapositiva | Qué dices en una frase |
|---|---|---|
| 0:00-0:20 | 1 · Portada | Qué es y qué vas a enseñar |
| 0:20-0:55 | 2 · El problema | 130 referencias, 23 cócteles, 0 personas para redes |
| 0:55-1:30 | 3 · La idea | No es un chatbot: es un sistema con la carta dentro |
| 1:30-2:10 | 4 · Cómo funciona | Eliges · el sistema documenta · recibes el carrusel |
| 2:10-2:40 | 5 · Regla de oro | Si no está en la carta, no se dice |
| 2:40-3:10 | 6 · El juez | El agente que puede suspender |
| 3:10-3:35 | 7 · El valor | Qué cambia en el día a día del bar |
| 3:35-4:00 | 8 · Resultado | Los slides que salen |
| **4:00-5:00** | **9 · DEMO Y CIERRE** | **Última diapositiva: te vas al panel y generas uno en vivo** |

**Si vas justo:** recorta las diapositivas 3 y 7. La demo no se toca: es el final.

---

## Texto para decir (resumido, no leas literal)

**1. Portada (20 s)**
«Esto es Clandestino 1920, un speakeasy de Salamanca inspirado en la Ley Seca. Mi proyecto no es
una web: es un sistema que escribe y diseña el contenido del bar leyendo su propia carta.»

**2. El problema (40 s)**
«130 referencias en carta, 23 cócteles, y cero personas dedicadas a redes. La cuenta del bar vive de
lo que se publica a las once de la noche con el móvil. Contenido irregular y una voz que cambia
según quién lo escriba.»

**3. La idea (40 s)**
«Cualquiera puede pedirle un post a ChatGPT. Lo que no puede es que diga el precio correcto, no
invente un cóctel y suene al bar. La diferencia no es la IA: es la información que le das y el control
que le pones.»

**4. Cómo funciona (40 s)** ← rehecha: ahora son tres pasos
«Se usa en tres pasos. Uno: abro el panel y elijo el cóctel. Dos: el sistema lo documenta solo,
buscando en la carta y en la historia del bar lo que encaja con ese cóctel. Tres: me devuelve un
carrusel de cinco slides con su pie de foto. Un cóctel, cinco slides, un minuto.»
*Si preguntan la tecnología (la línea pequeña de abajo):* base vectorial, modelo de lenguaje, IA de
imágenes y montaje local.

**5. Regla de oro (35 s)**
«El modelo no opina sobre la carta, la consulta. Precio, ingredientes y alérgenos salen de la ficha, y
cada frase lleva los identificadores de los documentos de los que sale. Se puede auditar.»

**6. El juez (30 s)**
«Lo que hace que esto sea un sistema y no una tubería: un segundo agente puntúa cinco criterios y si
baja de siete, se reescribe. Su último feedback pedía precio y alérgenos: lo mismo que corregiría
una persona.»

**7. El valor (25 s)**
«¿Y qué cambia? Una: lo que antes era una tarde, ahora es un minuto. Dos: todo lo que se publica
tiene la misma voz y la misma estética. Y tres: nada sale sin que el bar lo revise. El sistema
propone, el negocio decide.»

**8. El resultado (25 s)**
«Esto es lo que sale: cuatro slides con la misma luz, la misma tipografía y una historia que se sigue
deslizando, más el pie de foto con sus hashtags.»

**9. DEMO Y CIERRE (60 s)** ← última diapositiva: aquí se acaba presentando
Dices la frase: «El contenido no se inventa, se destila. Y para que no sea solo una frase, lo hago
delante de vosotros.» **Y te vas al panel.**
- Eliges el cóctel (mejor uno con historia: Old Fashioned o Al Capone Sour).
- Pulsas generar y dejas que se vea el progreso: «esto que veis es el sistema buscando en la carta,
  escribiendo y pintando cada slide».
- Al terminar: enseñas los slides y el pie de foto.
- Cierras: «esto es lo que publicaría el bar esta noche. Gracias, ¿preguntas?»
*Si tarda más de 40 s:* «mientras termina, os enseño los que hice ayer» y abres la carpeta.

---

## Preguntas que te van a hacer

**«¿Y si el modelo se inventa algo?»**
Por eso el agente de calidad: comprueba que lo que dice esté en el contexto recuperado y que los
precios y alérgenos coincidan con la carta. Si no, suspende y se reescribe. Además cada frase cita
los documentos usados.

**«¿Cuánto tarda en hacer uno?»**
Alrededor de un minuto por carrusel de cinco slides. La demo es en vivo, no un vídeo grabado.

**«¿Esto lo puede usar otro bar?»**
Sí: es cambiar `data/` (carta, historia, tono) y el `.env`. El código es el mismo.

**«¿Por qué carrusel y no vídeo?»**
Porque es el formato que mejor funciona para un bar: se desliza, se lee y se guarda. El vídeo está
implementado, pero el carrusel da más resultado por el esfuerzo que cuesta.

**«¿Y el community manager del bar?»**
No desaparece: deja de escribir y empieza a elegir. Revisa, aprueba y decide qué se publica.

**«¿Es todo IA?»**
El texto y las imágenes sí. La maquetación (tipografía, degradados, formatos) es código local con
Pillow y ffmpeg, para que el resultado sea siempre igual y no dependa del azar del modelo.

---

## Plan B

| Si falla… | Haces… |
|---|---|
| El panel no arranca | Enseñas los carruseles de `carruseles/` ya generados |
| Error 429 de la IA de imágenes | «Hemos agotado el cupo del día» y usas los ya hechos |
| No hay wifi | El montaje es local; solo fallan textos e imágenes nuevos |
| Se cae el proyector | Lleva el PPTX también en un USB |
