# Recybot

Interfaz táctil para un basurero inteligente que ayuda a separar residuos. El proyecto combina una experiencia visual de clasificación con una vista en directo de la cámara conectada a una Raspberry Pi.

> **Estado actual:** la interfaz muestra un flujo de clasificación de demostración. La cámara OV5647 puede transmitir video desde la Raspberry Pi, pero la detección y clasificación con YOLO, el control de compartimentos y la integración con hardware todavía no están implementados.

## Requisitos

- Node.js y pnpm instalados en el equipo de desarrollo.
- Raspberry Pi OS con soporte para `libcamera` y `Picamera2` para usar la cámara real.
- Cámara compatible conectada a la Raspberry Pi. El servicio incluido está preparado para la OV5647.

## Desarrollo local

Clona el repositorio e instala las dependencias:

```sh
git clone https://github.com/xmanugonzalez/recybot.git
cd recybot
pnpm install --frozen-lockfile
```

Inicia el servidor de desarrollo:

```sh
pnpm dev
```

Vite escucha en todas las interfaces de red para permitir abrir la interfaz desde otro dispositivo de la misma LAN. La vista de cámara utiliza `http://127.0.0.1:8765` por defecto. Como ese host apunta al propio dispositivo que abre la página, para ver la cámara real hay que abrir Recybot en Chromium en la Raspberry Pi donde corre el servicio.

Si necesitas cambiar la dirección del flujo en desarrollo, crea `.env.local` en la raíz:

```dotenv
VITE_CAMERA_STREAM_URL=http://127.0.0.1:8765/api/camara/stream
```

Los archivos `.env` locales están excluidos de Git. No guardes contraseñas, tokens ni otros secretos en el repositorio.

## Comprobaciones

```sh
pnpm check
pnpm build
```

El proyecto todavía no define un script `test`; por eso `pnpm test` no está disponible.

## Cámara en Raspberry Pi

El servidor de `camera/stream_server.py` publica MJPEG en `127.0.0.1:8765` y el estado en `/api/camara/status`. Se mantiene enlazado a loopback para que el flujo no quede expuesto directamente a la red local.

### Instalar el servicio

Desde PowerShell o una terminal con SSH y SCP, sustituye `<USUARIO>` y `<IP>` por los datos de tu Raspberry Pi:

```sh
ssh <USUARIO>@<IP> "mkdir -p ~/recybot-camera ~/.config/systemd/user"
scp camera/stream_server.py <USUARIO>@<IP>:~/recybot-camera/stream_server.py
scp camera/recybot-camera.service <USUARIO>@<IP>:~/.config/systemd/user/recybot-camera.service
ssh <USUARIO>@<IP> "systemctl --user daemon-reload && systemctl --user enable --now recybot-camera.service"
```

Instala antes `python3-picamera2` desde los paquetes de Raspberry Pi OS si aún no está disponible. La unidad usa `%h`, por lo que funciona con el directorio personal del usuario SSH y no requiere que la cuenta se llame `recybot`.

Comprueba el servicio y sus registros:

```sh
ssh <USUARIO>@<IP> "systemctl --user status recybot-camera.service"
ssh <USUARIO>@<IP> "journalctl --user -u recybot-camera.service -n 50 --no-pager"
ssh <USUARIO>@<IP> "curl -sS http://127.0.0.1:8765/api/camara/status"
```

Abre el frontend en un navegador que se ejecute en esa Raspberry Pi. Otros dispositivos pueden abrir la interfaz web, pero el flujo configurado en loopback no mostrará la cámara en ellos.

## Estructura

```text
camera/       Servicio MJPEG y unidad systemd de usuario
src/          Aplicación Svelte y recursos visuales
```

La aplicación está construida con Svelte 5, TypeScript estricto, Vite, Tailwind CSS v4 y componentes de iconos Tabler para Svelte.
