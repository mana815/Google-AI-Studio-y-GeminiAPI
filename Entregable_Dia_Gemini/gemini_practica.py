from __future__ import annotations

import argparse
import io
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

MODEL = "gemini-2.5-flash"
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
    """Crea una imagen JPG sencilla con Pillow si todavía no existe."""
    if path.exists():
        return

    image = Image.new("RGB", (1000, 600), (242, 246, 250))
    draw = ImageDraw.Draw(image)

    draw.rounded_rectangle((70, 70, 930, 530), radius=35, fill=(255, 255, 255), outline=(76, 110, 245), width=6)
    draw.rectangle((120, 145, 430, 400), fill=(252, 205, 75))
    draw.ellipse((560, 150, 820, 410), fill=(93, 173, 226))
    draw.line((150, 465, 850, 465), fill=(70, 70, 70), width=4)
    draw.text((120, 100), "Imagen de ejemplo - Gemini", fill=(30, 30, 30))
    draw.text((120, 480), "Creada automaticamente con Pillow", fill=(70, 70, 70))

    image.save(path, format="JPEG", quality=92)


def obtener_sdk_google():
    """Importa google-genai solo cuando se usa el modo real."""
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
        raise ValueError(f"JSON de sentimiento con claves inesperadas: {sorted(data.keys())}")

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


def modo_demo() -> dict[str, Any]:
    demo_sentimientos = [
        {"sentimiento": "positivo", "confianza": 0.98, "entidades": [{"texto": "aplicación", "tipo": "producto"}], "justificacion": "El texto expresa satisfacción clara con la rapidez y facilidad de uso."},
        {"sentimiento": "negativo", "confianza": 0.99, "entidades": [{"texto": "servicio", "tipo": "servicio"}], "justificacion": "Se usan términos negativos y se destaca una espera excesiva."},
        {"sentimiento": "neutro", "confianza": 0.96, "entidades": [{"texto": "Acme", "tipo": "organización"}, {"texto": "Barcelona", "tipo": "lugar"}, {"texto": "martes a las 10:00", "tipo": "fecha_hora"}], "justificacion": "Es información descriptiva sobre una reunión sin valoración emocional."},
        {"sentimiento": "neutro", "confianza": 0.78, "entidades": [{"texto": "cámara", "tipo": "producto"}, {"texto": "batería", "tipo": "componente"}], "justificacion": "Combina una valoración aceptable con una crítica moderada, sin una polaridad dominante."},
        {"sentimiento": "positivo", "confianza": 0.98, "entidades": [{"texto": "Google", "tipo": "organización"}, {"texto": "Madrid", "tipo": "lugar"}], "justificacion": "La frase expresa satisfacción explícita con el soporte recibido."},
        {"sentimiento": "positivo", "confianza": 0.99, "entidades": [{"texto": "dashboard", "tipo": "producto"}], "justificacion": "La persona expresa entusiasmo y utilidad de forma explícita."},
        {"sentimiento": "negativo", "confianza": 0.99, "entidades": [{"texto": "update", "tipo": "software"}, {"texto": "login screen", "tipo": "componente"}], "justificacion": "Describe un fallo causado por la actualización y expresa frustración."},
        {"sentimiento": "neutro", "confianza": 0.97, "entidades": [{"texto": "Friday at 9 AM", "tipo": "fecha_hora"}, {"texto": "London", "tipo": "lugar"}], "justificacion": "Es un dato informativo sobre fecha, hora y lugar, sin opinión."},
        {"sentimiento": "neutro", "confianza": 0.76, "entidades": [{"texto": "design", "tipo": "característica"}, {"texto": "menu", "tipo": "componente"}], "justificacion": "La valoración es mixta y moderada, por lo que se clasifica como neutra."},
        {"sentimiento": "negativo", "confianza": 0.98, "entidades": [{"texto": "Example Store", "tipo": "organización"}, {"texto": "delivery", "tipo": "servicio"}], "justificacion": "La palabra 'disappointed' expresa claramente una experiencia negativa."},
    ]

    analisis = []
    for entrada, salida in zip(TEXTOS, demo_sentimientos, strict=True):
        analisis.append({**entrada, "resultado": validar_resultado_sentimiento(salida)})

    return {
        "modo": "demo",
        "modelo": MODEL,
        "generado_en_utc": datetime.now(timezone.utc).isoformat(),
        "conexion_basica": {
            "prompt": "Explica en una frase qué es una API de inteligencia artificial.",
            "respuesta": "[DEMO] Una API de inteligencia artificial permite que un programa envíe datos a un modelo y reciba una respuesta de forma automática.",
        },
        "sentimiento": analisis,
        "multimodal": {
            "imagen": IMAGE_PATH.name,
            "respuesta": (
                "1. Descripción general: imagen didáctica creada para probar una entrada multimodal.\n"
                "2. Objetos y elementos: un rectángulo amarillo, un círculo azul, un marco y textos.\n"
                "3. Colores y composición: fondo claro, formas simples y composición centrada.\n"
                "4. Interpretación/uso: sirve como imagen de ejemplo para comprobar que el script puede enviar una imagen a Gemini."
            ),
        },
    }


def modo_real() -> dict[str, Any]:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "No existe la variable GEMINI_API_KEY. Configúrala en PowerShell o ejecuta con --demo."
        )

    genai, types = obtener_sdk_google()
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    # A) Conexión básica
    prompt_basico = "Explica en una frase qué es una API de inteligencia artificial."
    respuesta_basica = client.models.generate_content(
        model=MODEL,
        contents=prompt_basico,
    ).text

    # Pausa para repartir las peticiones y reducir el riesgo de 429 en Free Tier.
    time.sleep(6)

    # B) Sentimiento: 5 textos ES + 5 EN, JSON estricto.
    resultados_sentimiento = []
    for indice, entrada in enumerate(TEXTOS):
        prompt = (
            "Analiza el sentimiento del siguiente texto. Clasifícalo como positivo, negativo o neutro; "
            "estima una confianza entre 0 y 1; extrae entidades relevantes indicando texto y tipo; "
            "y añade una justificación breve. Devuelve únicamente el JSON conforme al esquema configurado.\n\n"
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

        parsed = json.loads(response.text)
        resultado = validar_resultado_sentimiento(parsed)
        resultados_sentimiento.append({**entrada, "resultado": resultado})

        # Requisito del ejercicio: 6 segundos entre llamadas de sentimiento.
        if indice < len(TEXTOS) - 1:
            time.sleep(6)

    # Pausa adicional antes de la petición multimodal.
    time.sleep(6)

    # C) Multimodal: cargar la imagen con Pillow y enviarla a Gemini.
    with Image.open(IMAGE_PATH) as image:
        image = image.convert("RGB")
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=92)
        image_bytes = buffer.getvalue()

    prompt_imagen = (
        "Describe esta imagen en español en exactamente 4 apartados: "
        "1) Descripción general, 2) Objetos y elementos, 3) Colores y composición, "
        "4) Interpretación o posible uso. Sé concreto pero detallado."
    )

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
    print("=== Práctica Gemini API ===")
    print(f"Modo: {data['modo'].upper()}")
    print(f"Modelo: {data['modelo']}")
    print("\n[1] Conexión básica")
    print(data["conexion_basica"]["respuesta"])

    print("\n[2] Análisis de sentimiento")
    for i, item in enumerate(data["sentimiento"], start=1):
        resultado = item["resultado"]
        print(
            f"{i:02d}. {item['idioma'].upper()} | "
            f"{resultado['sentimiento']} | confianza={resultado['confianza']:.2f} | "
            f"entidades={len(resultado['entidades'])}"
        )

    print("\n[3] Multimodal")
    print(data["multimodal"]["respuesta"])
    print(f"\n[OK] Resultados guardados en: {RESULTS_PATH.name}")
    print(f"[OK] Imagen usada: {IMAGE_PATH.name}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Práctica unificada con Gemini 2.5 Flash: texto, sentimiento y visión."
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Ejecuta sin API key ni llamadas reales y genera resultados de demostración.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    crear_imagen_ejemplo(IMAGE_PATH)

    try:
        data = modo_demo() if args.demo else modo_real()
        guardar_resultados(data)
        imprimir_resumen(data)
        return 0
    except Exception as exc:  # Mensaje limpio para la práctica; mantiene salida no-cero.
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
