# Práctica Gemini API — `google-genai` + `gemini-2.5-flash`

Práctica unificada para Windows PowerShell 5.1 y Python 3.14. Incluye:

- conexión básica por texto con Gemini;
- análisis de sentimiento de 5 textos en español y 5 en inglés;
- salida JSON estructurada para sentimiento;
- análisis multimodal de una imagen cargada con Pillow;
- modo `--demo` sin API Key;
- modo real usando `GEMINI_API_KEY`;
- guardado automático de los resultados en `resultados.json`.

## 1. Requisitos

- Windows con PowerShell 5.1.
- Python 3.14 instalado y disponible como `python` o mediante el launcher `py`.
- Acceso a Internet para instalar paquetes y, en modo real, llamar a la API de Gemini.
- Una API Key de Google AI Studio para el modo real.

Archivos del proyecto:

```text
Default Project/
├── gemini_practica.py
├── README.md
├── resultados.json
└── imagen_ejemplo.jpg
```

## 2. Instalación

Abre PowerShell y entra en la carpeta del proyecto:

```powershell
cd "C:\ruta\a\Default Project"
```

Instala o actualiza `google-genai` y Pillow:

```powershell
pip install -U google-genai Pillow
```

Si tienes varias versiones de Python, es más seguro usar Python 3.14 explícitamente:

```powershell
py -3.14 -m pip install -U google-genai Pillow
```

Verifica que el SDK se importa correctamente:

```powershell
python -c "from google import genai; from PIL import Image; print('Import OK: google-genai + Pillow')"
```

O con Python 3.14 explícito:

```powershell
py -3.14 -c "from google import genai; from PIL import Image; print('Import OK: google-genai + Pillow')"
```

La salida esperada es:

```text
Import OK: google-genai + Pillow
```

## 3. Obtener una API Key paso a paso

1. Entra en Google AI Studio: https://aistudio.google.com/app/apikey
2. Inicia sesión con tu cuenta de Google.
3. Pulsa **Create API key** / **Crear clave de API**.
4. Selecciona un proyecto existente o crea uno nuevo si AI Studio te lo solicita.
5. Copia la API Key generada.
6. No escribas la clave directamente dentro de `gemini_practica.py` ni la subas a GitHub.

### Configurar la clave solo para la sesión actual

En PowerShell:

```powershell
$env:GEMINI_API_KEY="TU_API_KEY_AQUI"
```

Puedes comprobar que existe sin mostrar el valor completo:

```powershell
if ($env:GEMINI_API_KEY) { "GEMINI_API_KEY configurada" } else { "No configurada" }
```

### Guardarla de forma persistente con `setx`

```powershell
setx GEMINI_API_KEY "TU_API_KEY_AQUI"
```

`setx` la guarda para futuras terminales. Después de ejecutarlo, cierra PowerShell y abre una ventana nueva. Si quieres usarla inmediatamente en la terminal actual, ejecuta también:

```powershell
$env:GEMINI_API_KEY="TU_API_KEY_AQUI"
```

## 4. Verificar el script

Primero comprueba que no tiene errores de sintaxis:

```powershell
python -m py_compile .\gemini_practica.py
```

Con el launcher de Python 3.14:

```powershell
py -3.14 -m py_compile .\gemini_practica.py
```

Si no aparece ningún mensaje, la compilación ha sido correcta.

## 5. Ejecutar en modo DEMO — sin API Key

```powershell
python .\gemini_practica.py --demo
```

O:

```powershell
py -3.14 .\gemini_practica.py --demo
```

En este modo no se llama a Google. Se generan resultados simulados con la misma estructura que en modo real y se guarda `resultados.json`.

## 6. Ejecutar en modo real — con API Key

Después de configurar `GEMINI_API_KEY`:

```powershell
python .\gemini_practica.py
```

O:

```powershell
py -3.14 .\gemini_practica.py
```

El programa crea el cliente de esta forma:

```python
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
```

Y usa el modelo:

```text
gemini-2.5-flash
```

> Nota: Google puede cambiar la disponibilidad de modelos y cuotas según el proyecto. Si AI Studio indica que `gemini-2.5-flash` no está disponible para tu proyecto, revisa los modelos habilitados antes de modificar el ejercicio.

## 7. Explicación del código

### A. Conexión básica

El programa obtiene `GEMINI_API_KEY` desde una variable de entorno, crea `genai.Client(...)` y realiza una llamada con:

```python
client.models.generate_content(
    model="gemini-2.5-flash",
    contents=prompt,
)
```

La respuesta se obtiene desde `response.text`.

### B. Análisis de sentimiento

Se analizan 10 textos en total:

- 5 en español;
- 5 en inglés.

Para cada texto se solicita:

```json
{
  "sentimiento": "positivo|negativo|neutro",
  "confianza": 0.0,
  "entidades": [
    {
      "texto": "...",
      "tipo": "..."
    }
  ],
  "justificacion": "..."
}
```

El programa fuerza una respuesta JSON mediante:

```python
config=types.GenerateContentConfig(
    response_mime_type="application/json",
    response_json_schema=SENTIMENT_SCHEMA,
    temperature=0.2,
)
```

Después se ejecuta `json.loads(response.text)` y se validan las claves principales.

Para no lanzar demasiadas peticiones seguidas en Free Tier se usa:

```python
time.sleep(6)
```

entre las llamadas de sentimiento. También hay pausas antes y después de ese bloque para repartir mejor las peticiones.

### C. Multimodal — texto + imagen

Si `imagen_ejemplo.jpg` no existe, el propio script crea una imagen sencilla usando Pillow.

Después la carga con:

```python
with Image.open(IMAGE_PATH) as image:
    image = image.convert("RGB")
```

La imagen se convierte a bytes JPEG y se envía junto al prompt usando `types.Part.from_bytes(...)`.

Se pide una descripción en cuatro apartados:

1. Descripción general.
2. Objetos y elementos.
3. Colores y composición.
4. Interpretación o posible uso.

### D. Guardado de resultados

Tanto en modo demo como en modo real se escribe `resultados.json` con:

- modo utilizado;
- modelo;
- fecha/hora UTC;
- respuesta de conexión básica;
- los 10 análisis de sentimiento;
- descripción multimodal.

El archivo se sobrescribe en cada ejecución.

## 8. Resultado obtenido en la ejecución DEMO

Comando ejecutado:

```powershell
python gemini_practica.py --demo
```

Salida de consola verificada:

```text
=== Práctica Gemini API ===
Modo: DEMO
Modelo: gemini-2.5-flash

[1] Conexión básica
[DEMO] Una API de inteligencia artificial permite que un programa envíe datos a un modelo y reciba una respuesta de forma automática.

[2] Análisis de sentimiento
01. ES | positivo | confianza=0.98 | entidades=1
02. ES | negativo | confianza=0.99 | entidades=1
03. ES | neutro | confianza=0.96 | entidades=3
04. ES | neutro | confianza=0.78 | entidades=2
05. ES | positivo | confianza=0.98 | entidades=2
06. EN | positivo | confianza=0.99 | entidades=1
07. EN | negativo | confianza=0.99 | entidades=2
08. EN | neutro | confianza=0.97 | entidades=2
09. EN | neutro | confianza=0.76 | entidades=2
10. EN | negativo | confianza=0.98 | entidades=2

[3] Multimodal
1. Descripción general: imagen didáctica creada para probar una entrada multimodal.
2. Objetos y elementos: un rectángulo amarillo, un círculo azul, un marco y textos.
3. Colores y composición: fondo claro, formas simples y composición centrada.
4. Interpretación/uso: sirve como imagen de ejemplo para comprobar que el script puede enviar una imagen a Gemini.

[OK] Resultados guardados en: resultados.json
[OK] Imagen usada: imagen_ejemplo.jpg
```

## 9. Límites gratuitos — tabla de referencia de la práctica

Los siguientes valores son los solicitados como referencia para esta práctica. Google puede modificar los límites del Free Tier, y la cuota efectiva puede variar por modelo/proyecto; para una entrega académica conviene indicar la fecha de consulta y comprobar los límites activos en AI Studio.

| Modelo | RPM | RPD | TPM |
|---|---:|---:|---:|
| Gemini Flash-Lite | 15 RPM | 1.000 RPD | 250.000 TPM |
| Gemini Flash | 10 RPM | 250 RPD | 250.000 TPM |
| Gemini Pro | 5 RPM | 50–100 RPD | 250.000 TPM |

Significado:

- **RPM**: requests per minute, peticiones por minuto.
- **RPD**: requests per day, peticiones por día.
- **TPM**: tokens per minute, tokens por minuto.

Documentación oficial de límites: https://ai.google.dev/gemini-api/docs/rate-limits

## 10. Errores comunes

### Error 429 — `RESOURCE_EXHAUSTED`

Significa normalmente que se ha superado alguna cuota o límite de frecuencia.

Soluciones:

- esperar antes de volver a llamar a la API;
- mantener las pausas `time.sleep(6)`;
- reducir el número de peticiones consecutivas;
- revisar las cuotas activas del proyecto en Google AI Studio.

### API Key inválida / no configurada

Si ejecutas el modo real sin variable de entorno, el script mostrará:

```text
[ERROR] No existe la variable GEMINI_API_KEY. Configúrala en PowerShell o ejecuta con --demo.
```

Si la clave existe pero Google la rechaza:

- comprueba que la has copiado completa;
- genera una clave nueva en AI Studio si es necesario;
- evita espacios antes o después de la clave;
- vuelve a abrir PowerShell si la configuraste únicamente con `setx`.

### `ModuleNotFoundError` o error al importar `genai`

Reinstala usando el mismo Python con el que ejecutas el script:

```powershell
py -3.14 -m pip install -U google-genai Pillow
py -3.14 -c "from google import genai; print('Import OK')"
```

### Modelo no disponible

Si el servicio indica que `gemini-2.5-flash` no existe o no está habilitado para tu proyecto, comprueba en AI Studio los modelos disponibles. No cambies el modelo de la práctica sin confirmar primero que el profesor permite usar otro.

## 11. Referencias oficiales

- Google Gen AI SDK para Python: https://googleapis.github.io/python-genai/
- Gemini API: https://ai.google.dev/gemini-api/docs
- Rate limits: https://ai.google.dev/gemini-api/docs/rate-limits
- Google AI Studio — API Keys: https://aistudio.google.com/app/apikey
