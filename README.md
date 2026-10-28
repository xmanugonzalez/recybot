# Recybot

Interfaz táctil para un basurero inteligente, construida con Svelte 5, TypeScript y Vite.

**Estado actual:** al tocar el video, la Pi 3 captura una imagen nueva y la Pi 5 identifica objetos con YOLOv8n. El modelo general no determina el material: la persona debe elegir Plástico, Vidrio, Metal o Papel / Cartón. Cuando confirma, la captura queda en una cola local para revisar y usar en un entrenamiento posterior. No se accionan motores ni compuertas.

## Instalación desde cero

Requisitos:

- Git
- Node.js 24.12.0
- pnpm 10.21.0
- Python 3.12
- Una Private API Key de Roboflow si vas a usar el backend `roboflow`

En Windows, instala pnpm después de Node.js si todavía no está disponible:

```powershell
npm install --global pnpm@10.21.0
```

Clona el repositorio e instala las dependencias JavaScript:

```powershell
git clone https://github.com/xmanugonzalez/recybot.git
cd recybot
pnpm install --frozen-lockfile
```

En Linux o macOS los mismos comandos funcionan desde una terminal Bash:

```bash
git clone https://github.com/xmanugonzalez/recybot.git
cd recybot
pnpm install --frozen-lockfile
```

Comprueba las versiones instaladas:

```text
node --version       # v24.12.0
pnpm --version       # 10.21.0
python --version     # Python 3.12.x en Windows
python3 --version    # Python 3.12.x en Linux/macOS
```

No necesitas crear `.venv` ni instalar manualmente las dependencias Python: `pnpm dev`
crea el entorno virtual e instala Pillow y PyYAML en el primer arranque. En Windows,
`pnpm run dev:server-camera` instala además OpenCV. En la Pi 3 usa el Picamera2 del
sistema y no instala OpenCV de Windows. Si prefieres instalar las dependencias locales
manualmente:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r ai\requirements-local.txt
```

Para añadir el adaptador OpenCV en Windows:

```powershell
.\.venv\Scripts\python.exe -m pip install -r ai\requirements-camera.txt
```

En Linux/macOS:

```bash
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r ai/requirements-local.txt
```

### Inicio directo en Raspberry Pi

En una Raspberry Pi configurada para el dispositivo, `~/recybot.sh` inicia Picamera2,
IA, puente, Vite y Chromium en modo kiosco. También se instalan los accesos directos
`Iniciar Recybot` y `Cerrar Recybot` en el escritorio, además del arranque automático
en `~/.config/autostart/recybot.desktop`. La comunicación interna usa `127.0.0.1`;
desde otro equipo se accede mediante la IP actual, por ejemplo
`http://10.181.61.50:5173`.

Para detenerlo manualmente:

```sh
~/recybot-stop.sh
```

Si el arranque se detiene en Picamera2, comprueba la conexión CSI y ejecuta
`rpicam-hello --list-cameras` antes de volver a pulsar `Iniciar Recybot`.

### Configurar la clave de Roboflow

La clave privada nunca se incluye en Git. Puedes configurarla de cualquiera de estas
formas:

1. Ejecuta `pnpm dev`. Si falta la clave, el supervisor la solicitará de forma oculta
   y la guardará en `ai/config/roboflow-api-key`.
2. Créala manualmente en PowerShell:

```powershell
New-Item -ItemType Directory -Force ai\config | Out-Null
Set-Content -Path ai\config\roboflow-api-key -Value 'rf_TU_PRIVATE_API_KEY' -NoNewline
```

3. O usa una variable de entorno únicamente para esa sesión:

```powershell
$env:ROBOFLOW_API_KEY='rf_TU_PRIVATE_API_KEY'
pnpm dev
```

En Linux/macOS:

```bash
mkdir -p ai/config
printf '%s' 'rf_TU_PRIVATE_API_KEY' > ai/config/roboflow-api-key
chmod 600 ai/config/roboflow-api-key
```

Reemplaza `rf_TU_PRIVATE_API_KEY` por la clave de Workspace Settings → API Keys de
Roboflow. No la pegues en `README.md`, `.env.example`, el frontend ni ningún archivo
que vayas a subir. La carpeta `ai/config/` está ignorada por Git.

El token entre el puente y la IA se genera automáticamente en `ai/config/api-token`.
No es la clave de Roboflow y tampoco debe subirse al repositorio.

## Arranque local completo

La PC ejecuta la interfaz, el puente y la inferencia como un único sistema supervisado. La cámara pertenece al navegador del dispositivo que abre la página; el video en vivo no consume créditos y cada toque envía una sola fotografía.

Versiones de referencia: **Node.js 24.12.0** (registrada en `.node-version`) y **pnpm 10.21.0** (registrada en `package.json`). Instala esas versiones y comprueba `node --version` y `pnpm --version`. Si falta pnpm, después de instalar Node ejecuta `npm install --global pnpm@10.21.0`.

```sh
git clone https://github.com/xmanugonzalez/recybot.git
cd recybot
pnpm install --frozen-lockfile
```

También hace falta Python 3.12. No es necesario crear el entorno virtual manualmente: el primer arranque crea `.venv`, instala las dependencias de `ai/requirements-local.txt` y genera el token privado entre los servicios. Si todavía no existe `ai/config/roboflow-api-key`, solicita la Private API Key una sola vez, la oculta mientras escribes y la guarda fuera de Git.

Inicia todo con un solo comando:

```sh
pnpm dev
```

Cuando aparezca `Sistema listo`, abre `http://localhost:5173`. Para detener cámara, IA, puente, Vite y todos sus subprocesos, presiona `Ctrl+C` o `Q` en esa misma terminal. El supervisor captura la orden directamente, incluso en Windows, y devuelve el control sin pedir otra confirmación. Si un servicio falla, apaga los demás para no dejar procesos huérfanos.

La configuración también permite comprobar la interfaz por separado:

```sh
pnpm check
pnpm build
pnpm preview
```

La vista previa normalmente usa `http://localhost:4173`. El proxy pertenece al servidor de Vite: publicar solamente `dist/` en otro servidor exige configurar allí el reenvío de `/api` hacia la Pi 3. `pnpm preview` es una comprobación local del build.

## Probar todo en la PC

La PC usa por defecto la cámara del navegador. Para probar específicamente el adaptador OpenCV y el stream MJPEG del servidor, utiliza:

```sh
pnpm run dev:server-camera
```

Este modo también queda bajo el mismo supervisor y se apaga completamente con `Ctrl+C`.

`ai/config/api-token` contiene el token interno generado automáticamente y
`ai/config/roboflow-api-key` la clave privada de Roboflow. También puedes proporcionar
esta última mediante `ROBOFLOW_API_KEY`. Ambos archivos están fuera de Git y nunca se
suben a GitHub.
El video MJPEG permanece local y no consume créditos: solo un toque con la cámara
activa obtiene un JPEG y llama a `/api/identificar`. Después de una respuesta correcta
no se permite repetir dentro de esa clasificación; ante un error, un nuevo toque manual
realiza como máximo otra consulta.

`RECYBOT_CAMERA_FLIP_HORIZONTAL=true` corrige una cámara que entrega texto e imágenes
en espejo. La corrección se aplica antes del stream y de la captura, de modo que Roboflow
y el dataset reciben exactamente la misma orientación que ve el usuario.

## Recorrido de las solicitudes

```text
Navegador → Vite → puente:8080
                    ├─ cámara configurable:8765 (OpenCV o Picamera2)
                    └─ IA configurable:8766 (PC o Pi 5)
```

Desarrollo y vista previa reenvían `/api` sin cambiar sus rutas. Por defecto (`VITE_CAMERA_SOURCE=device`), cada navegador solicita la cámara conectada al mismo dispositivo donde está abierto y envía directamente un único JPEG a `POST /api/identificar`; nunca elige la cámara de otra computadora por el tamaño de la pantalla. En navegadores sin video directo, el recuadro abre el selector de cámara o fotografía del propio dispositivo. El modo `VITE_CAMERA_SOURCE=server` queda reservado para una instalación donde la interfaz y el adaptador `Picamera2` se ejecutan juntos en Recybot. No hay reintentos automáticos. La respuesta contiene un `muestra_id` temporal. Al confirmar el material, el navegador envía `POST /api/muestras/confirmar`; recién entonces la IA conserva la imagen y su etiqueta. La Pi 3 agrega la credencial al comunicarse con la Pi 5; la PC no necesita el token, Python, CUDA ni los pesos del modelo para usar la interfaz.

`RECYBOT_BRIDGE_URL` se lee exclusivamente en la configuración de Vite. No es una variable `VITE_*` ni se incluye como credencial en el frontend. Para esta instalación no configures `VITE_CAMERA_STREAM_URL`: deja que el video use la ruta relativa y el mismo proxy que la identificación.

## Comprobar el funcionamiento

1. Abre la interfaz y pulsa «Toca la pantalla para comenzar»; debe aparecer el video.
2. Toca el video o enfoca el botón de captura y presiona Enter/Espacio. Debe mostrarse el análisis y luego los objetos detectados.
3. Pulsa «Elegir material». «Confirmar selección» permanece desactivado hasta elegir una categoría.
4. Confirma y verifica el mensaje que indica si la muestra quedó lista o necesita revisar su caja.
5. Si no se detecta un objeto, igualmente puedes indicar el material; la captura quedará separada para dibujar su caja antes de entrenar. Si falla la cámara o la IA, la interfaz muestra el error correspondiente.

## Aprendizaje activo

Las confirmaciones se guardan fuera de Git en `ai/datos_aprendizaje/inbox/`. Cada imagen tiene un JSON con la clase confirmada, las detecciones originales y la mejor caja propuesta. Una captura sin caja nunca entra automáticamente al entrenamiento: queda marcada con `requiere_revisar_caja: true`.

Las cuatro clases de entrenamiento son `botella_plastico`, `botella_vidrio`, `lata` y `papel_carton`. Las predicciones públicas `paper` y `cardboard` se combinan en la misma categoría y el mismo destino físico.

Roboflow está integrado como apoyo temporal. Puede detectar con el modelo público
`ee4016/3`, comparar sus resultados con el modelo local y recibir por lotes las muestras
confirmadas. La clave se guarda en `ai/config/roboflow-api-key`, fuera de Git. Las
anotaciones subidas siguen requiriendo revisión humana; Roboflow no se usa para que el
sistema se entrene solo ni para accionar compartimentos. Consulta los comandos y las
variables en [la guía del servicio de IA](ai/README.md).

En la máquina con GPU, instala PyTorch, Ultralytics y PyYAML en un entorno aislado. Descarga un dataset público YOLO y ejecuta el entrenador por lotes:

```powershell
python training/train_if_ready.py `
  --public-data C:\datasets\residuos\data.yaml `
  --learning-dir C:\datos-recybot `
  --workspace C:\entrenamiento-recybot `
  --base-model yolov8n.pt `
  --current-model C:\modelos\best.pt `
  --deploy-path C:\modelos\best.pt
```

Por defecto espera al menos 100 muestras confirmadas con caja y no repite un conjunto ya procesado. Crea una combinación nueva del dataset público y las imágenes locales, entrena hasta 100 épocas con parada temprana y evalúa sobre la partición de prueba. Solo promueve el candidato si alcanza `mAP50-95 >= 0.35` o mejora al modelo anterior por al menos `0.005`; antes de reemplazarlo conserva un respaldo. Programar este comando con el Programador de tareas o `cron` automatiza el ciclo. La sincronización de las muestras desde la Pi hacia la computadora de entrenamiento debe hacerse por una ruta privada; no se incluye subida a Internet.

## Diagnóstico

- **No hay video ni identificación:** comprueba la IP, la conexión de red y el puerto 8080 de la Pi 3. En PowerShell: `Test-NetConnection 10.199.232.50 -Port 8080`.
- **Comprobar cámara a través del puente:** abre `http://10.199.232.50:8080/api/camara/status`. A través de desarrollo, abre `http://localhost:5173/api/camara/status` (ajusta el puerto si Vite eligió otro).
- **El puente responde directamente pero Vite no:** revisa `.env.local`, reinicia Vite y elimina cualquier override antiguo de `VITE_CAMERA_STREAM_URL`.
- **Hay video pero la Pi 5 no responde:** comprueba desde la red de las Raspberry `http://10.199.232.70:8766/api/salud`. El proxy de la PC debe apuntar a la Pi 3, no directamente a la Pi 5.
- **Servicio detenido:** consulta por SSH `systemctl --user status recybot-camera recybot-web` en Pi 3 o `systemctl --user status recybot-ia` en Pi 5. Los registros se consultan con `journalctl --user -u NOMBRE -n 50 --no-pager`.
- **No se puede acceder a la LAN desde la nueva PC:** la interfaz puede compilar, pero la cámara y la inferencia no estarán disponibles hasta tener conectividad.

Vite escucha en todas las interfaces para pruebas en la LAN. Usa esta configuración en una red de confianza; no publiques sus puertos ni los de las Raspberry en Internet.

## Archivos y alcance

- `src/`: interfaz y recursos visuales versionados.
- `camera/`: cámara, puente web y servicios actuales de Pi 3.
- `ai/`: servidor de inferencia, cola de aprendizaje activo y pruebas para Pi 5. Consulta [la integración actual](ai/README.md).
- `training/`: preparación reproducible del dataset y entrenamiento con promoción condicionada por métricas.
- `.env.example`, `.node-version`, `package.json` y `pnpm-lock.yaml`: configuración y dependencias para la nueva PC.

`output/`, `tmp/`, entornos Python, pesos, datos de entrenamiento y credenciales quedan fuera de Git. No hacen falta para desarrollar desde otra PC usando las Raspberry actuales.

`pnpm check` verifica Svelte/TypeScript y `pnpm build` genera la aplicación. No hay un comando `pnpm test`. `python ai/test_learning.py` y `python training/test_build_dataset.py` prueban el flujo de datos sin cargar YOLO. La prueba `ai/test_api.py` requiere el entorno, modelo y token del servicio de IA.
