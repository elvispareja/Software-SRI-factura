# WhatsApp con audio e imagen: ya estaba construido, faltaba poder usarlo

Fecha: **12 de agosto de 2026**

Este documento parte de una corrección de rumbo: al preguntarme «qué más
hace falta», señalé «audio e imagen en WhatsApp» como pendiente, citando el
README y `traspaso.md`. Al revisar el código para trabajar en ello, resultó
que **ya estaba implementado** —`_transcribir_audio`, `_ocr_imagen` y el
enrutado en `_procesar` llevan ahí desde el commit `972d4f6`, la misma tanda
que cerró el API—. Los documentos estaban desactualizados, no el código.

Lo que sí faltaba, una vez verificado: la imagen funciona hoy (su dependencia,
`anthropic`, ya es un requirement obligatorio y su variable ya estaba
documentada); el **audio no**, porque su único camino —la API Whisper de
OpenAI— depende de un paquete que nunca se agregó a `requirements.txt` ni de
una variable de entorno que nunca se documentó. El código hacía lo correcto
—degradar con un aviso en vez de fallar en silencio—, pero nadie iba a saber
qué instalar para que dejara de degradar.

Y, más importante: **cero pruebas** para las tres rutas externas que maneja
`_procesar` (Graph API, Whisper, Claude Vision), pese a que el resto del
archivo sigue con disciplina la norma de "no se prueba que el modelo responda
bien, se prueba que el código enrute y degrade con gracia".

---

## 1. El audio ahora es instalable de fábrica

`backend/requirements.txt` no tenía `openai` en ninguna forma —ni como
requisito, ni como comentario indicando que es opcional—. Se agregó fijado a
`openai==1.109.1`, la última versión 1.x estable: se evitó a propósito la
`3.0.0` que resuelve por defecto, porque introduce una dependencia nueva
(`httpx2`) sin necesidad y un cambio de API mayor sin verificar contra el
código existente. La 1.x es la familia sobre la que está escrito
`_transcribir_audio` (`openai.OpenAI(...)` + `.audio.transcriptions.create(...)`),
estable desde noviembre de 2023.

`faster-whisper` —el fallback local, sin necesitar API externa— se deja
**fuera** de los requisitos: trae dependencias pesadas (`ctranslate2`) y no es
la ruta recomendada por defecto. Queda mencionado en el comentario del
requirements y en `.env.example` para quien lo necesite.

## 2. `OPENAI_API_KEY`, documentada

`.env.example` no mencionaba `OPENAI_API_KEY` en ningún lado. Se agregó junto
a las otras dos claves de IA, con la misma explicación que ya tenían
`ANTHROPIC_API_KEY` y `GEMINI_API_KEY`: para qué sirve y qué pasa si falta.
También se documentó `MODELO_CLAUDE`, la variable que usa el OCR de imágenes
y que tampoco estaba en el archivo de ejemplo.

## 3. Nueve pruebas para `_procesar`, que no tenía ninguna

Siguiendo la misma filosofía que ya declara el archivo —"lo que se prueba es
que la extracción se valide correctamente y que el webhook rechace lo que
debe rechazar, no que el modelo responda bien"— las pruebas nuevas no golpean
la API real de OpenAI ni de Anthropic: sustituyen `_descargar_media`,
`_transcribir_audio`, `_ocr_imagen`, `enviar_mensaje` y `atender_mensaje` por
dobles, y verifican el enrutado:

- Audio o imagen sin `media_id` → pide reenviar, sin llamar al orquestador.
- Descarga fallida → avisa, sin llamar al orquestador.
- Transcripción/OCR no disponible (sin API key) → responde con el mensaje de
  «no configurado» **que nombra la variable de entorno exacta que falta**, en
  vez de solo decir «no funcionó».
- Transcripción/OCR exitosos → el texto llega al orquestador marcado con
  `es_audio=True` o `es_imagen=True`, tal como usa el orquestador para anotar
  el origen en el historial de la conversación.
- Un tipo de mensaje no soportado (sticker, ubicación…) → explica qué formatos
  sí entiende.

```python
def test_audio_transcrito_llega_marcado_al_orquestador(cliente_web, monkeypatch):
    ...
    wa._procesar({"from": "593999", "type": "voice", "voice": {"id": "m1"}}, sesion=None)
    assert llamadas == [("593999", "factura para Juan", True, False)]
```

## 4. La documentación, corregida para decir lo que el código hace

El README decía «Pendiente menor: procesamiento de audio e imagen en
WhatsApp» y «exportación a PDF es cosmética, porque el CSV ya funciona».
**Las dos afirmaciones eran falsas** al momento de escribir esto: la
exportación a PDF de reportes se agregó en una tanda anterior
(`71c0aef`, nueve familias de reporte con endpoint `/pdf`), y el audio/imagen
de WhatsApp llevaba desde `972d4f6`. Se corrigió el README para reflejar el
estado real, incluyendo qué variable de entorno habilita cada canal.

También se actualizó el conteo de pruebas del README, que decía «526» desde
hace varias tandas: son **663** a día de hoy.

---

## Verificación

**663 pruebas en verde** — 410 backend (8 nuevas de esta tanda), 253
frontend (sin cambios: esta tanda no tocó frontend). Lint y build limpios.

```bash
cd backend  && .venv/Scripts/python -m pytest -q     # 410
cd frontend && npx vitest run                          # 253
cd frontend && npm run lint && npm run build
```

---

## Lo que sigue pendiente

- **La imagen funciona hoy con solo configurar `ANTHROPIC_API_KEY`.** El audio
  funciona hoy con `OPENAI_API_KEY` **y** haber corrido
  `pip install -r requirements.txt` de nuevo para traer `openai`. Ninguno de
  los dos se probó contra la API real —las pruebas nuevas verifican el
  enrutado del código, no que Whisper o Claude Vision produzcan una
  transcripción correcta—.
- El resto de la lista sigue igual que en la tanda anterior: el certificado
  `.p12`, el resto de operaciones sensibles sin diferenciar rol, y la suite
  sin ejecutar en Python 3.13/Linux real.
