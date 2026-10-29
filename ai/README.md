# Integración Pi 3 / Pi 5

Instalada el 26/10/2026. Pi 3: `smatipitouchpi3@10.199.232.50`.
Pi 5: `recybot@10.199.232.70`.

La Pi 3 captura CSI y sirve la interfaz en http://10.199.232.50:8080.
Tocar el video envía una captura JPEG nueva al servicio de IA en la Pi 5. El proveedor
principal es OpenAI con `gpt-6-luna`; Roboflow actúa como respaldo ante una falla
técnica. El procesamiento es real, bajo demanda y con una solicitud simultánea. No hay
detección automática continua de presencia todavía.

La clasificación alojada propone una de las cuatro categorías, pero la interfaz siempre
pide confirmación humana. Una botella no determina automáticamente plástico o vidrio si
la fotografía no aporta evidencia suficiente. Hace falta entrenar y validar el modelo
local de residuos antes de automatizar la clasificación. No se controlan motores ni
compuertas.

Cada inferencia crea un `muestra_id` temporal. La fotografía solo se conserva cuando
la persona confirma una de las cuatro clases mediante `POST /api/muestras/confirmar`.
Las muestras quedan en `datos_aprendizaje/inbox/`, fuera de Git. Si YOLO no propuso
una caja válida, el JSON queda marcado con `requiere_revisar_caja: true` y el ejemplo
no entra al entrenamiento automático hasta corregirlo.

Configuración del servicio:

- `RECYBOT_INFERENCE_BACKEND=openai|local|roboflow|comparar`: selecciona el proveedor de inferencia. `openai` usa Roboflow como respaldo ante una falla técnica.
- `RECYBOT_MODEL_PATH`: ruta de `yolov8n.pt` o `best.pt`.
- `RECYBOT_MODEL_MODE=prueba|recybot`: el modo de prueba nunca asigna destino.
- `RECYBOT_CONFIDENCE`: umbral de detección; valor predeterminado `0.4`.
- `RECYBOT_IMAGE_SIZE`: resolución de inferencia; valor predeterminado `320` para Pi.
- `RECYBOT_COLLECT_SAMPLES=true|false`: habilita la cola de confirmaciones.
- `RECYBOT_LEARNING_DIR`: carpeta privada para imágenes y metadatos.
- `OPENAI_MODEL`: modelo de visión principal; valor predeterminado `gpt-6-luna`.
- `OPENAI_API_KEY_PATH`: archivo local con la API key de OpenAI.
- `ROBOFLOW_MODEL_ID`: modelo alojado que se consultará, por defecto `ee4016/3`.
- `ROBOFLOW_API_KEY_PATH`: archivo local que contiene la clave privada de Roboflow.

Al instalar pesos propios cambia simultáneamente `RECYBOT_MODEL_PATH` y
`RECYBOT_MODEL_MODE=recybot`, recarga la unidad y reinicia el servicio. El mapa de
clase a destino permanece en `learning.py`: `plastico`, `papel_carton`, `metal` y
`otros`. Vidrio, orgánicos y los demás materiales se agrupan en `otros`.

## OpenAI principal y Roboflow de respaldo

El modo predeterminado es `openai`: envía una fotografía por interacción a Responses API
con detalle bajo y razonamiento desactivado. La respuesta está restringida a las cuatro
clases de Recybot o `ninguno`. No se reintenta automáticamente. Si OpenAI falla por red,
timeout, error HTTP o respuesta inválida, se consulta Roboflow una sola vez. Un resultado
válido `ninguno` no activa el respaldo.

Las claves pueden guardarse en `ai/config/openai-api-key` y
`ai/config/roboflow-api-key`, o proporcionarse mediante `OPENAI_API_KEY` y
`ROBOFLOW_API_KEY`. `pnpm dev` solicita de forma oculta cualquier clave que falte. Los
archivos de `ai/config/` están ignorados por Git y las claves nunca llegan al navegador.

OpenAI clasifica el material pero no genera una caja de entrenamiento confiable. Por
eso sus detecciones quedan marcadas para revisión de caja antes de entrar al dataset.
La confirmación humana sigue siendo obligatoria.

## Roboflow temporal

Roboflow puede actuar como detector durante la recopilación inicial sin quedar acoplado
al producto final. Instala sus dependencias en el entorno virtual separado:

```powershell
.\.venv\Scripts\python.exe -m pip install -r ai\requirements-roboflow.txt
```

Para desarrollo local no es necesario ejecutar ese comando manualmente: `pnpm dev`
crea `.venv`, instala `ai/requirements-local.txt` y supervisa IA, puente y Vite. Al
presionar `Ctrl+C`, termina todos los procesos. La clave puede guardarse en
`ai/config/roboflow-api-key` o proporcionarse con `ROBOFLOW_API_KEY`.

Guarda la clave privada únicamente en `ai/config/roboflow-api-key`; esa carpeta está
ignorada por Git. Comprueba la conexión con una fotografía real, sin imprimir la clave:

```powershell
.\.venv\Scripts\python.exe ai\check_roboflow.py C:\ruta\residuo.jpg
```

Para usar solamente Roboflow en el servicio, define `RECYBOT_INFERENCE_BACKEND=roboflow`. El modo
`comparar` ejecuta el proveedor local y Roboflow sobre la misma captura, lo que permite
medir la transición antes de eliminar la dependencia externa. `local` conserva el flujo
sin conexión.

La inferencia alojada usa una única petición HTTP por captura, sin los reintentos
automáticos del SDK. También envía `disable_active_learning=true`: observar el video o
detectar un residuo no agrega imágenes al proyecto de Roboflow. Solo la herramienta de
sincronización descrita debajo puede subir muestras confirmadas.

Las confirmaciones permanecen primero en almacenamiento local. La sincronización se hace
por lotes y nunca bloquea una detección:

```powershell
.\.venv\Scripts\python.exe training\sync_roboflow.py --dry-run
.\.venv\Scripts\python.exe training\sync_roboflow.py --limit 20
```

Solo se envían muestras confirmadas con una caja válida y sin personas detectadas. Las
anotaciones se suben como predicciones para revisión humana en Roboflow, no como verdad
definitiva. Después de revisarlas se puede generar una versión YOLOv8, descargarla y
entrenar `best.pt` localmente para dejar de depender del servicio.

## Servicios y archivos

Pi 3: `~/recybot-camera/stream_server.py`, `web_bridge.py`, `~/recybot-web`.
Servicios de usuario: `recybot-camera`, `recybot-web`, `recybot-pantalla`.
Pi 5: `~/recybot-ia/server.py`, `.venv`, `modelos/yolov8n.pt`.
Servicio de usuario: `recybot-ia` habilitado; `Linger=yes` confirmado en Pi 5 para
mantenerlo activo sin sesión SSH y permitir el arranque del gestor de usuario al iniciar.

Credencial compartida (no incluir en git): Pi 5 `~/recybot-ia/config/api-token`,
Pi 3 `~/.config/recybot/api-token`, modo 600. El frontend no recibe la credencial.
HTTP es solo para la red local de confianza; no publicar puertos en Internet.
Si cambia IP de Pi 5, ajustar `Environment=RECYBOT_AI_URL=...` en la unidad web de Pi 3
y ejecutar `systemctl --user daemon-reload && systemctl --user restart recybot-web`.

Pi 5 rechaza nuevas inferencias a 80 °C o más; esto no es monitoreo periódico.
La automatización de monitoreo previamente cancelada sigue desactivada.

## Prueba

En Pi 3:
```sh
curl -s -X POST -H 'X-Recybot-Capture: 1' http://127.0.0.1:8080/api/identificar
```
En Pi 5: `.venv/bin/python test_api.py` desde `~/recybot-ia`.

Respaldo anterior de Pi 3: `~/recybot-backup-integracion-20261026/`, con cámara,
unidad web anterior y `web.tar.gz`. No contiene credenciales nuevas.
