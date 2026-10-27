# Recybot

Interfaz táctil para un basurero inteligente, construida con Svelte 5, TypeScript y Vite.

**Estado actual:** al tocar el video, la Pi 3 captura una imagen nueva y la Pi 5 identifica objetos con YOLOv8n. El modelo general no determina el material: la persona debe elegir Plástico, Papel / Cartón, Metal o Vidrio. No se accionan motores ni compuertas.

## Usar desde otra PC

La nueva PC ejecuta la interfaz; la cámara y la inferencia siguen en las Raspberry existentes. Ambas deben estar encendidas y la PC debe poder acceder al puente web de la Pi 3 por la LAN o una red privada con ruta hacia ella. Clonar no instala servicios ni cambia las Raspberry.

Versiones de referencia: **Node.js 24.12.0** (registrada en `.node-version`) y **pnpm 10.21.0** (registrada en `package.json`). Instala esas versiones y comprueba `node --version` y `pnpm --version`. Si falta pnpm, después de instalar Node ejecuta `npm install --global pnpm@10.21.0`.

```sh
git clone https://github.com/xmanugonzalez/recybot.git
cd recybot
pnpm install --frozen-lockfile
```

Copia `.env.example` a `.env.local`:

```powershell
# PowerShell
Copy-Item .env.example .env.local
```

```sh
# Linux / macOS
cp .env.example .env.local
```

Ajusta la dirección si la Pi 3 cambia de IP:

```dotenv
RECYBOT_BRIDGE_URL=http://10.199.232.50:8080
```

Inicia la interfaz y abre la dirección que indique Vite:

```sh
pnpm dev
```

Normalmente será `http://localhost:5173`. Reinicia Vite después de cambiar `.env.local`. La configuración también sirve para la vista previa:

```sh
pnpm check
pnpm build
pnpm preview
```

La vista previa normalmente usa `http://localhost:4173`. El proxy pertenece al servidor de Vite: publicar solamente `dist/` en otro servidor exige configurar allí el reenvío de `/api` hacia la Pi 3. `pnpm preview` es una comprobación local del build.

## Recorrido de las solicitudes

```text
Navegador → Vite en la PC → puente web en Pi 3:8080
                              ├─ cámara local:8765
                              └─ IA en Pi 5:8766
```

Desarrollo y vista previa reenvían `/api` sin cambiar sus rutas. El navegador pide `/api/camara/stream` para el video y envía `POST /api/identificar` con `X-Recybot-Capture: 1` para analizar una captura. La Pi 3 agrega la credencial al comunicarse con la Pi 5; la PC no necesita el token, Python, CUDA ni los pesos del modelo.

`RECYBOT_BRIDGE_URL` se lee exclusivamente en la configuración de Vite. No es una variable `VITE_*` ni se incluye como credencial en el frontend. Para esta instalación no configures `VITE_CAMERA_STREAM_URL`: deja que el video use la ruta relativa y el mismo proxy que la identificación.

## Comprobar el funcionamiento

1. Abre la interfaz y pulsa «Toca la pantalla para comenzar»; debe aparecer el video.
2. Toca el video o enfoca el botón de captura y presiona Enter/Espacio. Debe mostrarse el análisis y luego los objetos detectados.
3. Pulsa «Elegir material». «Confirmar selección» permanece desactivado hasta elegir una categoría.
4. Confirma y verifica el mensaje que indica que el mecanismo todavía no está conectado.
5. Si no se detecta un objeto, acerca uno a la cámara y vuelve a intentar. Si falla la cámara o la IA, la interfaz muestra el error correspondiente.

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
- `ai/`: servidor de inferencia, servicio y prueba HTTP para Pi 5. Consulta [la integración actual](ai/README.md).
- `.env.example`, `.node-version`, `package.json` y `pnpm-lock.yaml`: configuración y dependencias para la nueva PC.

`output/`, `tmp/`, entornos Python, pesos, datos de entrenamiento y credenciales quedan fuera de Git. No hacen falta para desarrollar desde otra PC usando las Raspberry actuales. Los experimentos locales de entrenamiento no forman parte de esta entrega.

`pnpm check` verifica Svelte/TypeScript y `pnpm build` genera la aplicación. No hay un comando `pnpm test`. La prueba `ai/test_api.py` requiere el entorno y token de la Pi 5; no es una dependencia de instalación de la PC. Reinstalar las Raspberry desde cero o reproducir entrenamiento son tareas separadas.
