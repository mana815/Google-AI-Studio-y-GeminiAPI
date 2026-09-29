from __future__ import annotations

import io
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

MODEL = "gemini-3.8-flash"
BASE_DIR = Path(__file__).resolve().parent
IMAGE_PATH = BASE_DIR / "imagen_ejemplo.jpg"
RESULTS_PATH = BASE_DIR / "resultados.json"

TEXTOS = [
    {"idioma": "es", "texto": "Me encanta esta aplicación; es rápida y muy fácil de usar."},
    {"idioma": "es", "texto": "El servicio fue terrible y tuve que esperar más de una hora."},
    {"idioma": "es", "texto": "La reunión de Acme será el martes a las 10:00 en Barcelona."},
    {"idioma": "es", "texto": "La cámara está bien, aunque la batería podría durar un poco más."},
    {"idioma": "es", "texto": "Estoy muy contento con el soporte de Google en Madrid."},
    {"idioma": "en", "texto": "I love the new dashboard; it is clear and incredibly useful."},
    {"idioma": "en", "texto": "The latest update broke the login screen and I am very frustrated."},
    {"idioma": "en", "texto": "The conference starts on Friday at 9 AM in London."},
    {"idioma": "en", "texto": "The design is fine, but the menu could be easier to navigate."},
    {"idioma": "en", "texto": "I am disappointed with the delivery from Example Store."},
]

SENTIMENT_SCHEMA = {
    "type": "object",
    "properties": {
        "sentimiento": {
            "type": "string",
            "enum": ["positivo", "negativo", "neutro"],
        },
        "confianza": {
            "type": "number",
            "minimum": 0,
            "maximum": 1,
        },
        "entidades": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "texto": {"type": "string"},
                    "tipo": {"type": "string"},
                },
                "required": ["texto", "tipo"],
                "additionalProperties": False,
            },
        },
        "justificacion": {"type": "string"},
    },
    "required": ["sentimiento", "confianza", "entidades", "justificacion"],
    "additionalProperties": False,
}


def crear_imagen_ejemplo(path: Path) -> None:
    """Crea una imagen de prueba solo si no existe imagen_ejemplo.jpg."""
    if path.exists():
        return

    image = Image.new("RGB", (1000, 600), (242, 246, 250))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle(
        (70, 70, 930, 530),
        radius=35,
        fill=(255, 255, 255),
        outline=(76, 110, 245),
        width=6,
    )
    draw.rectangle((120, 145, 430, 400), fill=(252, 205, 75))
    draw.ellipse((560, 150, 820, 410), fill=(93, 173, 226))
    draw.text((120, 100), "Imagen de ejemplo - Gemini", fill=(30, 30, 30))
    image.save(path, format="JPEG", quality=92)


def obtener_sdk_google():
    try:
        from google import genai
        from google.genai import types
    except ImportError as exc:
        raise RuntimeError(
            "No se encuentra google-genai. Instala primero: "
            "python -m pip install -U google-genai Pillow"
        ) from exc
    return genai, types


def validar_resultado_sentimiento(data: dict[str, Any]) -> dict[str, Any]:
    requeridas = {"sentimiento", "confianza", "entidades", "justificacion"}
    if set(data.keys()) != requeridas:
        raise ValueError(f"JSON con claves inesperadas: {sorted(data.keys())}")

    if data["sentimiento"] not in {"positivo", "negativo", "neutro"}:
        raise ValueError("El campo 'sentimiento' no contiene un valor permitido.")

    confianza = data["confianza"]
    if not isinstance(confianza, (int, float)) or not 0 <= float(confianza) <= 1:
        raise ValueError("El campo 'confianza' debe estar entre 0 y 1.")

    if not isinstance(data["entidades"], list):
        raise ValueError("El campo 'entidades' debe ser una lista.")

    for entidad in data["entidades"]:
        if not isinstance(entidad, dict) or set(entidad.keys()) != {"texto", "tipo"}:
            raise ValueError("Cada entidad debe contener exactamente 'texto' y 'tipo'.")

    if not isinstance(data["justificacion"], str):
        raise ValueError("El campo 'justificacion' debe ser texto.")

    return data


def ejecutar_practica() -> dict[str, Any]:
    """Ejecuta la práctica usando llamadas REALES a la API de Gemini."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "No se encuentra GEMINI_API_KEY. En PowerShell ejecuta primero:\n"
            '$env:GEMINI_API_KEY="TU_API_KEY"'
        )

    genai, types = obtener_sdk_google()
    client = genai.Client(api_key=api_key)

    # 1) Conexión básica y prompt de texto
    prompt_basico = "Explica en una frase qué es una API de inteligencia artificial."
    respuesta_basica = client.models.generate_content(
        model=MODEL,
        contents=prompt_basico,
    ).text

    time.sleep(6)

    # 2) Sentimiento: 5 textos en español + 5 en inglés
    resultados_sentimiento = []

    for indice, entrada in enumerate(TEXTOS, start=1):
        print(f"Analizando texto {indice}/{len(TEXTOS)}...")

        prompt = (
            "Analiza el sentimiento del siguiente texto. "
            "Clasifícalo como positivo, negativo o neutro; "
            "indica una confianza entre 0 y 1; extrae entidades relevantes "
            "indicando texto y tipo; y añade una justificación breve. "
            "Devuelve únicamente JSON conforme al esquema configurado.\n\n"
            f"Texto: {entrada['texto']}"
        )

        response = client.models.generate_content(
            model=MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_json_schema=SENTIMENT_SCHEMA,
                temperature=0.2,
            ),
        )

        resultado = validar_resultado_sentimiento(json.loads(response.text))
        resultados_sentimiento.append({**entrada, "resultado": resultado})

        if indice < len(TEXTOS):
            time.sleep(6)

    time.sleep(6)

    # 3) Multimodal: enviar imagen a Gemini
    if not IMAGE_PATH.exists():
        crear_imagen_ejemplo(IMAGE_PATH)

    with Image.open(IMAGE_PATH) as image:
        image = image.convert("RGB")
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=92)
        image_bytes = buffer.getvalue()

    prompt_imagen = (
        "Describe esta imagen en español en exactamente 4 apartados: "
        "1) Descripción general, 2) Objetos y elementos, "
        "3) Colores y composición, 4) Interpretación o posible uso. "
        "Sé concreto pero detallado."
    )

    print("Analizando imagen...")
    respuesta_imagen = client.models.generate_content(
        model=MODEL,
        contents=[
            prompt_imagen,
            types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
        ],
    ).text

    return {
        "modo": "real",
        "modelo": MODEL,
        "generado_en_utc": datetime.now(timezone.utc).isoformat(),
        "conexion_basica": {
            "prompt": prompt_basico,
            "respuesta": respuesta_basica,
        },
        "sentimiento": resultados_sentimiento,
        "multimodal": {
            "imagen": IMAGE_PATH.name,
            "respuesta": respuesta_imagen,
        },
    }


def guardar_resultados(data: dict[str, Any]) -> None:
    RESULTS_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def imprimir_resumen(data: dict[str, Any]) -> None:
    print("\n=== PRÁCTICA GEMINI API ===")
    print(f"Modo: {data['modo'].upper()}")
    print(f"Modelo: {data['modelo']}")

    print("\n[1] Conexión básica")
    print(data["conexion_basica"]["respuesta"])

    print("\n[2] Análisis de sentimiento")
    for i, item in enumerate(data["sentimiento"], start=1):
        resultado = item["resultado"]
        print(
            f"{i:02d}. {item['idioma'].upper()} | "
            f"{resultado['sentimiento']} | "
            f"confianza={resultado['confianza']:.2f} | "
            f"entidades={len(resultado['entidades'])}"
        )

    print("\n[3] Descripción detallada de la imagen")
    print(data["multimodal"]["respuesta"])

    print(f"\n[OK] Resultados reales guardados en: {RESULTS_PATH.name}")
    print(f"[OK] Imagen analizada: {IMAGE_PATH.name}")


def main() -> int:
    try:
        data = ejecutar_practica()
        guardar_resultados(data)
        imprimir_resumen(data)
        return 0
    except Exception as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())